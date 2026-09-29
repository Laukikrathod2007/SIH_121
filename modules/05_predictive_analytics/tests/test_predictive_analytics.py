"""
Unit and Integration Tests for Module 5 Predictive Risk Analytics Subsystem.

Tests:
1. Part A: Baseline Deterministic Rules (Debounce, Hysteresis, Single-Spike Rejection)
2. Part B: Unsupervised Anomaly Detector (Isolation Forest on Normal Operations)
3. Part C & D: Supervised Multiclass Classifier (XGBoost 6-Class Prediction)
4. Part G, H, I, J: Risk Fusion Engine & Output Contract Compliance
5. Part L & M: Real-Time Online Inference Service & End-to-End Latency (< 1000 ms)
"""

from __future__ import annotations

import time
import pytest
from typing import Dict, Any

from predictive.baseline_hazard_rules import (
    BaselineHazardRules,
    DebounceState,
)
from predictive.anomaly_detector import DrillingAnomalyDetector
from predictive.xgboost_classifier import (
    XGBoostHazardClassifier,
    HAZARD_TARGET_MAP,
)
from predictive.risk_fusion_engine import RiskFusionEngine
from predictive.realtime_inference import RealTimeRiskInferenceService


class TestBaselineHazardRules:
    """Tests Part A deterministic hazard engines."""

    def test_single_noisy_spike_does_not_trigger_lost_circulation(self):
        rules = BaselineHazardRules(lc_persistence=3)
        well_id = "TEST-WELL-LC-SPIKE"

        # Baseline normal features
        normal_feats = {"delta_flow": 0.0, "pit_slope": 0.0, "fg_margin_bar": 25.0}
        score, state, _ = rules.evaluate_lost_circulation(normal_feats, well_id=well_id)
        assert score < 0.20
        assert state == "LOW"

        # Inject single extreme spike (noise burst)
        noisy_spike = {"delta_flow": -180.0, "pit_slope": -0.03, "fg_margin_bar": 2.0}
        spike_score, spike_state, _ = rules.evaluate_lost_circulation(noisy_spike, well_id=well_id)
        # MUST NOT immediately trigger HIGH alert due to debouncing
        assert spike_state != "HIGH"
        assert spike_score <= 0.35

        # Return to normal: must immediately clear counter
        clean_feats = {"delta_flow": 5.0, "pit_slope": 0.0, "fg_margin_bar": 25.0}
        clear_score, clear_state, _ = rules.evaluate_lost_circulation(clean_feats, well_id=well_id)
        assert clear_score < 0.20
        assert clear_state == "LOW"

    def test_persistent_lost_circulation_triggers_and_hysteresis_clears(self):
        rules = BaselineHazardRules(lc_persistence=3)
        well_id = "TEST-WELL-LC-PERSIST"

        hazard_feats = {"delta_flow": -120.0, "pit_slope": -0.025, "fg_margin_bar": 4.0}

        # Tick 1: Pre-alert/Guard
        s1, st1, _ = rules.evaluate_lost_circulation(hazard_feats, well_id=well_id)
        assert st1 in ["LOW", "GUARD"]

        # Tick 2: Still pending persistence
        s2, st2, _ = rules.evaluate_lost_circulation(hazard_feats, well_id=well_id)
        assert st2 in ["LOW", "GUARD"]

        # Tick 3: Persistent threshold reached -> triggers ACTIVE alert
        s3, st3, contribs = rules.evaluate_lost_circulation(hazard_feats, well_id=well_id)
        assert s3 >= 0.55
        assert st3 in ["MEDIUM", "HIGH"]
        assert contribs["persistence_ticks"] >= 3.0

        # Now test hysteresis clearing: takes 3 clear ticks to deactivate
        recovery_feats = {"delta_flow": -5.0, "pit_slope": 0.0, "fg_margin_bar": 30.0}
        _ = rules.evaluate_lost_circulation(recovery_feats, well_id=well_id)
        _ = rules.evaluate_lost_circulation(recovery_feats, well_id=well_id)
        s_rec, st_rec, _ = rules.evaluate_lost_circulation(recovery_feats, well_id=well_id)
        assert st_rec == "LOW"
        assert s_rec < 0.25

    def test_kick_rules_debouncing(self):
        rules = BaselineHazardRules(kick_persistence=3)
        well_id = "TEST-WELL-KICK"

        influx_feats = {"delta_flow": 120.0, "pit_slope": 0.03, "pp_margin_bar": 2.0}
        # 1 tick does not trigger HIGH
        s1, st1, _ = rules.evaluate_kick(influx_feats, well_id=well_id)
        assert st1 != "HIGH"

        # 3 ticks triggers HIGH
        rules.evaluate_kick(influx_feats, well_id=well_id)
        s3, st3, contribs = rules.evaluate_kick(influx_feats, well_id=well_id)
        assert st3 in ["MEDIUM", "HIGH"]
        assert s3 >= 0.55
        assert "delta_flow_lpm" in contribs

    def test_washout_rules_debouncing(self):
        rules = BaselineHazardRules(washout_persistence=4)
        well_id = "TEST-WELL-WASHOUT"

        wo_feats = {"spp_slope": -0.15, "delta_flow": 5.0, "pit_slope": 0.0}
        # 1 tick
        _, st1, _ = rules.evaluate_washout(wo_feats, well_id=well_id)
        assert st1 != "HIGH"

        # 4 ticks
        for _ in range(3):
            s4, st4, contribs = rules.evaluate_washout(wo_feats, well_id=well_id)
        assert s4 >= 0.55
        assert st4 in ["MEDIUM", "HIGH"]
        assert contribs["spp_slope_bar_s"] == -0.15


