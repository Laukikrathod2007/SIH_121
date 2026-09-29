"""
Physics Engine -- Unified Reduced-Order Drilling Digital Twin Core.

Integrates all 10 subsystems into a single causal physics simulation:
1. Formation model (rock strength, pore/fracture pressure, leakoff)
2. Trajectory / geometry (MD -> TVD -> TVDSS -> Formation -> Xi)
3. Drilling mechanics (coupled WOB, RPM, rock UCS -> ROP with saturation)
4. Drillstring mechanics (normal force, wall friction, overpull, hookload)
5. Hydraulics (frictional losses, bit TFA loss, SPP, BHP, ECD, margins)
6. Mass balance (Lost Circulation, Kick influx, return flow, pit conservation)
7. Torsional dynamics (2nd-order spring-damper, nonlinear Stribeck stick-slip)
8. Hole cleaning (cuttings generation, slip velocity, annular concentration, bed buildup)
9. Fault engine (physical parameter perturbations)
10. Sensor array (noise, bias, delay, drift, dropout, quantization, quality)

Adheres strictly to the core philosophy:
Operator Controls + Formation + Mud + Drillstring + Physics Equations = Internal State
Internal State -> Sensor Model -> Telemetry Envelope
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from models.state import (
    SimulationState, FormationParams, OperatorInputs
)
from models.config import SimulatorConfig
from models.telemetry import (
    TelemetryEnvelope, TelemetryChannels, DepthRecord, FormationRecord,
    TelemetryQuality, ChannelQuality, ProvenanceTier
)
from simulation.formation import FormationModel, default_demo_formations
from simulation.mechanics import MechanicsEngine
from simulation.hydraulics import HydraulicsEngine
from simulation.mass_balance import MassBalanceEngine
from simulation.torsional_dynamics import TorsionalDynamicsEngine
from simulation.hole_cleaning import HoleCleaningEngine
from simulation.faults import FaultEngine, ScenarioType
from simulation.sensors import SensorArray


class DrillingPhysicsEngine:
    """The central reduced-order digital twin solver for Module 5."""

    def __init__(
        self,
        config: Optional[SimulatorConfig] = None,
        formations: Optional[List[FormationParams]] = None,
        well_id: str = "NHK-SIM-001",
        initial_md_m: float = 2500.0,
        initial_inclination_deg: float = 12.0,
        initial_azimuth_deg: float = 45.0,
    ):
        self.config = config or SimulatorConfig()
        self.formations = FormationModel(formations or default_demo_formations())
        self.well_id = well_id

        # Instantiate Subsystems
        self.mechanics = MechanicsEngine(self.config)
        self.hydraulics = HydraulicsEngine(self.config)
        self.mass_balance = MassBalanceEngine(self.config)
        self.torsional = TorsionalDynamicsEngine(self.config)
        self.hole_cleaning = HoleCleaningEngine(self.config)
        self.faults = FaultEngine()
        self.sensor_array = SensorArray(seed=self.config.seed)

        # Operator inputs (surface controls)
        self.inputs = OperatorInputs(
            wob_kn=85.0,
            rpm=110.0,
            flow_in_lpm=2200.0,
            mud_weight_gcc=1.28,
        )

        # Initialize internal simulation state at steady-state drilling
        self.state = SimulationState(
            md_m=initial_md_m,
            inclination_deg=initial_inclination_deg,
            azimuth_deg=initial_azimuth_deg,
            pit_volume_m3=80.0,
            bit_rpm=self.inputs.rpm,
            twist_angle_rad=1.5,
        )
        self._update_depth_and_formation()

    def set_operator_inputs(
        self,
        wob_kn: Optional[float] = None,
        rpm: Optional[float] = None,
        flow_in_lpm: Optional[float] = None,
        mud_weight_gcc: Optional[float] = None,
    ) -> None:
        """Dynamically update surface operator controls."""
        if wob_kn is not None:
            self.inputs.wob_kn = max(0.0, wob_kn)
        if rpm is not None:
            self.inputs.rpm = max(0.0, rpm)
        if flow_in_lpm is not None:
            self.inputs.flow_in_lpm = max(0.0, flow_in_lpm)
        if mud_weight_gcc is not None:
            self.inputs.mud_weight_gcc = max(0.8, mud_weight_gcc)

    def _update_depth_and_formation(self) -> None:
        """Maps MD -> TVD -> TVDSS -> Active Formation -> Xi."""
        inc_rad = math.radians(self.state.inclination_deg)
        # Simplified TVD projection: TVD = MD * cos(inc)
        self.state.tvd_m = self.state.md_m * math.cos(inc_rad)
        self.state.tvdss_m = self.state.tvd_m - self.config.wellhead_elevation_m

        fm = self.formations.at_depth(self.state.tvdss_m)
        if fm:
            self.state.formation_name = fm.name
            thickness = max(1.0, fm.thickness_m)
            self.state.xi = max(0.0, min(1.0, (self.state.tvdss_m - fm.top_tvdss_m) / thickness))
        else:
            self.state.formation_name = "Unknown"
            self.state.xi = 0.0

    def step(self, dt_s: Optional[float] = None) -> Tuple[SimulationState, TelemetryEnvelope]:
        """
        Advances the physical simulation by dt_s.
        
        Executes the coupled causal loop:
        Faults -> Multipliers
        Formation -> Mechanics & Hydraulics
        Mass Balance -> Pit & Returns
        Torsional Dynamics -> Stick-Slip
        Hole Cleaning -> Cuttings Bed
        Sensor Model -> Telemetry Envelope
        """
        dt = dt_s if dt_s is not None else self.config.dt_s
        self.state.sim_time_s += dt
        self.state.step_count += 1

        # 1. Active Formation Lookup
        active_fm = self.formations.at_depth(self.state.tvdss_m) or self.formations.formations[0]

        # 2. Evaluate Fault Parameter Multipliers
        multipliers = self.faults.evaluate_multipliers(
            sim_time_s=self.state.sim_time_s,
            md_m=self.state.md_m,
        )

        # 3. Drilling Mechanics: ROP Calculation
        rop_m_hr = self.mechanics.calculate_rop(
            inputs=self.inputs,
            formation=active_fm,
            cuttings_concentration=self.state.cuttings_concentration,
            dysfunction_factor=multipliers["dysfunction_factor"],
        )
        self.state.rop_m_hr = rop_m_hr

        # Advance Measured Depth: dMD/dt = ROP
        rop_m_s = rop_m_hr / 3600.0
        self.state.md_m += rop_m_s * dt
        self._update_depth_and_formation()

        # 4. Hydraulics Engine: Pressures, Losses, Flow Velocities
        hyd_res = self.hydraulics.solve_hydraulics(
            inputs=self.inputs,
            formation=active_fm,
            md_m=self.state.md_m,
            tvd_m=self.state.tvd_m,
            tvdss_m=self.state.tvdss_m,
            cuttings_concentration=self.state.cuttings_concentration,
            washout_severity=multipliers["washout_severity"],
            pore_pressure_multiplier=multipliers.get("pore_pressure_multiplier", 1.0),
            fracture_pressure_multiplier=multipliers.get("fracture_pressure_multiplier", 1.0),
        )
        self.state.standpipe_pressure_bar = hyd_res["spp_bar"]
        self.state.annular_pressure_bar = hyd_res["annular_pressure_bar"]
        self.state.bhp_pa = hyd_res["bhp_pa"]
        self.state.ecd_gcc = hyd_res["ecd_gcc"]
        self.state.pp_margin_pa = hyd_res["pp_margin_bar"] * 100000.0
        self.state.fg_margin_pa = hyd_res["fg_margin_bar"] * 100000.0

        # 5. Mass Balance & Fluid Exchange: Influx, Loss, Flow Out, Pit Volume
        mass_res = self.mass_balance.solve_mass_balance(
            inputs=self.inputs,
            formation=active_fm,
            bhp_pa=self.state.bhp_pa,
            tvdss_m=self.state.tvdss_m,
            current_pit_volume_m3=self.state.pit_volume_m3,
            dt_s=dt,
            leakoff_multiplier=multipliers["leakoff_multiplier"],
            influx_multiplier=multipliers["influx_multiplier"],
            pore_pressure_multiplier=multipliers.get("pore_pressure_multiplier", 1.0),
            fracture_pressure_multiplier=multipliers.get("fracture_pressure_multiplier", 1.0),
        )
        self.state.q_loss_m3s = mass_res["q_loss_m3s"]
        self.state.q_influx_m3s = mass_res["q_influx_m3s"]
        self.state.flow_out_lpm = mass_res["flow_out_lpm"]
        self.state.pit_volume_m3 = mass_res["new_pit_volume_m3"]

        # 6. Hole Cleaning & Annular Solids Transport
        clean_res = self.hole_cleaning.calculate_cuttings_transport(
            rop_m_hr=self.state.rop_m_hr,
            v_annulus_m_s=hyd_res["flow_velocity_annulus_m_s"],
            formation=active_fm,
            mud_weight_gcc=self.inputs.mud_weight_gcc,
            current_concentration=self.state.cuttings_concentration,
            md_m=self.state.md_m,
            dt_s=dt,
            cuttings_slip_multiplier=multipliers["cuttings_slip_multiplier"],
        )
        self.state.cuttings_concentration = clean_res["new_cuttings_concentration"]

        # 7. Drillstring Mechanics: Torque, Hookload, Overpull
        t_base_kn_m, hl_kn, overpull_kn = self.mechanics.calculate_torque_and_hookload(
            inputs=self.inputs,
            formation=active_fm,
            md_m=self.state.md_m,
            inclination_deg=self.state.inclination_deg,
            cuttings_concentration=self.state.cuttings_concentration,
            friction_multiplier=multipliers["friction_multiplier"],
            cuttings_drag_multiplier=multipliers["cuttings_drag_multiplier"],
        )
        self.state.hookload_kn = hl_kn
        self.state.overpull_kn = overpull_kn

        # 8. Torsional Dynamics & Stick-Slip
        tors_res = self.torsional.step(
            surface_rpm=self.inputs.rpm,
            base_torque_kn_m=t_base_kn_m,
            formation=active_fm,
            wob_kn=self.inputs.wob_kn,
            current_twist_rad=self.state.twist_angle_rad,
            current_bit_rpm=self.state.bit_rpm,
            dt_s=dt,
            damping_multiplier=multipliers["torsional_damping_multiplier"],
            static_friction_multiplier=multipliers["static_friction_multiplier"],
        )
        self.state.bit_rpm = tors_res["bit_rpm"]
        self.state.twist_angle_rad = tors_res["twist_angle_rad"]
        self.state.torque_kn_m = tors_res["dynamic_torque_kn_m"]
        self.state.stick_slip_index = tors_res["stick_slip_index"]

        # 9. Engineering Features: MSE and d-exponent
        self.state.mse_mpa = self.mechanics.calculate_mse(
            wob_kn=self.inputs.wob_kn,
            torque_kn_m=self.state.torque_kn_m,
            rpm=self.inputs.rpm,
            rop_m_hr=self.state.rop_m_hr,
        )
        self.state.d_exponent = self.mechanics.calculate_d_exponent(
            rop_m_hr=self.state.rop_m_hr,
            rpm=self.inputs.rpm,
            wob_kn=self.inputs.wob_kn,
            mud_weight_gcc=self.inputs.mud_weight_gcc,
        )

        # 10. Circulating Temperature Model
        # Geothermal gradient ~ 0.03 deg C/m from surface 25 deg C
        bottomhole_temp = 25.0 + 0.028 * self.state.tvd_m
        # Circulation cooling effect
        flow_cooling = min(15.0, (self.inputs.flow_in_lpm / 2000.0) * 10.0)
        self.state.temperature_c = max(30.0, bottomhole_temp - flow_cooling)

        # 11. Sensor Observation Layer -> Telemetry Envelope
        envelope = self._generate_telemetry_envelope(mass_res, dt)
        return self.state, envelope

    def _generate_telemetry_envelope(self, mass_res: Dict[str, float], dt_s: float) -> TelemetryEnvelope:
        """Passes internal true state through sensor array to build canonical telemetry."""
        true_dict = {
            "rop_m_hr": self.state.rop_m_hr,
            "rpm": self.inputs.rpm,
            "bit_rpm": self.state.bit_rpm,
            "wob_kn": self.inputs.wob_kn,
            "torque_kn_m": self.state.torque_kn_m,
            "hookload_kn": self.state.hookload_kn,
            "flow_in_lpm": self.inputs.flow_in_lpm,
            "flow_out_lpm": self.state.flow_out_lpm,
            "standpipe_pressure_bar": self.state.standpipe_pressure_bar,
            "annular_pressure_bar": self.state.annular_pressure_bar,
            "pit_volume_m3": self.state.pit_volume_m3,
            "mud_weight_gcc": self.inputs.mud_weight_gcc,
        }

        obs, q_scores, statuses = self.sensor_array.observe(true_dict, dt_s)
        overall_q = sum(q_scores.values()) / max(1, len(q_scores))

        channels = TelemetryChannels(
            rop_m_hr=round(obs.get("rop_m_hr", self.state.rop_m_hr), 2),
            rpm=round(obs.get("rpm", self.inputs.rpm), 1),
            bit_rpm=round(obs.get("bit_rpm", self.state.bit_rpm), 1),
            wob_kn=round(obs.get("wob_kn", self.inputs.wob_kn), 1),
            torque_kn_m=round(obs.get("torque_kn_m", self.state.torque_kn_m), 2),
            hookload_kn=round(obs.get("hookload_kn", self.state.hookload_kn), 1),
            overpull_kn=round(self.state.overpull_kn, 2),
            mse_mpa=round(self.state.mse_mpa, 1),
            d_exponent=round(self.state.d_exponent, 3),
            stick_slip_index=round(self.state.stick_slip_index, 2),
            flow_in_lpm=round(obs.get("flow_in_lpm", self.inputs.flow_in_lpm), 1),
            flow_out_lpm=round(obs.get("flow_out_lpm", self.state.flow_out_lpm), 1),
            standpipe_pressure_bar=round(obs.get("standpipe_pressure_bar", self.state.standpipe_pressure_bar), 1),
            annular_pressure_bar=round(obs.get("annular_pressure_bar", self.state.annular_pressure_bar), 1),
            bhp_bar=round(self.state.bhp_pa / 100000.0, 1),
            pit_volume_m3=round(obs.get("pit_volume_m3", self.state.pit_volume_m3), 2),
            mud_weight_gcc=round(obs.get("mud_weight_gcc", self.inputs.mud_weight_gcc), 3),
            ecd_gcc=round(self.state.ecd_gcc, 3),
            pp_margin_bar=round(self.state.pp_margin_pa / 100000.0, 2),
            fg_margin_bar=round(self.state.fg_margin_pa / 100000.0, 2),
            q_loss_lpm=round(mass_res["q_loss_lpm"], 1),
            q_influx_lpm=round(mass_res["q_influx_lpm"], 1),
            cuttings_concentration=round(self.state.cuttings_concentration, 4),
            inclination_deg=round(self.state.inclination_deg, 2),
            azimuth_deg=round(self.state.azimuth_deg, 2),
            temperature_c=round(self.state.temperature_c, 1),
        )

        active_fm = self.formations.at_depth(self.state.tvdss_m) or self.formations.formations[0]

        return TelemetryEnvelope(
            well_id=self.well_id,
            sequence=self.state.step_count,
            timestamp=datetime.now(timezone.utc).isoformat(),
            simulation_time_s=round(self.state.sim_time_s, 2),
            depth=DepthRecord(
                # md_m must round to the same precision as SimulationState.md_m
                # comparisons elsewhere (e.g. test_well_advances_and_telemetry_evolves
                # asserts envelope.depth.md_m == round(engine.state.md_m, 2)) -- a
                # 3-decimal round here made the two disagree whenever the 3rd decimal
                # was nonzero.
                md_m=round(self.state.md_m, 2),
                tvd_m=round(self.state.tvd_m, 3),
                tvdss_m=round(self.state.tvdss_m, 3),
            ),
            formation=FormationRecord(
                name=self.state.formation_name or "Unknown",
                xi=round(self.state.xi, 3),
                top_tvdss_m=round(active_fm.top_tvdss_m, 1),
                base_tvdss_m=round(active_fm.base_tvdss_m, 1),
            ),
            channels=channels,
            quality=TelemetryQuality(
                overall=round(overall_q, 3),
                channel_qualities={k: round(v, 2) for k, v in q_scores.items()},
                flagged_channels=statuses,
            ),
        )

    def reset(
        self,
        initial_md_m: float = 2500.0,
        initial_pit_volume_m3: float = 80.0,
    ) -> None:
        """Resets engine to pristine starting state and clears active scenarios."""
        self.state = SimulationState(
            md_m=initial_md_m,
            inclination_deg=self.state.inclination_deg,
            azimuth_deg=self.state.azimuth_deg,
            pit_volume_m3=initial_pit_volume_m3,
        )
        self.faults.clear_scenarios()
        self._update_depth_and_formation()
