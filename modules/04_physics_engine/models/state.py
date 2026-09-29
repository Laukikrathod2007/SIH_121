"""
Physics Engine -- Internal Engineering State.

This module defines the simulator's internal "ground truth" -- the state
object the physics engine integrates forward in time -- and the inputs
that drive it (formation properties, operator commands, active fault
parameter perturbations).

Per Module 5 section 9, this state is NOT exposed directly to telemetry.
The sensor layer (see services/sensors.py) observes it and adds
measurement effects (noise/bias/delay/drift/dropout/quantization).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass
class FormationParams:
    """
    One formation's mechanical/hydraulic/pressure properties.
    Values are demo parameters per Module 5 section 12 unless a real
    source is wired in -- provenance is tracked at the catalog level,
    not per-instance, since formations are shared reference data.
    """

    name: str
    top_tvdss_m: float
    base_tvdss_m: float

    rock_density_gcc: float = 2.25
    ucs_mpa: float = 35.0
    youngs_modulus_gpa: float = 8.0
    poisson_ratio: float = 0.25

    porosity: float = 0.18
    permeability_md: float = 120.0

    pore_pressure_gradient_gcc: float = 1.00
    fracture_gradient_gcc: float = 1.55

    friction_coefficient: float = 0.25
    leakoff_coefficient: float = 0.02

    # Drillability: higher = softer/faster to drill (used by the ROP model)
    drillability_coefficient: float = 1.0

    @property
    def thickness_m(self) -> float:
        return self.base_tvdss_m - self.top_tvdss_m

    def contains(self, tvdss_m: float) -> bool:
        return self.top_tvdss_m <= tvdss_m < self.base_tvdss_m

    def pore_pressure_pa(self, tvdss_m: float, g: float = 9.80665) -> float:
        """P_pore(depth) = pore_pressure_gradient(g/cc) * g * depth(m), Pa."""
        rho = self.pore_pressure_gradient_gcc * 1000.0  # kg/m3
        return rho * g * max(tvdss_m, 0.0)

    def fracture_pressure_pa(self, tvdss_m: float, g: float = 9.80665) -> float:
        """P_fracture(depth) = fracture_gradient(g/cc) * g * depth(m), Pa."""
        rho = self.fracture_gradient_gcc * 1000.0
        return rho * g * max(tvdss_m, 0.0)


@dataclass
class OperatorInputs:
    """Surface controls the operator (or a scripted test) sets each step."""

    wob_kn: float = 80.0            # Weight on bit, kN
    rpm: float = 100.0              # Surface RPM
    flow_in_lpm: float = 2000.0     # Pump rate, L/min
    mud_weight_gcc: float = 1.20    # Active mud weight, g/cc


@dataclass
class ActiveFault:
    """
    A currently-applied fault/scenario perturbation. Faults modify
    *parameters* consumed by the physics equations (see services/faults.py);
    they never write directly to telemetry/sensor output.
    """

    scenario: str
    start_md_m: float
    severity: float = 1.0  # 0..1+ multiplier applied to the fault's effect
    # Parameter multipliers applied on top of the active formation's base
    # properties while this fault is active. Keys match FormationParams
    # field names (e.g. "leakoff_coefficient", "friction_coefficient").
    parameter_multipliers: dict = field(default_factory=dict)
    seed: Optional[int] = None


@dataclass
class SimulationState:
    """
    The simulator's complete internal ground truth at one instant.
    Mutated in place by `DrillingPhysicsEngine.step()`.
    """

    # Time
    sim_time_s: float = 0.0
    step_count: int = 0

    # Depth / trajectory
    md_m: float = 0.0
    tvd_m: float = 0.0
    tvdss_m: float = 0.0
    inclination_deg: float = 0.0
    azimuth_deg: float = 0.0

    # Drilling mechanics
    rop_m_hr: float = 0.0
    torque_kn_m: float = 0.0
    mse_mpa: float = 0.0
    hookload_kn: float = 0.0

    # Torsional dynamics (stick-slip state)
    bit_rpm: float = 0.0
    twist_angle_rad: float = 0.0
    stick_slip_index: float = 0.0

    # Hydraulics
    flow_out_lpm: float = 0.0
    standpipe_pressure_bar: float = 0.0
    annular_pressure_bar: float = 0.0
    bhp_pa: float = 0.0
    ecd_gcc: float = 0.0

    # Fluid balance
    pit_volume_m3: float = 80.0

    # Hole cleaning
    cuttings_concentration: float = 0.0

    # Pressure margins (derived, stored for convenience/telemetry)
    pp_margin_pa: float = 0.0
    fg_margin_pa: float = 0.0

    # Loss/influx flow rates (m3/s), derived each step
    q_loss_m3s: float = 0.0
    q_influx_m3s: float = 0.0

    # Active formation name and stratigraphic coordinate
    formation_name: Optional[str] = None
    xi: float = 0.0

    # Additional mechanical & environmental channels
    overpull_kn: float = 0.0
    d_exponent: float = 1.0
    temperature_c: float = 50.0

    # Currently active faults (by scenario id)
    active_faults: list = field(default_factory=list)

    def clone(self) -> "SimulationState":
        return replace(self, active_faults=list(self.active_faults))
