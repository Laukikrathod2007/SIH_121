"""
Train and serialize Module 05 Predictive Risk Analytics models:
1. DrillingAnomalyDetector (IsolationForest)
2. XGBoostHazardClassifier (XGBoost 6-class multi-hazard)

Saves artifacts to:
modules/05_predictive_analytics/predictive/data/models/
- anomaly_detector_isolation_forest.joblib
- xgboost_hazard_classifier.joblib
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "Backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.modules.physics.simulation.engine import DrillingPhysicsEngine
from app.modules.physics.simulation.faults import ScenarioType
from app.modules.physics.models.state import FormationParams
from app.modules.predictive_analytics.predictive.realtime_inference import RealTimeRiskInferenceService
from app.modules.predictive_analytics.predictive.anomaly_detector import DrillingAnomalyDetector
from app.modules.predictive_analytics.predictive.xgboost_classifier import XGBoostHazardClassifier

OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FORMATIONS = [
    FormationParams(
        name="Shale_Cap",
        top_tvdss_m=2000.0,
        base_tvdss_m=2500.0,
        ucs_mpa=45.0,
        pore_pressure_gradient_gcc=1.05,
        fracture_gradient_gcc=1.85,
        friction_coefficient=0.25,
        permeability_md=0.01,
        leakoff_coefficient=1e-6,
        drillability_coefficient=0.75,
    ),
    FormationParams(
        name="Porous_Sandstone",
        top_tvdss_m=2500.0,
        base_tvdss_m=2800.0,
        ucs_mpa=28.0,
        pore_pressure_gradient_gcc=1.12,
        fracture_gradient_gcc=1.55,
        friction_coefficient=0.38,
        permeability_md=120.0,
        leakoff_coefficient=0.02,
        drillability_coefficient=0.90,
    ),
]


def generate_training_data():
    scenarios = [
        (ScenarioType.NORMAL, "NORMAL", 140),
        (ScenarioType.LOST_CIRCULATION, "LOST_CIRCULATION", 70),
        (ScenarioType.KICK_OVERPRESSURE, "KICK", 70),
        (ScenarioType.STUCK_PIPE, "STUCK_PIPE", 70),
        (ScenarioType.STICK_SLIP, "TORQUE_DRAG", 70),
        (ScenarioType.WASHOUT, "WASHOUT", 70),
    ]
    train_features = []
    train_labels = []
    normal_for_anomaly = []

    for scen, label, steps in scenarios:
        engine = DrillingPhysicsEngine(formations=FORMATIONS)
        service = RealTimeRiskInferenceService()
        if scen in (ScenarioType.LOST_CIRCULATION, ScenarioType.KICK_OVERPRESSURE):
            engine.state.md_m = 2650.0
            engine._update_depth_and_formation()

        if scen != ScenarioType.NORMAL:
            for _ in range(5):
                _, t = engine.step(1.0)
                service.process_telemetry_point(t.model_dump())
            engine.faults.inject_scenario(scen, severity=1.0, start_sim_time_s=engine.state.sim_time_s)

        for _ in range(steps):
            _, t = engine.step(1.0)
            service.process_telemetry_point(t.model_dump())
            buf = list(service._telemetry_buffers[engine.well_id])
            if len(buf) >= 5:
                f = service.feature_engine.extract_features(buf)
                train_features.append(f)
                train_labels.append(label)
                if label == "NORMAL":
                    normal_for_anomaly.append(f)

    return train_features, train_labels, normal_for_anomaly


if __name__ == "__main__":
    print("Collecting physics-driven telemetry training features across 6 hazard scenarios...")
    features, labels, normal_feats = generate_training_data()
    print(f"Total features collected: {len(features)} across {len(set(labels))} classes")
    print(f"Normal baseline samples for IsolationForest: {len(normal_feats)}")

    # 1. Train & save XGBoost classifier
    xgb_clf = XGBoostHazardClassifier()
    xgb_meta = xgb_clf.fit(features, labels)
    xgb_path = OUTPUT_DIR / "xgboost_hazard_classifier.joblib"
    xgb_clf.save(xgb_path)
    print(f"Saved XGBoost model to {xgb_path} (classes: {xgb_meta['train_samples']} samples)")

    # 2. Train & save Anomaly Detector
    anom_det = DrillingAnomalyDetector(contamination=0.03)
    anom_meta = anom_det.fit(normal_feats)
    anom_path = OUTPUT_DIR / "anomaly_detector_isolation_forest.joblib"
    anom_det.save(anom_path)
    print(f"Saved Anomaly Detector to {anom_path} (fitted on {anom_meta['training_samples']} samples)")
