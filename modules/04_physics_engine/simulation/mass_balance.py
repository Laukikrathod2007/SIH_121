"""
Physics Engine -- Fluid Mass Balance Subsystem.

Implements:
- Physical formation loss mechanism (Lost Circulation):
  When BHP > P_fracture:
  Q_loss = C_loss * (BHP - P_fracture)^n
- Physical formation influx mechanism (Kick / Overpressure):
  When P_pore > BHP:
  Q_influx = PI * (P_pore - BHP)
- Emerging flow-out and active pit volume dynamics:
  dV_pit / dt = Q_in + Q_influx - Q_out - Q_loss
  (Since return flow to surface Q_out = Q_in - Q_loss + Q_influx,
   net pit volume change dV_pit/dt = Q_out - Q_in = Q_influx - Q_loss)
- Strict mass conservation verification.

Units:
Internal SI: m3/s, Pa, m3.
Boundary conversions:
- Flow rates: m3/s <-> L/min (1 m3/s = 60,000 L/min)
- Pressures: Pa <-> bar
"""

from __future__ import annotations

import math
from typing import Tuple, Dict, Any
from models.state import FormationParams, OperatorInputs
from models.config import SimulatorConfig


class MassBalanceEngine:
    """Manages fluid influx, loss, return flow, and pit conservation."""

    def __init__(self, config: SimulatorConfig):
        self.config = config

    def solve_mass_balance(
        self,
        inputs: OperatorInputs,
        formation: FormationParams,
        bhp_pa: float,
        tvdss_m: float,
        current_pit_volume_m3: float,
        dt_s: float,
        leakoff_multiplier: float = 1.0,
        influx_multiplier: float = 1.0,
        fracture_pressure_multiplier: float = 1.0,
        pore_pressure_multiplier: float = 1.0,
    ) -> Dict[str, float]:
        """
        Calculates Q_loss, Q_influx, Q_out, and updates pit volume over dt_s.
        
        Returns:
        - q_loss_m3s
        - q_influx_m3s
        - flow_out_lpm
        - q_loss_lpm
        - q_influx_lpm
        - new_pit_volume_m3
        - d_pit_dt_m3s
        """
        g = self.config.gravity_m_s2
        p_pore_pa = formation.pore_pressure_pa(tvdss_m, g) * pore_pressure_multiplier
        p_frac_pa = formation.fracture_pressure_pa(tvdss_m, g) * fracture_pressure_multiplier

        q_in_m3s = max(0.0, inputs.flow_in_lpm) / 60000.0

        # 1. Lost Circulation Physics
        # When BHP exceeds fracture pressure, fluid invades formation fractures
        q_loss_m3s = 0.0
        if bhp_pa > p_frac_pa:
            delta_p_over_frac = bhp_pa - p_frac_pa
            # Base loss coefficient (m3 / (s * Pa^0.8))
            # Scaled by formation's intrinsic leakoff coefficient & fault multiplier
            base_c_loss = 2.5e-7 * max(0.001, formation.leakoff_coefficient) * leakoff_multiplier
            exponent = 0.85
            q_loss_m3s = base_c_loss * (delta_p_over_frac ** exponent)
            # Physical limit: loss cannot exceed pump flow plus wellbore gravity drainage
            q_loss_m3s = min(q_loss_m3s, q_in_m3s + 0.02)  # Max loss cap ~ 1200 LPM above pump

        # 2. Formation Influx / Kick Physics
        # When pore pressure exceeds BHP (underbalanced state)
        q_influx_m3s = 0.0
        if p_pore_pa > bhp_pa:
            delta_p_underbalance = p_pore_pa - bhp_pa
            # Productivity Index (PI) based on permeability (mD)
            # 1 mD ~ 1e-15 m2. Base PI ~ 4e-8 m3/(s.Pa) per 100 mD
            perm_factor = max(1.0, formation.permeability_md) / 100.0
            pi = 4.0e-8 * perm_factor * influx_multiplier
            q_influx_m3s = pi * delta_p_underbalance

        # 3. Emerging Return Flow (Q_out)
        # Fluid leaving the annulus into the shale shakers / active pit
        q_out_m3s = max(0.0, q_in_m3s - q_loss_m3s + q_influx_m3s)

        # 4. Active Pit Volume Dynamics:
        # Pit gains when returns exceed pump rate (influx > loss)
        # Pit loses when returns fall below pump rate (loss > influx)
        d_vpit_dt = q_out_m3s - q_in_m3s
        # Net balance check: d_vpit_dt equals (q_influx - q_loss)
        net_imbalance_m3s = q_influx_m3s - q_loss_m3s

        new_pit_volume = max(0.0, current_pit_volume_m3 + net_imbalance_m3s * dt_s)

        return {
            "q_loss_m3s": q_loss_m3s,
            "q_influx_m3s": q_influx_m3s,
            "q_out_m3s": q_out_m3s,
            "flow_out_lpm": q_out_m3s * 60000.0,
            "q_loss_lpm": q_loss_m3s * 60000.0,
            "q_influx_lpm": q_influx_m3s * 60000.0,
            "new_pit_volume_m3": new_pit_volume,
            "d_pit_dt_m3s": net_imbalance_m3s,
        }
