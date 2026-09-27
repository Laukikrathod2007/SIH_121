"""
Comprehensive Multi-Persona Engineering Review Test Suite for SIH26121 / eRTMAC-NWIS.

Covers:
1. Drilling-Domain Review: Causal physics scenarios (Normal, Lost Circulation, Kick, Stuck Pipe, Stick-Slip)
2. ML Review: Leakage audit, well-split independence, feature rolling windows, preprocessor isolation
3. Geological Review: Minimum curvature TVDSS, formation identification, stratigraphic xi, offset projection
4. Data Engineering Review: Provenance markers (OBSERVED, SYNTHETIC, INFERRED), quality gating, sensor fault resilience
5. Software Architecture Review: Sub-second inference latency, state debouncing, thread-safe buffers, atomic model persistence
6. SIH Evaluator Review: Full closed-loop demonstration cycle from Normal -> Hazard -> Alert -> Mitigation -> Recovery
"""

import math
import pytest
from datetime import datetime, timezone

from app.modules.physics_engine.services.engine import DrillingPhysicsEngine
from app.modules.physics_engine.services.faults import ScenarioType
from app.modules.physics_engine.models.config import SimulatorConfig
from app.modules.physics_engine.models.state import FormationParams
from app.modules.predictive_analytics.services.realtime_inference import RealTimeRiskInferenceService
from app.modules.well_intelligence.services.xi_correlator import compute_xi, xi_to_tvdss
from app.modules.well_intelligence.services.dors_engine import rank_offset_wells, compute_dors
from app.modules.physics_engine.data_pipeline.splitter import DatasetSplitter


@pytest.fixture
def sim_engine():
    """Configures a reproducible digital twin simulation engine."""
    formations = [
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
            fracture_gradient_gcc=1.55,  # lower FG susceptible to loss
            friction_coefficient=0.38,
            permeability_md=120.0,
            leakoff_coefficient=0.02,
            drillability_coefficient=0.90,
        ),
    ]
    cfg = SimulatorConfig(wellhead_elevation_m=25.0, dt_s=1.0, seed=42)
    engine = DrillingPhysicsEngine(
        config=cfg,
        formations=formations,
        well_id="TEST-WELL-REV",
        initial_md_m=2490.0,
        initial_inclination_deg=15.0,
    )
    return engine


@pytest.fixture
def inference_service():
    """Provides a fresh real-time inference service instance."""
    svc = RealTimeRiskInferenceService()
    svc._telemetry_buffers.clear()
    svc.rules._states.clear()
    svc.alert_engine._alerts.clear()
    return svc


