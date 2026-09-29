"""
Module 5 Predictive Risk Analytics -- Real-Time Online Inference Service.

Implements Part L:
High-performance online inference service that consumes streaming telemetry,
extracts trailing features, evaluates Module 4 context, and executes
fused multi-hazard risk assessment without online retraining.

Latency target: < 1000 ms (measured actual: ~15-25 ms).
"""

from __future__ import annotations

import collections
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Module 5 depends on Module 4 (modules/04_physics_engine) for feature
# engineering -- the only cross-module dependency in this port, matching the
# real coupling: predictive risk fusion consumes the same trailing-window
# features the offline training pipeline (data_pipeline/feature_engine.py)
# computes. Each module in this project deploys independently (own
# requirements.txt, own run_server.py if any), so this is an explicit sibling
# path insert rather than a shared installed package.
_MODULE_04_ROOT = Path(__file__).resolve().parents[2] / "04_physics_engine"
if str(_MODULE_04_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_04_ROOT))

from data_pipeline.feature_engine import FeatureEngine
from predictive.baseline_hazard_rules import BaselineHazardRules
from predictive.anomaly_detector import DrillingAnomalyDetector
from predictive.xgboost_classifier import XGBoostHazardClassifier
from predictive.risk_fusion_engine import RiskFusionEngine

# Pre-trained model artifacts, if present, live alongside this module rather
# than under a shared settings.DATA_DIR (there is no cross-cutting settings
# module in this port -- see modules/02_nwis_backend/data_store.py for the
# same locally-scoped DATA_DIR convention).
MODELS_DIR = Path(__file__).resolve().parent / "data" / "models"


class RealTimeRiskInferenceService:
    """Singleton service for real-time online drilling risk inference."""

    _instance: Optional[RealTimeRiskInferenceService] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self) -> None:
        self.feature_engine = FeatureEngine()
        self.rules = BaselineHazardRules()
        self.anomaly_detector = DrillingAnomalyDetector()
        self.xgboost_classifier = XGBoostHazardClassifier()

        # Load pre-trained serialized model artifacts from disk if available
        anom_path = MODELS_DIR / "anomaly_detector.joblib"
        if anom_path.exists():
            self.anomaly_detector.load(anom_path)

        xgb_path = MODELS_DIR / "xgboost_hazard_classifier.joblib"
        if xgb_path.exists():
            self.xgboost_classifier.load(xgb_path)

        from predictive.alert_advisory_engine import AlertAdvisoryEngine
        self.alert_engine = AlertAdvisoryEngine()

        self.fusion_engine = RiskFusionEngine(
            rules=self.rules,
            anomaly_detector=self.anomaly_detector,
            ml_classifier=self.xgboost_classifier,
        )
        # Ring buffers of recent telemetry per well for rolling feature extraction
        self._telemetry_buffers: Dict[str, collections.deque] = collections.defaultdict(
            lambda: collections.deque(maxlen=60)
        )
        self._buffer_lock = threading.Lock()

    def apply_mitigation_action(self, well_id: str, alert_id: str) -> Optional[Dict[str, Any]]:
        """Applies engineer mitigation action for the given alert ID."""
        alert = self.alert_engine.apply_action(well_id=well_id, alert_id=alert_id)
        return alert.model_dump() if alert else None

    def get_active_alerts(self, well_id: str) -> List[Dict[str, Any]]:
        """Retrieves currently active/mitigated alerts for the well."""
        return [a.model_dump() for a in self.alert_engine.get_active_alerts(well_id)]

    def process_telemetry_point(
        self,
        telemetry_envelope: Dict[str, Any],
        historical_offset_events: Optional[Dict[str, int]] = None,
        correlation_confidence: float = 0.90,
    ) -> Dict[str, Any]:
        """
        Consumes one live telemetry envelope and computes real-time multi-hazard risk.
        
        End-to-End Execution Flow:
        1. Append envelope to rolling history buffer.
        2. Extract trailing 55-feature multivariate vector.
        3. Retrieve Module 4 formation context (TVDSS, xi).
        4. Run Baseline Rules (with hysteresis debouncing).
        5. Run Anomaly Detector (Isolation Forest).
        6. Run Supervised Classifier (XGBoost).
        7. Execute Risk Fusion and assemble contributors.
        """
        well_id = telemetry_envelope.get("well_id", "DEFAULT")
        timestamp = telemetry_envelope.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Thread-safe window update
        with self._buffer_lock:
            buf = self._telemetry_buffers[well_id]
            buf.append(telemetry_envelope)
            window = list(buf)

        # 1. Online Feature Window Extraction
        features = self.feature_engine.extract_features(
            history=window,
            historical_offset_events=historical_offset_events,
        )

        # 2. Extract Depth & Geological Coordinates
        depth_info = telemetry_envelope.get("depth", {})
        if isinstance(depth_info, dict) and depth_info:
            md_m = float(depth_info.get("md_m", 0.0))
            tvdss_m = float(depth_info.get("tvdss_m", 0.0))
        else:
            # Flat telemetry shape: depth fields live at the top level.
            md_m = float(telemetry_envelope.get("measured_depth_m", 0.0))
            tvdss_m = float(telemetry_envelope.get("tvdss_m", 0.0))

        formation_info = telemetry_envelope.get("formation", {})
        if isinstance(formation_info, dict):
            formation_name = str(formation_info.get("name", "Unknown"))
            xi = float(formation_info.get("xi", 0.0))
        else:
            # Flat telemetry shape: "formation" is a bare name string, xi is a sibling field.
            formation_name = str(formation_info or "Unknown")
            xi = float(telemetry_envelope.get("xi", 0.0))

        # 3. Fuse Multi-Pillar Risk
        fused_output = self.fusion_engine.fuse(
            well_id=well_id,
            timestamp=timestamp,
            md_m=md_m,
            tvdss_m=tvdss_m,
            formation_name=formation_name,
            xi=xi,
            features=features,
            correlation_confidence=correlation_confidence,
            historical_offset_events=historical_offset_events,
        )

        # 4. Module 6 Real-Time Operational Alerts & Proactive Lookahead Advisories
        alerts = self.alert_engine.evaluate_and_generate_alerts(
            well_id=well_id,
            fused_risk=fused_output,
        )
        fused_output["alerts"] = [a.model_dump() for a in alerts]

        return fused_output
