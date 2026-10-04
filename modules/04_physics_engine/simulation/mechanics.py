"""
Physics Engine -- Mechanics Subsystem.

Implements:
- Reduced-order ROP with physical saturation (no infinite asymptotic growth).
- Drillstring Torque & Drag (normal contact force, friction, overpull).
- Mechanical Specific Energy (MSE).
- Corrected d-exponent.

Units:
Internal SI: N, m, s, Pa, N.m, rad/s.
Boundary conversions:
- ROP: m/s -> m/hr
- Torque: N.m -> kN.m
- WOB: kN -> N
- Hookload: N -> kN
- MSE: Pa -> MPa
"""

from __future__ import annotations

import math
from typing import Tuple
from app.modules.physics.models.state import FormationParams, OperatorInputs
from app.modules.physics.models.config import SimulatorConfig


class MechanicsEngine:
    """Solves drilling mechanics, ROP, torque, hookload, MSE, and d-exponent."""

    def __init__(self, config: SimulatorConfig):
        self.config = config

    def calculate_rop(
        self,
        inputs: OperatorInputs,
        formation: FormationParams,
        cuttings_concentration: float = 0.0,
        bit_wear_factor: float = 1.0,
        dysfunction_factor: float = 1.0,
    ) -> float:
        """
        Calculates ROP (m/hr) with physical saturation.
        
        ROP_raw = alpha * RPM * (WOB / D_b)^b * formation_factor * dysfunction
        where formation_factor = drillability / (UCS / UCS_ref)
        
        Physical saturation:
        ROP = ROP_max * tanh(ROP_raw / ROP_max)
        Prevents physically absurd infinite penetration rates.
        """
        wob_kn = max(0.0, inputs.wob_kn)
        rpm = max(0.0, inputs.rpm)

        if wob_kn < 1.0 or rpm < 1.0:
            return 0.0

        # Calibratable coefficients
        alpha = 0.0085  # Base bit-rock penetration coefficient
        b = 1.15        # WOB non-linearity exponent
        db_m = self.config.bit_diameter_m

        # Formation hardness resistance factor (reference UCS = 30 MPa)
        ucs_factor = max(5.0, formation.ucs_mpa) / 30.0
        drillability = max(0.1, formation.drillability_coefficient)
        formation_factor = drillability / ucs_factor

        # Hole cleaning dysfunction: excessive cuttings in annulus dampen ROP
        cleaning_factor = max(0.2, 1.0 - 1.5 * max(0.0, cuttings_concentration - 0.05))

        # Raw ROP in m/hr
        wob_db_ratio = (wob_kn / (db_m * 100.0)) ** b
        rop_raw_m_hr = (
            alpha
            * rpm
            * wob_db_ratio
            * formation_factor
            * bit_wear_factor
            * cleaning_factor
            * max(0.1, dysfunction_factor)
        )

        # Upper asymptotic saturation threshold based on rock strength
        # Harder rock limits peak mechanical rock shearing rate
        rop_max_m_hr = max(10.0, 60.0 / ucs_factor)

        # Soft physical saturation using tanh
        rop_m_hr = rop_max_m_hr * math.tanh(rop_raw_m_hr / rop_max_m_hr)
        return max(0.0, rop_m_hr)

    def calculate_torque_and_hookload(
        self,
        inputs: OperatorInputs,
        formation: FormationParams,
        md_m: float,
        inclination_deg: float,
        cuttings_concentration: float = 0.0,
        friction_multiplier: float = 1.0,
        cuttings_drag_multiplier: float = 1.0,
    ) -> Tuple[float, float, float]:
        """
        Calculates surface torque (kN.m), hookload (kN), and overpull (kN).
        
        Couples drillstring weight, contact normal force, wellbore inclination,
        and cuttings bed buildup:
        F_friction = mu * N
        T_friction = F_friction * r_pipe
        Total Torque = T_bit + T_friction
        """
        db_m = self.config.bit_diameter_m
        dp_od_m = self.config.pipe_od_m
        r_pipe_m = dp_od_m / 2.0
        g = self.config.gravity_m_s2

        # 1. Bit-Rock Interaction Torque (kN.m)
        # T_bit = (1/3) * mu_bit * WOB * D_bit
        mu_bit = formation.friction_coefficient * 1.2
        wob_kn = max(0.0, inputs.wob_kn)
        t_bit_kn_m = (1.0 / 3.0) * mu_bit * wob_kn * db_m

        # 2. Drillstring Weight & Buoyancy
        # Drillpipe linear mass ~ 30 kg/m for 5-inch pipe
        # BHA (bottom 150m) ~ 120 kg/m
        bha_length_m = min(150.0, md_m)
        pipe_length_m = max(0.0, md_m - bha_length_m)
        air_weight_n = (pipe_length_m * 30.0 + bha_length_m * 120.0) * g

        # Buoyancy factor
        mud_density_gcc = max(1.0, inputs.mud_weight_gcc)
        steel_density_gcc = 7.85
        buoyancy_factor = max(0.6, 1.0 - (mud_density_gcc / steel_density_gcc))
        buoyed_weight_kn = (air_weight_n * buoyancy_factor) / 1000.0

        # 3. Normal Contact Force N along wellbore
        inc_rad = math.radians(inclination_deg)
        sin_inc = math.sin(inc_rad)
        cos_inc = math.cos(inc_rad)

        # Normal force increases in deviated wells due to gravity contact on low side
        n_contact_kn = buoyed_weight_kn * sin_inc + 0.05 * buoyed_weight_kn * cos_inc

        # 4. Friction & Drag Force: F_friction = mu * N
        base_mu = formation.friction_coefficient * friction_multiplier
        # Cuttings accumulation increases wall friction significantly
        cuttings_penalty = 1.0 + 3.0 * (cuttings_concentration ** 1.5) * cuttings_drag_multiplier
        effective_mu = base_mu * cuttings_penalty

        f_drag_kn = effective_mu * n_contact_kn

        # 5. Torsional friction from drillstring wall contact (kN.m)
        t_friction_kn_m = f_drag_kn * r_pipe_m

        # Total surface torque
        total_torque_kn_m = t_bit_kn_m + t_friction_kn_m

        # Hookload: W_buoyed - WOB + Overpull/Drag
        # In rotary drilling, axial drag is a fraction of total drag due to rotation
        rpm = max(1.0, inputs.rpm)
        axial_drag_fraction = 1.0 / (1.0 + (rpm / 30.0))
        axial_drag_kn = f_drag_kn * axial_drag_fraction

        overpull_kn = axial_drag_kn
        hookload_kn = max(0.0, buoyed_weight_kn - wob_kn + axial_drag_kn)

        return total_torque_kn_m, hookload_kn, overpull_kn

    def calculate_mse(
        self,
        wob_kn: float,
        torque_kn_m: float,
        rpm: float,
        rop_m_hr: float,
    ) -> float:
        """
        Calculates Mechanical Specific Energy (MSE) in MPa.
        
        MSE = WOB / A_bit + (2 * pi * RPM * Torque) / (A_bit * ROP)
        
        Properly handles low/zero ROP edge cases to prevent division by zero.
        """
        ab_m2 = self.config.bit_area_m2
        wob_n = wob_kn * 1000.0
        torque_n_m = torque_kn_m * 1000.0

        axial_component_pa = wob_n / max(1e-4, ab_m2)

        if rop_m_hr <= 0.05 or rpm <= 0.1:
            # When stationary or barely moving, rotary work is dissipated as friction
            # Bounded static baseline
            return (axial_component_pa + 1e7) / 1e6

        rop_m_s = rop_m_hr / 3600.0
        omega_rad_s = (2.0 * math.pi * rpm) / 60.0

        rotary_component_pa = (torque_n_m * omega_rad_s) / (ab_m2 * rop_m_s)
        total_mse_pa = axial_component_pa + rotary_component_pa

        # Convert Pa to MPa and cap at physical ceiling (e.g. 5000 MPa)
        mse_mpa = min(5000.0, total_mse_pa / 1e6)
        return max(0.0, mse_mpa)

    def calculate_d_exponent(
        self,
        rop_m_hr: float,
        rpm: float,
        wob_kn: float,
        mud_weight_gcc: float,
        normal_pore_pressure_gcc: float = 1.0,
    ) -> float:
        """
        Calculates corrected d-exponent (d_c).
        
        Standard Jordan & Shirley relation:
        d = log10( ROP / (60 * RPM) ) / log10( 12 * WOB / (10^6 * D_bit) )
        d_c = d * (normal_pore_pressure_gradient / actual_mud_weight)
        """
        rop_ft_hr = rop_m_hr * 3.28084
        wob_klbf = (wob_kn * 0.224809)  # kN to klbf
        db_in = self.config.bit_diameter_m * 39.3701  # m to in
        rpm_val = max(1.0, rpm)

        if rop_ft_hr <= 0.01 or wob_klbf <= 0.1:
            return 1.0

        try:
            num = math.log10(rop_ft_hr / (60.0 * rpm_val))
            denom = math.log10(wob_klbf / (1000.0 * db_in))
            if abs(denom) < 1e-4:
                return 1.0
            d = num / denom
            # Correct for mud weight overbalance
            mw = max(0.8, mud_weight_gcc)
            d_c = d * (normal_pore_pressure_gcc / mw)
            # Clip to physical reasonable limits [0.2 .. 3.5]
            return max(0.2, min(3.5, d_c))
        except (ValueError, ZeroDivisionError):
            return 1.0