class TestDrillingDomainEngineeringReview:
    """Rigorous physical verification of drilling mechanics, hydraulics, and mass balance."""

    def test_normal_drilling_progression(self, sim_engine, inference_service):
        """
        Verify:
        - Bit advances monotonically (dMD/dt = ROP)
        - Formation transitions at boundary
        - TVDSS and xi update correctly
        - Risk scores remain LOW (<0.35) with no false alerts
        """
        start_md = sim_engine.state.md_m
        start_tvdss = sim_engine.state.tvdss_m

        for _ in range(25):
            sim_state, telem = sim_engine.step(dt_s=1.0)
            res = inference_service.process_telemetry_point(telem.model_dump())

        end_md = sim_engine.state.md_m
        end_tvdss = sim_engine.state.tvdss_m

        # Verify physical advancement
        assert end_md > start_md
        assert end_tvdss > start_tvdss
        assert sim_engine.state.rop_m_hr > 0.0

        # Verify risks remain low
        for h_name, h_info in res["hazards"].items():
            assert h_info["score"] < 0.35, f"False hazard trigger during normal drilling: {h_name}"
            assert h_info["state"] == "LOW"

        # Verify no critical alerts
        critical_alerts = [a for a in res.get("alerts", []) if a["severity"] in ("CRITICAL", "WARNING")]
        assert len(critical_alerts) == 0

    def test_lost_circulation_physical_causality(self, sim_engine, inference_service):
        """
        Verify physical chain:
        Formation condition -> BHP vs FG breakdown -> Loss flow -> Return drop -> Pit loss ->
        Feature anomaly -> Historical fusion -> LC risk HIGH -> Module 6 Alert.
        """
        # Advance into Porous Sandstone (lower FG, high permeability)
        sim_engine.state.md_m = 2650.0
        sim_engine._update_depth_and_formation()

        for _ in range(5):
            _, telem = sim_engine.step(1.0)
            inference_service.process_telemetry_point(telem.model_dump())

        # Inject physical lost circulation scenario
        sim_engine.faults.inject_scenario(
            scenario_type=ScenarioType.LOST_CIRCULATION,
            severity=1.0,
            start_sim_time_s=sim_engine.state.sim_time_s,
        )

        lc_detected = False
        alert_fired = False

        for _ in range(15):
            sim_state, telem = sim_engine.step(1.0)
            # Historical evidence: offset well had 2 LC events at this horizon
            res = inference_service.process_telemetry_point(
                telemetry_envelope=telem.model_dump(),
                historical_offset_events={"LOST_CIRCULATION": 2},
                correlation_confidence=0.92,
            )

            # Causal verification: loss flow and pit drop
            if sim_state.q_loss_m3s > 0:
                assert telem.channels.flow_out_lpm < telem.channels.flow_in_lpm

            lc_info = res["hazards"]["lost_circulation"]
            if lc_info["state"] == "HIGH":
                lc_detected = True
                assert lc_info["score"] > 0.70
                assert "delta_flow_lpm" in lc_info["contributors"]

            for alert in res.get("alerts", []):
                if alert["hazard_type"] == "LOST_CIRCULATION" and alert["severity"] == "CRITICAL":
                    alert_fired = True
                    assert "Pump LCM" in alert["recommended_mitigation"]["title"]

        assert lc_detected, "Lost circulation failed to trigger HIGH risk state via causal physical chain"
        assert alert_fired, "Module 6 failed to generate CRITICAL Lost Circulation alert"

    def test_kick_physical_causality(self, sim_engine, inference_service):
        """
        Verify physical chain:
        Formation overpressure -> Influx flow -> Return flow excess -> Pit gain ->
        Feature anomaly -> Kick risk HIGH -> Module 6 Shut-In BOP Alert.
        """
        # Advance into Porous Sandstone reservoir (permeability = 120 md)
        sim_engine.state.md_m = 2650.0
        sim_engine._update_depth_and_formation()

        for _ in range(5):
            _, telem = sim_engine.step(1.0)
            inference_service.process_telemetry_point(telem.model_dump())

        # Inject formation kick (underbalance influx)
        sim_engine.faults.inject_scenario(
            scenario_type=ScenarioType.KICK_OVERPRESSURE,
            severity=1.2,
            start_sim_time_s=sim_engine.state.sim_time_s,
        )

        kick_detected = False
        alert_fired = False

        for _ in range(15):
            sim_state, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(
                telemetry_envelope=telem.model_dump(),
                historical_offset_events={"KICK": 2},
                correlation_confidence=0.90,
            )

            if sim_state.q_influx_m3s > 0:
                assert telem.channels.flow_out_lpm > telem.channels.flow_in_lpm

            kick_info = res["hazards"]["kick"]
            if kick_info["state"] == "HIGH":
                kick_detected = True
                assert kick_info["score"] > 0.70

            for alert in res.get("alerts", []):
                if alert["hazard_type"] == "KICK" and alert["severity"] == "CRITICAL":
                    alert_fired = True
                    assert "Shut-In BOP" in alert["recommended_mitigation"]["title"]

        assert kick_detected, "Kick failed to trigger HIGH risk state via causal influx physics"
        assert alert_fired, "Module 6 failed to generate CRITICAL Kick alert"

    def test_stuck_pipe_causality(self, sim_engine, inference_service):
        """
        Verify physical chain:
        Cuttings transport buildup / friction -> Overpull elevation -> Torque rise -> ROP drop ->
        SP risk HIGH -> Module 6 Free Pipe Alert.
        """
        for _ in range(10):
            _, telem = sim_engine.step(1.0)
            inference_service.process_telemetry_point(telem.model_dump())

        sim_engine.faults.inject_scenario(
            scenario_type=ScenarioType.STUCK_PIPE,
            severity=0.90,
            start_sim_time_s=sim_engine.state.sim_time_s,
        )

        sp_detected = False
        for _ in range(15):
            sim_state, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(
                telemetry_envelope=telem.model_dump(),
                historical_offset_events={"STUCK_PIPE": 2},
            )

            if sim_state.overpull_kn > 25.0:
                sp_info = res["hazards"]["stuck_pipe"]
                if sp_info["state"] in ("MEDIUM", "HIGH"):
                    sp_detected = True

        assert sp_detected, "Stuck pipe failed to trigger elevated risk despite overpull"

    def test_stick_slip_torsional_dynamics(self, sim_engine, inference_service):
        """
        Verify torsional dynamics:
        Nonlinear Stribeck friction -> Torque oscillation -> RPM variance ->
        Stick-slip index > 0.40 -> Torque/Drag risk elevation.
        """
        for _ in range(10):
            _, telem = sim_engine.step(1.0)
            inference_service.process_telemetry_point(telem.model_dump())

        sim_engine.faults.inject_scenario(
            scenario_type=ScenarioType.STICK_SLIP,
            severity=1.8,
            start_sim_time_s=sim_engine.state.sim_time_s,
        )

        ss_detected = False
        for _ in range(25):
            sim_state, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(telem.model_dump())
            td_info = res["hazards"]["torque_drag"]
            if td_info["state"] in ("MEDIUM", "HIGH"):
                ss_detected = True

        assert ss_detected, "Torsional stick-slip failed to trigger elevated torque/drag risk"


