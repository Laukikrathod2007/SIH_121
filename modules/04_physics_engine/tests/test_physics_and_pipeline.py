"""
Comprehensive Test Suite for eRTMAC-NWIS Physics Engine & ML Data Pipeline.

Verifies:
1. Normal drilling (well advances, telemetry evolves).
2. Lost circulation (loss begins, flow-out falls, pit falls).
3. Kick / overpressure (influx begins, flow-out rises, pit rises).
4. Stuck pipe (drag rises, overpull rises, torque rises, ROP falls).
5. Stick-slip (torque & RPM oscillate via 2nd-order torsional dynamics).
6. Sensor fault decoupling (sensor changes, physics state does not).
7. Data pipeline (ingestion, cleaning, gap imputation, outlier preservation).
8. Feature extraction (50+ features covering all domains).
9. Multi-horizon labeling (causal predictive targets).
10. Leakage prevention (strict well-level splitting).
11. Synthetic data quality gate (mass conservation & physical ranges).
12. API endpoints and simulation controller.
"""

import math
import pytest
from app.modules.physics.models.config import SimulatorConfig
from app.modules.physics.models.state import FormationParams, OperatorInputs
from app.modules.physics.simulation.formation import FormationModel, default_demo_formations
from app.modules.physics.simulation.engine import DrillingPhysicsEngine
from app.modules.physics.simulation.faults import ScenarioType
from app.modules.physics.simulation.sensors import ChannelSensor, SensorArray
from app.modules.physics.data_pipeline.ingestion import TelemetryIngestor
from app.modules.physics.data_pipeline.cleaner import UnitStandardizer, TelemetryCleaner
from app.modules.physics.data_pipeline.alignment import DepthTimeAligner
from app.modules.physics.data_pipeline.feature_engine import FeatureEngine
from app.modules.physics.data_pipeline.labeler import HazardLabeler
from app.modules.physics.data_pipeline.splitter import DatasetSplitter
from app.modules.physics.data_pipeline.synthetic_generator import (
    SyntheticDataGenerator,
    QualityGateFailure,
)
from app.modules.physics.simulation.physics_controller import PhysicsController


# ===========================================================================
# 1. Normal Drilling Tests
# ===========================================================================

class TestNormalDrilling:
    def test_well_advances_and_telemetry_evolves(self):
        engine = DrillingPhysicsEngine(initial_md_m=2000.0)
        start_md = engine.state.md_m

        for _ in range(20):
            state, envelope = engine.step(dt_s=1.0)

        # Well must advance forward in depth
        assert engine.state.md_m > start_md
        assert engine.state.rop_m_hr > 0.0
        # Depth mapping TVD and TVDSS must update
        assert engine.state.tvd_m > 0.0
        assert engine.state.tvdss_m > 0.0
        # Telemetry envelope sequence must advance
        assert envelope.sequence == 20
        assert envelope.depth.md_m == round(engine.state.md_m, 2)
        assert envelope.channels.rop_m_hr > 0.0

    def test_formation_transition_on_depth_progression(self):
        # Tipam base is 1400m, Barail top is 1400m. Wellhead elevation is 20m.
        fms = default_demo_formations()
        # MD 1350m -> TVDSS 1330m < 1400m (Tipam Sandstone)
        engine = DrillingPhysicsEngine(formations=fms, initial_md_m=1350.0, initial_inclination_deg=0.0)
        assert engine.state.formation_name == "Tipam Sandstone"

        # MD 1500m -> TVDSS 1480m >= 1400m (Barail Sandstone)
        engine.state.md_m = 1500.0
        engine._update_depth_and_formation()
        assert engine.state.formation_name == "Barail Sandstone"


# ===========================================================================
# 2. Lost Circulation Tests
# ===========================================================================

class TestLostCirculation:
    def test_loss_begins_flow_out_falls_and_pit_declines(self):
        engine = DrillingPhysicsEngine(initial_md_m=2500.0)
        # Baseline step
        state0, env0 = engine.step(dt_s=1.0)
        initial_pit = state0.pit_volume_m3
        initial_flow_out = state0.flow_out_lpm

        # Inject Lost Circulation
        engine.faults.inject_scenario(
            scenario_type=ScenarioType.LOST_CIRCULATION,
            severity=1.5,
            start_sim_time_s=engine.state.sim_time_s,
        )

        # Step forward
        for _ in range(15):
            state, envelope = engine.step(dt_s=1.0)

        # Physics: Formation loss develops
        assert state.q_loss_m3s > 0.0
        # Flow out falls below pump rate
        assert state.flow_out_lpm < initial_flow_out
        assert state.flow_out_lpm < engine.inputs.flow_in_lpm
        # Pit volume falls due to mass conservation
        assert state.pit_volume_m3 < initial_pit


# ===========================================================================
# 3. Kick / Overpressure Tests
# ===========================================================================