class TestAnomalyDetector:
    """Tests Part B unsupervised anomaly detection."""

    def test_anomaly_detector_training_and_scoring(self):
        detector = DrillingAnomalyDetector(contamination=0.08)

        # Generate synthetic normal training data
        normal_samples = []
        for i in range(80):
            normal_samples.append({
                "delta_flow": 0.0 + (i % 5) * 0.5,
                "pit_slope": 0.0001 * (i % 3),
                "standpipe_pressure_bar": 180.0 + (i % 4),
                "torque_kn_m": 12.0 + (i % 3) * 0.2,
                "rop_m_hr": 15.0 + (i % 5) * 0.3,
            })

        meta = detector.fit(normal_samples)
        assert meta["is_fitted"] is True
        assert meta["training_samples"] == 80

        # Normal query should yield low anomaly score
        normal_query = {
            "delta_flow": 1.0,
            "pit_slope": 0.0,
            "standpipe_pressure_bar": 181.0,
            "torque_kn_m": 12.1,
            "rop_m_hr": 15.2,
        }
        score_norm, is_anom_norm = detector.score(normal_query)
        assert 0.0 <= score_norm <= 0.45
        assert is_anom_norm is False

        # Severe outlier query should yield elevated anomaly score
        severe_query = {
            "delta_flow": -350.0,
            "pit_slope": -0.12,
            "standpipe_pressure_bar": 40.0,
            "torque_kn_m": 45.0,
            "rop_m_hr": 95.0,
        }
        score_anom, is_anom = detector.score(severe_query)
        assert score_anom > score_norm
        assert score_anom >= 0.50


class TestXGBoostHazardClassifier:
    """Tests Part C & D supervised multiclass classifier."""

    def test_xgboost_fit_and_prediction(self):
        classifier = XGBoostHazardClassifier(n_estimators=40, max_depth=3)

        # Prepare simple multi-class training data
        train_features = []
        train_labels = []

        classes = ["NORMAL", "LOST_CIRCULATION", "STUCK_PIPE", "KICK", "TORQUE_DRAG", "WASHOUT"]
        for c in classes:
            for _ in range(15):
                f = {
                    "delta_flow": -120.0 if c == "LOST_CIRCULATION" else (100.0 if c == "KICK" else 0.0),
                    "pit_slope": -0.03 if c == "LOST_CIRCULATION" else (0.02 if c == "KICK" else 0.0),
                    "overpull_kn": 60.0 if c == "STUCK_PIPE" else 0.0,
                    "stick_slip_index": 0.85 if c == "TORQUE_DRAG" else 0.05,
                    "spp_slope": -0.15 if c == "WASHOUT" else 0.0,
                    "standpipe_pressure_bar": 120.0 if c == "WASHOUT" else 190.0,
                    "telemetry_quality": 0.98,
                }
                train_features.append(f)
                train_labels.append(c)

        fit_res = classifier.fit(train_features, train_labels)
        assert fit_res["is_fitted"] is True
        assert fit_res["train_samples"] == len(train_features)
        assert len(fit_res["top_features"]) > 0

        # Predict probabilities on a test point
        probs = classifier.predict_probabilities({
            "delta_flow": -150.0,
            "pit_slope": -0.04,
            "standpipe_pressure_bar": 190.0,
            "telemetry_quality": 0.95,
        })

        assert "LOST_CIRCULATION" in probs
        assert "NORMAL" in probs
        assert probs["LOST_CIRCULATION"] > probs["NORMAL"]
        total_p = sum(probs.values())
        assert 0.95 <= total_p <= 1.05