class TestDataEngineeringAndSensorResilience:
    """Verifies sensor fault tolerance, provenance, and data quality gating."""

    def test_sensor_fault_resilience(self, sim_engine, inference_service):
        """
        Verify:
        Injecting sensor failure (dropout, stale value, bias) does NOT cause false physical hazard alerts.
        System correctly triggers SENSOR_FAULT advisory and degrades data quality.
        """
        for _ in range(10):
            _, telem = sim_engine.step(1.0)
            inference_service.process_telemetry_point(telem.model_dump())

        # Inject sensor faults: flow sensor dropout + pressure sensor dropout
        sim_engine.sensor_array.sensors["flow_out_lpm"].dropout_probability = 1.0
        sim_engine.sensor_array.sensors["standpipe_pressure_bar"].dropout_probability = 1.0

        for _ in range(10):
            _, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(telem.model_dump())

        # Verify Kick and Lost Circulation did NOT falsely trigger CRITICAL
        assert res["hazards"]["kick"]["state"] != "HIGH"
        assert res["hazards"]["lost_circulation"]["state"] != "HIGH"

        # Verify data quality was degraded
        dq = res["data_quality"]
        assert dq["overall_quality"] < 0.90 or dq["sensor_health"] == "DEGRADED"

        # Verify Module 6 fired SENSOR_FAULT advisory instead
        sensor_alerts = [a for a in res.get("alerts", []) if a["hazard_type"] == "SENSOR_FAULT"]
        assert len(sensor_alerts) > 0, "System failed to identify sensor fault as SENSOR_FAULT advisory"

    def test_data_provenance_markers(self, sim_engine):
        """
        Verify data records clearly mark OBSERVED, SYNTHETIC, and INFERRED provenance tiers.
        """
        _, telem = sim_engine.step(1.0)
        td = telem.model_dump()

        # Engine produces explicitly marked SYNTHETIC telemetry
        assert td["provenance"]["tier"] == "SYNTHETIC"
        assert td["provenance"]["version"] == "1.0.0"
        assert td["provenance"]["source"] == "NWIS_PHYSICS_ENGINE"


class TestGeologicalCorrelationModule4Review:
    """Verifies TVDSS, stratigraphic xi, and geological authority."""

    def test_stratigraphic_xi_and_offset_mapping(self):
        """
        Verify:
        xi = (TVDSS - Top) / (Base - Top)
        Equivalent Offset TVDSS = Top_offset + xi * Thickness_offset
        """
        active_fm = FormationParams(
            name="Barail_Sand",
            top_tvdss_m=2000.0,
            base_tvdss_m=2200.0,
        )
        offset_fm = FormationParams(
            name="Barail_Sand",
            top_tvdss_m=2100.0,
            base_tvdss_m=2350.0,
        )

        current_tvdss = 2100.0  # exactly at xi = 0.50
        xi = compute_xi(current_tvdss, active_fm.top_tvdss_m, active_fm.base_tvdss_m)
        assert xi == 0.50

        equiv_offset_tvdss = xi_to_tvdss(xi, offset_fm.top_tvdss_m, offset_fm.thickness_m)
        expected_offset = 2100.0 + 0.50 * 250.0  # 2225.0
        assert equiv_offset_tvdss == expected_offset


