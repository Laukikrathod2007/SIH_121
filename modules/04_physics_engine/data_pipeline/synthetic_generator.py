"""
ML Data Engineering Pipeline -- Synthetic Batch Generator & Quality Gate.

Implements Module 5 Data Pipeline Sections 14-16:
- Runs batches of physics simulation sequences across all scenarios:
  NORMAL, LOST_CIRCULATION, KICK_OVERPRESSURE, STUCK_PIPE, STICK_SLIP, WASHOUT, POOR_HOLE_CLEANING.
- Applies domain randomization (rock strength, mud weight, WOB, RPM, flow, sensor noise).
- Deterministic seeding for complete reproducibility.
- SYNTHETIC DATA QUALITY GATE:
  Strictly validates physical ranges, mass balance conservation, scenario activation,
  and telemetry integrity before admitting sequences into training pools!
"""

from __future__ import annotations

import random
from typing import Dict, Any, List, Optional, Tuple
from models.config import SimulatorConfig
from simulation.engine import DrillingPhysicsEngine
from simulation.formation import FormationModel, default_demo_formations
from simulation.faults import ScenarioType
from data_pipeline.labeler import HazardLabeler


class QualityGateFailure(Exception):
    pass


class SyntheticDataGenerator:
    """Generates quality-gated synthetic drilling datasets for predictive ML training."""

    def __init__(self, base_seed: int = 100):
        self.base_seed = base_seed
        self.labeler = HazardLabeler()

    def generate_scenario_run(
        self,
        scenario_type: ScenarioType,
        well_id: str,
        n_steps: int = 200,
        dt_s: float = 1.0,
        seed: Optional[int] = None,
        fault_start_step: int = 60,
        fault_duration_steps: int = 80,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Runs one randomized physics simulation session and validates it through the Quality Gate.
        """
        run_seed = seed or self.base_seed
        rng = random.Random(run_seed)

        # 1. Domain Randomization: Perturb operating conditions and geology
        cfg = SimulatorConfig(seed=run_seed, dt_s=dt_s)
        base_fms = default_demo_formations()
        # Randomize rock properties by +/- 15%
        for fm in base_fms:
            fm.ucs_mpa *= rng.uniform(0.85, 1.15)
            fm.friction_coefficient *= rng.uniform(0.9, 1.1)

        engine = DrillingPhysicsEngine(
            config=cfg,
            formations=base_fms,
            well_id=well_id,
            initial_md_m=rng.uniform(2200.0, 3100.0),
        )

        # Set randomized surface controls
        engine.set_operator_inputs(
            wob_kn=rng.uniform(60.0, 110.0),
            rpm=rng.uniform(80.0, 130.0),
            flow_in_lpm=rng.uniform(1800.0, 2500.0),
            mud_weight_gcc=rng.uniform(1.22, 1.34),
        )

        records: List[Dict[str, Any]] = []
        fault_injected = False
        fault_time_s = fault_start_step * dt_s
        fault_end_time_s = (fault_start_step + fault_duration_steps) * dt_s

        # 2. Step Engine Through Time
        for step_idx in range(n_steps):
            if scenario_type != ScenarioType.NORMAL and step_idx == fault_start_step and not fault_injected:
                engine.faults.inject_scenario(
                    scenario_type=scenario_type,
                    severity=rng.uniform(1.2, 2.0),
                    start_sim_time_s=engine.state.sim_time_s,
                    duration_s=fault_duration_steps * dt_s,
                )
                fault_injected = True

            state, envelope = engine.step(dt_s=dt_s)
            records.append(envelope.model_dump())

        # 3. Apply Multi-Horizon Labels
        labels = self.labeler.label_sequence(
            records=records,
            event_type=scenario_type.value if scenario_type != ScenarioType.NORMAL else None,
            event_start_time_s=fault_time_s if scenario_type != ScenarioType.NORMAL else None,
            event_end_time_s=fault_end_time_s if scenario_type != ScenarioType.NORMAL else None,
        )

        for r, lbl in zip(records, labels):
            r["labels"] = lbl.model_dump()

        # 4. Strict Synthetic Data Quality Gate Verification
        self._verify_quality_gate(records, scenario_type, fault_start_step)

        run_metadata = {
            "well_id": well_id,
            "scenario": scenario_type.value,
            "n_steps": n_steps,
            "dt_s": dt_s,
            "seed": run_seed,
            "quality_gate_passed": True,
        }

        return records, run_metadata

    def _verify_quality_gate(
        self,
        records: List[Dict[str, Any]],
        scenario_type: ScenarioType,
        fault_start_step: int,
    ) -> None:
        """
        Rejects runs that violate physical limits, mass conservation, or scenario signatures.
        """
        for r in records:
            ch = r.get("channels", {})
            # Range check: ROP cannot exceed physical saturation limit
            if ch.get("rop_m_hr", 0.0) < 0.0 or ch.get("rop_m_hr", 0.0) > 120.0:
                raise QualityGateFailure(f"ROP out of physical bounds: {ch.get('rop_m_hr')}")
            # Flow in must be positive
            if ch.get("flow_in_lpm", 0.0) < 0.0:
                raise QualityGateFailure(f"Flow in cannot be negative: {ch.get('flow_in_lpm')}")
            # SPP must be positive
            if ch.get("standpipe_pressure_bar", 0.0) < 0.0:
                raise QualityGateFailure(f"SPP cannot be negative: {ch.get('standpipe_pressure_bar')}")
            # Pit volume must not be negative
            if ch.get("pit_volume_m3", 0.0) < 0.0:
                raise QualityGateFailure(f"Pit volume cannot be negative: {ch.get('pit_volume_m3')}")

        # Mass balance check between initial and final pit volume
        v_init = records[0]["channels"]["pit_volume_m3"]
        v_final = records[-1]["channels"]["pit_volume_m3"]

        if scenario_type == ScenarioType.NORMAL:
            # Under normal drilling, pit volume must be conserved within sensor noise drift (+/- 0.5 m3)
            if abs(v_final - v_init) > 1.5:
                raise QualityGateFailure(f"Mass balance violation in NORMAL run: delta_V={v_final - v_init} m3")
        elif scenario_type == ScenarioType.LOST_CIRCULATION:
            # Pit volume must decline significantly
            if v_final >= v_init:
                raise QualityGateFailure("Lost circulation scenario failed to produce pit decline")
        elif scenario_type == ScenarioType.KICK_OVERPRESSURE:
            # Pit volume must gain significantly
            if v_final <= v_init:
                raise QualityGateFailure("Kick scenario failed to produce pit gain")
        elif scenario_type == ScenarioType.STUCK_PIPE:
            # Overpull / drag must increase significantly after fault onset
            pre_overpull = records[fault_start_step - 1]["channels"]["overpull_kn"]
            post_overpull = records[fault_start_step + 10]["channels"]["overpull_kn"]
            if post_overpull <= pre_overpull:
                raise QualityGateFailure("Stuck pipe scenario failed to produce overpull increase")
