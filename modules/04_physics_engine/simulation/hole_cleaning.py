"""
Physics Engine -- Hole Cleaning & Cuttings Transport Subsystem.

Implements:
- Volumetric cuttings generation rate: Q_cuttings ~ A_bit * ROP * (1 - porosity)
- Cuttings slip velocity (Chien / Moore correlation for drilling fluids)
- Net annular cuttings transport velocity: v_transport = v_annulus - v_slip
- Dynamic solids concentration C_c(t) in the annulus:
  d(C_c)/dt = (Q_cuttings - v_transport * A_annulus * C_c) / V_annulus
- Transport margin and cuttings bed accumulation
- Feedforward impact on annular friction and mechanical torque & drag.

Units:
Internal SI: m3/s, m/s, m3, dimensionless concentration [0..1].
"""

from __future__ import annotations

import math
from typing import Dict, Any
from app.modules.physics.models.state import FormationParams
from app.modules.physics.models.config import SimulatorConfig


class HoleCleaningEngine:
    """Models cuttings generation, annular transport, solids buildup, and cleaning efficiency."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        # Typical average drilled cuttings diameter ~ 3.5 mm (0.0035 m)
        self.cuttings_diameter_m = 0.0035
        # Cuttings density ~ 2600 kg/m3 (rock density)
        self.rock_density_kg_m3 = 2600.0

    def calculate_cuttings_transport(
        self,
        rop_m_hr: float,
        v_annulus_m_s: float,
        formation: FormationParams,
        mud_weight_gcc: float,
        current_concentration: float,
        md_m: float,
        dt_s: float,
        cuttings_slip_multiplier: float = 1.0,
    ) -> Dict[str, float]:
        """
        Advances annular hole cleaning state over dt_s.
        
        Returns:
        - cuttings_generation_rate_m3s
        - slip_velocity_m_s
        - net_transport_velocity_m_s
        - new_cuttings_concentration
        - transport_margin
        - bed_thickness_fraction
        """
        ab_m2 = self.config.bit_area_m2
        a_annulus_m2 = self.config.annulus_area_m2
        g = self.config.gravity_m_s2
        rho_fluid = max(800.0, mud_weight_gcc * 1000.0)
        rho_rock = max(1800.0, formation.rock_density_gcc * 1000.0)

        # 1. Cuttings Generation Rate:
        # Q_cuttings = A_bit * ROP * (1 - porosity)
        rop_m_s = max(0.0, rop_m_hr) / 3600.0
        solids_fraction = max(0.2, 1.0 - formation.porosity)
        q_gen_m3s = ab_m2 * rop_m_s * solids_fraction

        # 2. Cuttings Particle Slip Velocity
        # Chien correlation simplified for turbulent/laminar transition
        # v_slip ~ sqrt( (4/3) * g * d_p * (rho_rock - rho_fluid) / (rho_fluid * C_drag) )
        delta_rho = max(100.0, rho_rock - rho_fluid)
        # In drilling mud with yield stress, apparent viscosity retards slip:
        # Nominal slip velocity for 3-4mm cuttings in 10-12 ppg mud is ~ 0.15 - 0.35 m/s
        base_v_slip = 0.22 * math.sqrt(delta_rho / 1400.0) * cuttings_slip_multiplier
        v_slip_m_s = max(0.05, base_v_slip)

        # 3. Net Transport Velocity
        # In vertical to moderately inclined well, net transport = v_annulus - v_slip
        v_transport_m_s = v_annulus_m_s - v_slip_m_s

        # Transport Margin: ratio of fluid velocity to slip velocity
        # If > 1.5, good cleaning; if < 1.0, cuttings accumulate / fall backward
        transport_margin = v_annulus_m_s / max(0.01, v_slip_m_s)

        # 4. Annular Volume
        effective_depth_m = max(50.0, md_m)
        v_annulus_m3 = a_annulus_m2 * effective_depth_m

        # 5. Differential Conservation of Solids in Annular Column:
        # Rate of change = Solids entering at bit - Solids exiting at surface
        if v_transport_m_s > 0.0:
            q_out_solids = v_transport_m_s * a_annulus_m2 * current_concentration
        else:
            q_out_solids = 0.0  # Cuttings are settling downhole!

        d_conc_dt = (q_gen_m3s - q_out_solids) / max(1.0, v_annulus_m3)
        new_conc = current_concentration + d_conc_dt * dt_s

        # Physics bounds: solids concentration between 0.0 and maximum packing limit (0.35)
        new_conc = max(0.0, min(0.35, new_conc))

        # Stationary cuttings bed indicator (develops when transport margin < 1.0 and conc > 0.08)
        bed_indicator = max(0.0, min(1.0, (new_conc - 0.05) / 0.15))

        return {
            "cuttings_generation_rate_m3s": q_gen_m3s,
            "slip_velocity_m_s": v_slip_m_s,
            "net_transport_velocity_m_s": v_transport_m_s,
            "new_cuttings_concentration": round(new_conc, 4),
            "transport_margin": round(transport_margin, 2),
            "bed_thickness_fraction": round(bed_indicator, 3),
        }
