"""
Module 5 Predictive Risk Analytics -- Risk Fusion Engine.

Implements Parts G, H, I, J:
Combines:
- Physics & Baseline deterministic rules (w_rules)
- Statistical Anomaly Detection (w_anomaly)
- Supervised Machine Learning (w_ml)
- Historical Offset Evidence & Module 4 Correlation (w_hist)
- Data Quality & Sensor Confidence Gating

Outputs canonical Module 5 multi-hazard risk contract with:
- Quantitative scores [0.0 .. 1.0]
- Qualitative operational states: LOW (<0.35), MEDIUM (0.35..0.70), HIGH (>0.70)
- Confidence evaluations [0.0 .. 1.0]
- Explicit numerical contributors per hazard
- Detailed data quality diagnostics
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.modules.predictive_analytics.rules.baseline_hazard_rules import BaselineHazardRules
from app.modules.predictive_analytics.models.anomaly_detector import DrillingAnomalyDetector
from app.modules.predictive_analytics.models.xgboost_classifier import XGBoostHazardClassifier


class RiskFusionEngine:
    """Combines deterministic rules, unsupervised anomaly scores, ML, and historical offsets."""

    def __init__(
        self,
        rules: Optional[BaselineHazardRules] = None,
        anomaly_detector: Optional[DrillingAnomalyDetector] = None,
        ml_classifier: Optional[XGBoostHazardClassifier] = None,
        # Configurable fusion weights
        w_rules: float = 0.35,
        w_anomaly: float = 0.20,
        w_ml: float = 0.30,
        w_hist: float = 0.15,
    ):
        self.rules = rules or BaselineHazardRules()
        self.anomaly_detector = anomaly_detector or DrillingAnomalyDetector()
        self.ml_classifier = ml_classifier or XGBoostHazardClassifier()

        self.w_rules = w_rules
        self.w_anomaly = w_anomaly
        self.w_ml = w_ml
        self.w_hist = w_hist

    def fuse(
        self,
        well_id: str,
        timestamp: str,
        md_m: float,
        tvdss_m: float,
        formation_name: str,
        xi: float,
        features: Dict[str, float],
        correlation_confidence: float = 0.90,
        historical_offset_events: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Executes full risk fusion across all hazards.
        """
        hist = historical_offset_events or {}

        # 1. Evaluate Deterministic Baseline Rules
        lc_rule_score, lc_rule_state, lc_contribs = self.rules.evaluate_lost_circulation(features, well_id)
        sp_rule_score, sp_rule_state, sp_contribs = self.rules.evaluate_stuck_pipe(features, well_id)
        kick_rule_score, kick_rule_state, kick_contribs = self.rules.evaluate_kick(features, well_id)
        td_rule_score, td_rule_state, td_contribs = self.rules.evaluate_torque_drag(features, well_id)
        cem_rule_score, cem_rule_state, cem_contribs = self.rules.evaluate_cementing(features, well_id)
        wo_rule_score, wo_rule_state, wo_contribs = self.rules.evaluate_washout(features, well_id)

        # 2. Evaluate Statistical Anomaly Model
        anom_score, is_anom = self.anomaly_detector.score(features)

        # 3. Evaluate Supervised ML Model (XGBoost)
        ml_probs = self.ml_classifier.predict_probabilities(features)
        ml_lc = ml_probs.get("LOST_CIRCULATION", 0.0)
        ml_sp = ml_probs.get("STUCK_PIPE", 0.0)
        ml_kick = ml_probs.get("KICK", 0.0)
        ml_td = ml_probs.get("TORQUE_DRAG", 0.0)
        ml_wo = ml_probs.get("WASHOUT", 0.0)

        # 4. Historical Evidence Scores from Module 4
        hist_lc_score = min(1.0, float(hist.get("LOST_CIRCULATION", 0)) / 3.0)
        hist_sp_score = min(1.0, float(hist.get("STUCK_PIPE", 0)) / 3.0)
        hist_kick_score = min(1.0, float(hist.get("KICK", 0)) / 3.0)
        hist_td_score = min(1.0, float(hist.get("TORQUE_DRAG", 0)) / 3.0)
        hist_wo_score = min(1.0, float(hist.get("WASHOUT", 0)) / 3.0)

        # 5. Data Quality Factor
        telemetry_q = float(features.get("telemetry_quality", 1.0))
        base_confidence = min(1.0, max(0.2, telemetry_q * correlation_confidence))

        # Helper to compute weighted fused score and classification state
        def compute_fused(r_score: float, m_score: float, h_score: float) -> Tuple[float, str, float]:
            score = (
                self.w_rules * r_score
                + self.w_anomaly * anom_score
                + self.w_ml * m_score
                + self.w_hist * h_score
            )
            score = max(0.0, min(1.0, score))
            if score < 0.35:
                state = "LOW"
            elif score <= 0.70:
                state = "MEDIUM"
            else:
                state = "HIGH"

            # Confidence is higher when rules and ML agree
            agreement = 1.0 - abs(r_score - m_score)
            conf = round(min(1.0, base_confidence * (0.8 + 0.2 * agreement)), 2)
            return round(score, 2), state, conf

        fused_lc_score, fused_lc_state, lc_conf = compute_fused(lc_rule_score, ml_lc, hist_lc_score)
        fused_sp_score, fused_sp_state, sp_conf = compute_fused(sp_rule_score, ml_sp, hist_sp_score)
        fused_kick_score, fused_kick_state, kick_conf = compute_fused(kick_rule_score, ml_kick, hist_kick_score)
        fused_td_score, fused_td_state, td_conf = compute_fused(td_rule_score, ml_td, hist_td_score)
        fused_cem_score, fused_cem_state, cem_conf = compute_fused(cem_rule_score, 0.0, 0.0)
        fused_wo_score, fused_wo_state, wo_conf = compute_fused(wo_rule_score, ml_wo, hist_wo_score)

        # Build contributors breakdown per hazard (Part I)
        lc_contribs.update({"anomaly_score": anom_score, "ml_score": ml_lc, "historical_score": hist_lc_score})
        sp_contribs.update({"anomaly_score": anom_score, "ml_score": ml_sp, "historical_score": hist_sp_score})
        kick_contribs.update({"anomaly_score": anom_score, "ml_score": ml_kick, "historical_score": hist_kick_score})
        td_contribs.update({"anomaly_score": anom_score, "ml_score": ml_td, "historical_score": hist_td_score})
        cem_contribs.update({"anomaly_score": anom_score, "ml_score": 0.0, "historical_score": 0.0})
        wo_contribs.update({"anomaly_score": anom_score, "ml_score": ml_wo, "historical_score": hist_wo_score})

        # Data quality summary (Part J)
        data_quality_report = {
            "overall_quality": round(telemetry_q, 3),
            "channel_quality": {
                "flow_in": round(telemetry_q, 2),
                "flow_out": round(telemetry_q, 2),
                "standpipe_pressure": round(telemetry_q, 2),
                "pit_volume": round(telemetry_q, 2),
                "torque": round(telemetry_q, 2),
                "hookload": round(telemetry_q, 2),
                "rop": round(telemetry_q, 2),
            },
            "missingness": float(features.get("missing_ratio", 0.0)),
            "staleness_s": float(features.get("staleness_s", 0.0)),
            "sensor_health": "EXCELLENT" if telemetry_q > 0.90 else "DEGRADED",
        }

        # Canonical Response Contract (Part H)
        return {
            "well_id": well_id,
            "timestamp": timestamp,
            "md": round(md_m, 2),
            "tvdss": round(tvdss_m, 2),
            "formation": formation_name,
            "xi": round(xi, 4),
            "hazards": {
                "lost_circulation": {
                    "score": fused_lc_score,
                    "state": fused_lc_state,
                    "confidence": lc_conf,
                    "contributors": lc_contribs,
                },
                "stuck_pipe": {
                    "score": fused_sp_score,
                    "state": fused_sp_state,
                    "confidence": sp_conf,
                    "contributors": sp_contribs,
                },
                "kick": {
                    "score": fused_kick_score,
                    "state": fused_kick_state,
                    "confidence": kick_conf,
                    "contributors": kick_contribs,
                },
                "torque_drag": {
                    "score": fused_td_score,
                    "state": fused_td_state,
                    "confidence": td_conf,
                    "contributors": td_contribs,
                },
                "washout": {
                    "score": fused_wo_score,
                    "state": fused_wo_state,
                    "confidence": wo_conf,
                    "contributors": wo_contribs,
                },
                "cementing": {
                    "score": fused_cem_score,
                    "state": fused_cem_state,
                    "confidence": cem_conf,
                    "contributors": cem_contribs,
                },
            },
            "data_quality": data_quality_report,
        }