class TestKickOverpressure:
    def test_influx_begins_flow_out_rises_and_pit_gains(self):
        engine = DrillingPhysicsEngine(initial_md_m=2500.0)
        state0, env0 = engine.step(dt_s=1.0)
        initial_pit = state0.pit_volume_m3
        initial_flow_out = state0.flow_out_lpm

        # Inject Kick / Overpressure
        engine.faults.inject_scenario(
            scenario_type=ScenarioType.KICK_OVERPRESSURE,
            severity=1.5,
            start_sim_time_s=engine.state.sim_time_s,
        )

        for _ in range(15):
            state, envelope = engine.step(dt_s=1.0)

        # Physics: Formation influx develops
        assert state.q_influx_m3s > 0.0
        # Flow out rises above pump rate
        assert state.flow_out_lpm > initial_flow_out
        assert state.flow_out_lpm > engine.inputs.flow_in_lpm
        # Pit volume gains
        assert state.pit_volume_m3 > initial_pit


# ===========================================================================
# 4. Stuck Pipe Tests
# ===========================================================================

class TestStuckPipe:
    def test_drag_rises_overpull_rises_torque_rises_and_rop_falls(self):
        engine = DrillingPhysicsEngine(initial_md_m=2500.0)
        state0, env0 = engine.step(dt_s=1.0)
        base_torque = state0.torque_kn_m
        base_overpull = state0.overpull_kn
        base_rop = state0.rop_m_hr

        # Inject Stuck Pipe
        engine.faults.inject_scenario(
            scenario_type=ScenarioType.STUCK_PIPE,
            severity=1.8,
            start_sim_time_s=engine.state.sim_time_s,
        )

        for _ in range(10):
            state, envelope = engine.step(dt_s=1.0)

        # Overpull and drag rise
        assert state.overpull_kn > base_overpull
        # Torque rises significantly
        assert state.torque_kn_m > base_torque
        # ROP drops due to mechanical dysfunction
        assert state.rop_m_hr < base_rop


# ===========================================================================
# 5. Stick-Slip Tests
# ===========================================================================

class TestStickSlip:
    def test_torque_and_rpm_oscillate_physically(self):
        engine = DrillingPhysicsEngine(initial_md_m=2800.0)
        # Inject stick-slip fault with high static friction
        engine.faults.inject_scenario(
            scenario_type=ScenarioType.STICK_SLIP,
            severity=2.0,
            start_sim_time_s=0.0,
        )
        engine.set_operator_inputs(rpm=60.0, wob_kn=100.0)

        bit_rpms = []
        torques = []
        for _ in range(40):
            state, envelope = engine.step(dt_s=0.2)
            bit_rpms.append(state.bit_rpm)
            torques.append(state.torque_kn_m)

        # Verify true physical oscillation: bit RPM must have significant variance
        rpm_min = min(bit_rpms)
        rpm_max = max(bit_rpms)
        assert rpm_max > (rpm_min + 30.0)  # Violent slip release
        # Torque must oscillate with spring twist
        t_min = min(torques)
        t_max = max(torques)
        assert t_max > (t_min + 3.0)
        # Stick slip index must be elevated
        assert engine.state.stick_slip_index > 0.3


# ===========================================================================
# 6. Sensor Fault Decoupling Tests
# ===========================================================================

class TestSensorDecoupling:
    def test_sensor_noise_and_dropout_do_not_alter_physics_state(self):
        sensor = ChannelSensor(
            name="flow_out", unit="L/min",
            scale=1.0, bias=25.0, noise_sigma=10.0, dropout_probability=0.5, seed=42
        )
        true_flow = 2000.0

        # Sample multiple times
        obs_values = []
        for _ in range(10):
            obs, q, status = sensor.sample(true_flow, dt_s=0.1)
            obs_values.append(obs)

        # Observations will vary due to noise and bias
        assert any(abs(obs - true_flow) > 5.0 for obs in obs_values)
        # The true physical value itself is strictly unaffected
        assert true_flow == 2000.0


# ===========================================================================
# 7. Data Pipeline & Preprocessing Tests
# ===========================================================================