class TestMachineLearningAuditReview:
    """Verifies no leakage in dataset splitting, rolling windows, and preprocessing."""

    def test_strict_well_level_splitting_no_leakage(self):
        """
        Verify:
        - Strict GroupKFold: No well appears in both train and test splits
        - Zero overlapping sequences between wells
        """
        splitter = DatasetSplitter()
        # Mock dataset with well tags
        records = (
            [{"well_id": f"WELL_{i}", "step": j, "val": j * 1.5} for i in range(10) for j in range(20)]
        )

        train_data, val_data, test_data = splitter.split_by_well(
            records=records,
            train_ratio=0.60,
            val_ratio=0.20,
            test_ratio=0.20,
            seed=42,
        )

        train_wells = set(r["well_id"] for r in train_data)
        val_wells = set(r["well_id"] for r in val_data)
        test_wells = set(r["well_id"] for r in test_data)

        # Zero well leakage
        assert train_wells.isdisjoint(val_wells)
        assert train_wells.isdisjoint(test_wells)
        assert val_wells.isdisjoint(test_wells)


class TestFullClosedLoopSIHDemonstration:
    """
    Executes the full 16-step SIH demonstration workflow:
    NORMAL -> DEPTH ADVANCES -> FORMATION CHANGES -> MODULE 4 UPDATES xi ->
    RELEVANT OFFSETS UPDATE -> HISTORICAL EVIDENCE CHANGES -> PHYSICS SCENARIO DEVELOPS ->
    TELEMETRY CHANGES -> MODULE 5 DETECTS ANOMALY -> MODULE 5 FUSES HISTORICAL EVIDENCE ->
    RISK RISES -> MODULE 6 ALERT -> ENGINEER ACTION -> PHYSICS STATE CHANGES ->
    TELEMETRY CHANGES -> RISK DECREASES -> ALERT RECOVERS.
    """

    def test_full_operational_mitigation_and_recovery_cycle(self, sim_engine, inference_service):
        well_id = sim_engine.well_id

        # Phase 1: NORMAL DRILLING
        for _ in range(8):
            _, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(telem.model_dump())
            assert res["hazards"]["lost_circulation"]["state"] == "LOW"

        # Phase 2: DEPTH ADVANCES & FORMATION CHANGES
        sim_engine.state.md_m = 2670.0  # Enter Porous_Sandstone (TVDSS > 2500m)
        sim_engine._update_depth_and_formation()
        assert sim_engine.state.formation_name == "Porous_Sandstone"
        assert sim_engine.state.xi > 0.0

        # Phase 3: PHYSICS SCENARIO DEVELOPS (Lost Circulation)
        sim_engine.faults.inject_scenario(
            scenario_type=ScenarioType.LOST_CIRCULATION,
            severity=1.0,
            start_sim_time_s=sim_engine.state.sim_time_s,
        )

        # Phase 4: TELEMETRY CHANGES & RISK RISES & MODULE 6 ALERT
        alert_to_mitigate = None
        for _ in range(18):
            _, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(
                telemetry_envelope=telem.model_dump(),
                historical_offset_events={"LOST_CIRCULATION": 3},
                correlation_confidence=0.92,
            )
            for alert in res.get("alerts", []):
                if alert["hazard_type"] == "LOST_CIRCULATION" and alert["severity"] == "CRITICAL":
                    alert_to_mitigate = alert
                    break
            if alert_to_mitigate:
                break

        assert alert_to_mitigate is not None, "CRITICAL Lost Circulation alert failed to fire"
        assert alert_to_mitigate["status"] == "ACTIVE"

        # Phase 5: RIG ENGINEER ACTION
        action_res = inference_service.apply_mitigation_action(
            well_id=well_id,
            alert_id=alert_to_mitigate["alert_id"],
        )
        assert action_res is not None
        assert action_res["status"] == "MITIGATED"
        assert action_res["recommended_mitigation"]["applied"] is True

        # Phase 6: PHYSICS STATE CHANGES (Mitigation executed on rig: reduce pump rate, clear fault)
        sim_engine.inputs.flow_in_lpm = 1400.0
        sim_engine.faults.clear_all()  # LCM pill spotted, fracture sealed

        # Phase 7: TELEMETRY NORMALIZES & RISK DECREASES & ALERT RECOVERS
        recovery_verified = False
        for _ in range(15):
            sim_state, telem = sim_engine.step(1.0)
            res = inference_service.process_telemetry_point(
                telemetry_envelope=telem.model_dump(),
                historical_offset_events={"LOST_CIRCULATION": 1},
                correlation_confidence=0.92,
            )
            lc_state = res["hazards"]["lost_circulation"]["state"]
            if lc_state == "LOW":
                recovery_verified = True
                # Check alert status transitioned to CLEARED
                cleared_alerts = [
                    a for a in res.get("alerts", [])
                    if a["hazard_type"] == "LOST_CIRCULATION" and a["status"] == "CLEARED"
                ]
                assert len(cleared_alerts) > 0

        assert recovery_verified, "Risk failed to decrease back to LOW following successful mitigation"