class TestRiskFusionEngine:
    """Tests Part G, H, I, J canonical output contract and contributors."""

    def test_risk_fusion_output_structure_and_contributors(self):
        fusion = RiskFusionEngine()

        features = {
            "delta_flow": -80.0,
            "pit_slope": -0.02,
            "fg_margin_bar": 3.0,
            "telemetry_quality": 0.95,
        }

        fused = fusion.fuse(
            well_id="NHK-TEST-001",
            timestamp="2026-09-28T02:00:00Z",
            md_m=3218.4,
            tvdss_m=3012.8,
            formation_name="Tipam Sandstone",
            xi=0.63,
            features=features,
            historical_offset_events={"LOST_CIRCULATION": 2},
        )

        # Part H Contract Checks
        assert fused["well_id"] == "NHK-TEST-001"
        assert fused["md"] == 3218.4
        assert fused["tvdss"] == 3012.8
        assert fused["formation"] == "Tipam Sandstone"
        assert fused["xi"] == 0.63
        assert "hazards" in fused

        # Check all 6 hazards are present
        hazards = fused["hazards"]
        for h_name in ["lost_circulation", "stuck_pipe", "kick", "torque_drag", "cementing", "washout"]:
            assert h_name in hazards
            h = hazards[h_name]
            assert "score" in h
            assert "state" in h
            assert "confidence" in h
            assert "contributors" in h
            assert 0.0 <= h["score"] <= 1.0
            assert h["state"] in ["LOW", "MEDIUM", "HIGH"]
            assert 0.0 <= h["confidence"] <= 1.0

        # Part I Contributors Check: numerical values present
        lc_contribs = hazards["lost_circulation"]["contributors"]
        assert "delta_flow_lpm" in lc_contribs
        assert "pit_slope_m3_min" in lc_contribs
        assert "anomaly_score" in lc_contribs
        assert "historical_score" in lc_contribs

        # Part J Data Quality Check
        dq = fused["data_quality"]
        assert "overall_quality" in dq
        assert "channel_quality" in dq
        assert "missingness" in dq
        assert "staleness_s" in dq
        assert dq["sensor_health"] == "EXCELLENT"


class TestRealTimeRiskInferenceService:
    """Tests Part L & M online streaming and sub-second latency."""

    def test_realtime_inference_stream_latency(self):
        service = RealTimeRiskInferenceService()

        # Simulated live telemetry envelope
        envelope = {
            "well_id": "NHK-SIM-001",
            "timestamp": "2026-09-28T02:00:00Z",
            "depth": {"md_m": 2550.0, "tvd_m": 2500.0, "tvdss_m": 2480.0},
            "formation": {"name": "Barail Sandstone", "xi": 0.45},
            "channels": {
                "flow_in_lpm": 2200.0,
                "flow_out_lpm": 2200.0,
                "standpipe_pressure_bar": 195.0,
                "pit_volume_m3": 45.0,
                "torque_kn_m": 14.0,
                "rpm": 110.0,
                "rop_m_hr": 18.0,
                "wob_kn": 85.0,
                "hookload_kn": 840.0,
            },
            "derived": {"ecd_gcc": 1.28, "d_exponent": 1.45},
            "data_quality": {"overall": 1.0},
        }

        # Measure processing latency
        t0 = time.perf_counter()
        result = service.process_telemetry_point(envelope)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Assert contract and latency
        assert result["well_id"] == "NHK-SIM-001"
        assert "hazards" in result
        assert result["hazards"]["lost_circulation"]["state"] in ["LOW", "MEDIUM", "HIGH"]

        # Latency requirement: Part M specifies target < 1000 ms.
        # Our implementation must comfortably beat 100 ms in unit tests.
        assert latency_ms < 100.0, f"Inference took {latency_ms:.2f} ms (expected < 100 ms)"

    def test_model_serialization_and_loading(self, tmp_path):
        """Tests that both anomaly and XGBoost models serialize to disk and restore faithfully."""
        anom = DrillingAnomalyDetector()
        anom.fit([{"delta_flow": 0.0, "torque_kn_m": 12.0} for _ in range(30)])

        anom_path = tmp_path / "anom.joblib"
        anom.save(anom_path)
        assert anom_path.exists()

        restored_anom = DrillingAnomalyDetector()
        assert restored_anom.load(anom_path) is True
        assert restored_anom._is_fitted is True

        # Test XGBoost serialization
        xgb = XGBoostHazardClassifier(n_estimators=10)
        xgb_feats = [{"delta_flow": 0.0, "torque_kn_m": 12.0} for _ in range(10)] + [
            {"delta_flow": -100.0, "torque_kn_m": 22.0} for _ in range(10)
        ]
        xgb_lbls = ["NORMAL" for _ in range(10)] + ["LOST_CIRCULATION" for _ in range(10)]
        xgb.fit(xgb_feats, xgb_lbls)

        xgb_path = tmp_path / "xgb.joblib"
        xgb.save(xgb_path)
        assert xgb_path.exists()

        restored_xgb = XGBoostHazardClassifier()
        assert restored_xgb.load(xgb_path) is True
        assert restored_xgb._is_fitted is True