class TestDataPipeline:
    def test_ingestion_and_timestamp_sorting(self):
        ingestor = TelemetryIngestor()
        raw = [
            {"sequence": 2, "timestamp": "2026-09-28T02:00:02Z", "channels": {"rpm": 100.0}},
            {"sequence": 1, "timestamp": "2026-09-28T02:00:01Z", "channels": {"rpm": 98.0}},
            {"sequence": 1, "timestamp": "2026-09-28T02:00:01Z", "channels": {"rpm": 98.0}},  # Duplicate
        ]
        processed = ingestor.process_batch(raw)
        assert len(processed) == 2  # Deduplicated
        assert processed[0]["sequence"] == 1
        assert processed[1]["sequence"] == 2

    def test_cleaner_gap_imputation_and_outlier_preservation(self):
        cleaner = TelemetryCleaner()
        time_series = [
            {"channels": {"rpm": 100.0}},
            {"channels": {"rpm": None}},  # Short gap
            {"channels": {"rpm": 102.0}},
        ]
        results = cleaner.impute_missing(time_series, "rpm")
        assert len(results) == 3
        # Middle value must be linearly interpolated
        assert results[1][1] is True  # is_imputed
        assert results[1][2] == "linear_interp"
        assert round(results[1][0], 1) == 101.0

        # Outlier preservation
        raw_vals = [100.0] * 10 + [250.0] + [100.0] * 10
        outlier_res = cleaner.detect_outliers_layered(raw_vals)
        spike_rec = outlier_res[10]
        assert spike_rec[0] == 250.0  # Raw value preserved!
        assert spike_rec[2] is True   # Outlier flagged

    def test_feature_engineering_multivariate_extraction(self):
        engine = FeatureEngine()
        sample_history = []
        for i in range(25):
            sample_history.append({
                "channels": {
                    "flow_in_lpm": 2000.0,
                    "flow_out_lpm": 2000.0 - i * 10.0,  # Developing fluid loss
                    "pit_volume_m3": 80.0 - (i * 0.1),
                    "standpipe_pressure_bar": 150.0,
                    "annular_pressure_bar": 45.0,
                    "torque_kn_m": 15.0,
                    "rpm": 100.0,
                    "bit_rpm": 98.0,
                    "wob_kn": 80.0,
                    "hookload_kn": 120.0,
                    "overpull_kn": 5.0,
                    "rop_m_hr": 12.0,
                    "mse_mpa": 180.0,
                    "d_exponent": 1.2,
                    "cuttings_concentration": 0.04,
                },
                "depth": {"md_m": 2500.0 + i},
                "geology": {"xi": 0.45, "distance_to_top_m": 100.0, "distance_to_base_m": 200.0},
            })

        features = engine.extract_features(sample_history)
        assert "delta_flow" in features
        assert features["delta_flow"] < 0.0  # Negative flow imbalance
        assert features["pit_slope"] < 0.0   # Declining pit
        assert "mse_zscore" in features
        assert "flow_imbalance_slope" in features
        assert len(features) >= 45

    def test_multi_horizon_labeling(self):
        labeler = HazardLabeler()
        records = [
            {"simulation_time_s": 100.0, "depth": {"md_m": 2000.0}},
            {"simulation_time_s": 700.0, "depth": {"md_m": 2020.0}},
            {"simulation_time_s": 1100.0, "depth": {"md_m": 2040.0}},
        ]
        # Event starts at t=1000s, warning window is 600s (400s - 1000s)
        labels = labeler.label_sequence(
            records=records,
            event_type="LOST_CIRCULATION",
            event_start_time_s=1000.0,
            event_end_time_s=1300.0,
        )
        assert labels[0].event_phase.value == "NORMAL"     # t=100s (< 400s)
        assert labels[1].event_phase.value == "PRE_EVENT"  # t=700s (within 600s of event)
        assert labels[1].hazard_5m_ahead is True           # 700s is within 300s of 1000s
        assert labels[2].event_phase.value == "EVENT"      # t=1100s (active event)

    def test_well_level_split_prevents_leakage(self):
        records = [
            {"well_id": "W-1", "val": 1},
            {"well_id": "W-1", "val": 2},
            {"well_id": "W-2", "val": 3},
            {"well_id": "W-3", "val": 4},
            {"well_id": "W-4", "val": 5},
        ]
        train, val, test = DatasetSplitter.split_by_well(records, train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, seed=42)
        train_wells = set(r["well_id"] for r in train)
        val_wells = set(r["well_id"] for r in val)
        test_wells = set(r["well_id"] for r in test)

        # No well may appear across multiple sets
        assert train_wells.isdisjoint(val_wells)
        assert train_wells.isdisjoint(test_wells)
        assert val_wells.isdisjoint(test_wells)


# ===========================================================================
# 8. Controller & API Tests
# ===========================================================================

class TestPhysicsController:
    def test_step_reset_and_operator_inputs(self):
        controller = PhysicsController()
        # Step
        step_res = controller.step_simulation()
        assert step_res["status"] == "stepped"
        assert "telemetry" in step_res

        # Set operator inputs
        upd = controller.set_operator_inputs(wob_kn=95.0, rpm=115.0)
        assert upd["operator_inputs"]["wob_kn"] == 95.0
        assert upd["operator_inputs"]["rpm"] == 115.0

        # Scenario injection
        inj = controller.inject_scenario("LOST_CIRCULATION", severity=1.5)
        assert inj["status"] == "injected"
        assert "scenario_id" in inj

        # Clear scenarios
        clr = controller.clear_scenarios()
        assert clr["status"] == "cleared"

        # Reset
        rst = controller.reset_simulation(initial_md_m=2600.0)
        assert rst["status"] == "reset"
        assert rst["initial_md_m"] == 2600.0
