"""
Physics Engine -- Hydraulics Subsystem.

Implements:
- Flow velocities through drillstring and annular geometry.
- Hydrostatic bottomhole pressure using true vertical depth (TVD).
- Frictional pressure losses (drillpipe, BHA, bit nozzles, annulus).
- Standpipe Pressure (SPP).
- Dynamic Bottomhole Pressure (BHP) and Equivalent Circulating Density (ECD).
- Pressure window analysis: Pore Pressure margin and Fracture Gradient margin.
- Hydraulic washouts (drillstring pressure drop anomalies).

Units:
Internal SI: Pa, m, s, kg/m3, m3/s.
Boundary conversions:
- Flow rate: L/min <-> m3/s (1 m3/s = 60,000 L/min)
- Pressure: Pa <-> bar (1 bar = 100,000 Pa)
- Density: kg/m3 <-> g/cc (1 g/cc = 1,000 kg/m3)
"""

from __future__ import annotations

import math
from typing import Tuple, Dict, Any
from models.state import FormationParams, OperatorInputs
from models.config import SimulatorConfig


class HydraulicsEngine:
    """Solves wellbore fluid mechanics, pressures, losses, and circulating margins."""

    def __init__(self, config: SimulatorConfig):
        self.config = config

    def solve_hydraulics(
        self,
        inputs: OperatorInputs,
        formation: FormationParams,
        md_m: float,
        tvd_m: float,
        tvdss_m: float,
        cuttings_concentration: float = 0.0,
        washout_severity: float = 0.0,
        choke_pressure_bar: float = 0.0,
        pore_pressure_multiplier: float = 1.0,
        fracture_pressure_multiplier: float = 1.0,
    ) -> Dict[str, float]:
        """
        Solves complete hydraulic state for current timestep.
        
        Returns a dictionary containing:
        - flow_velocity_annulus_m_s
        - hydrostatic_pa
        - friction_pipe_pa
        - friction_bit_pa
        - friction_annulus_pa
        - spp_bar
        - annular_pressure_bar
        - bhp_pa
        - bhp_bar
        - ecd_gcc
        - pp_margin_bar
        - fg_margin_bar
        """
        g = self.config.gravity_m_s2
        dh_m = self.config.hole_diameter_m
        dp_od_m = self.config.pipe_od_m
        # Drillpipe inner diameter ~ 4.276 inches (0.1086 m) for 5-inch 19.5 lb/ft pipe
        dp_id_m = 0.1086
        a_pipe_id_m2 = (math.pi / 4.0) * (dp_id_m ** 2)
        a_annulus_m2 = self.config.annulus_area_m2
        hyd_diam_annulus_m = dh_m - dp_od_m

        # Convert inputs to internal SI units
        q_in_m3s = max(0.0, inputs.flow_in_lpm) / 60000.0
        rho_mud_kg_m3 = max(800.0, inputs.mud_weight_gcc * 1000.0)

        # 1. Flow Velocities
        v_pipe_m_s = q_in_m3s / max(1e-4, a_pipe_id_m2)
        v_annulus_m_s = q_in_m3s / max(1e-4, a_annulus_m2)

        # 2. Hydrostatic Pressure at bit
        # Ph = rho * g * TVD (TVD in meters)
        effective_tvd_m = max(1.0, tvd_m)
        p_hydrostatic_pa = rho_mud_kg_m3 * g * effective_tvd_m

        if q_in_m3s <= 1e-6:
            # Pumps off / static well condition
            p_annular_friction_pa = 0.0
            p_bit_pa = 0.0
            p_pipe_friction_pa = 0.0
            spp_pa = 0.0
            bhp_pa = p_hydrostatic_pa + (choke_pressure_bar * 100000.0)
            ecd_gcc = bhp_pa / (g * effective_tvd_m * 1000.0)
            p_pore_pa = formation.pore_pressure_pa(tvdss_m, g)
            p_frac_pa = formation.fracture_pressure_pa(tvdss_m, g)

            return {
                "flow_velocity_annulus_m_s": 0.0,
                "hydrostatic_pa": p_hydrostatic_pa,
                "friction_pipe_pa": 0.0,
                "friction_bit_pa": 0.0,
                "friction_annulus_pa": 0.0,
                "spp_bar": 0.0,
                "annular_pressure_bar": (p_hydrostatic_pa / 100000.0) + choke_pressure_bar,
                "bhp_pa": bhp_pa,
                "bhp_bar": bhp_pa / 100000.0,
                "ecd_gcc": ecd_gcc,
                "pp_margin_bar": (bhp_pa - p_pore_pa) / 100000.0,
                "fg_margin_bar": (p_frac_pa - bhp_pa) / 100000.0,
            }

        # 3. Frictional Pressure Drops along well length L = MD
        effective_md_m = max(1.0, md_m)
        f_pipe = 0.018  # Smooth steel pipe friction factor
        f_annulus = 0.024 * (1.0 + 2.0 * cuttings_concentration)  # Annular friction factor affected by cuttings

        # DeltaP_pipe = f * (L / D) * (rho * v^2 / 2)
        p_pipe_friction_pa = f_pipe * (effective_md_m / dp_id_m) * (rho_mud_kg_m3 * (v_pipe_m_s ** 2) / 2.0)
        p_annular_friction_pa = f_annulus * (effective_md_m / hyd_diam_annulus_m) * (rho_mud_kg_m3 * (v_annulus_m_s ** 2) / 2.0)

        # 4. Bit Pressure Loss: DeltaP_bit = K_bit * Q^2
        # Standard 3x 12/32" bit nozzles Total Flow Area (TFA) ~ 0.33 in2 (0.000213 m2)
        # Washout opens up nozzle/tool area, dropping bit pressure loss significantly!
        tfa_m2 = 0.000213 * (1.0 + 1.5 * max(0.0, washout_severity))
        cd = 0.95
        # DeltaP_bit = (rho * Q^2) / (2 * Cd^2 * TFA^2)
        p_bit_pa = (rho_mud_kg_m3 * (q_in_m3s ** 2)) / (2.0 * (cd ** 2) * (tfa_m2 ** 2))

        # 5. Standpipe Pressure (SPP):
        # SPP = DeltaP_surface + DeltaP_pipe + DeltaP_bha + DeltaP_bit + DeltaP_annulus
        # BHA and surface piping lumped as ~15% of pipe friction
        p_bha_pa = 0.15 * p_pipe_friction_pa
        total_spp_pa = p_pipe_friction_pa + p_bha_pa + p_bit_pa + p_annular_friction_pa
        spp_bar = total_spp_pa / 100000.0

        # 6. Bottomhole Pressure (BHP) and Annular Pressure:
        # BHP = Ph + DeltaP_annulus + P_choke
        p_choke_pa = choke_pressure_bar * 100000.0
        bhp_pa = p_hydrostatic_pa + p_annular_friction_pa + p_choke_pa
        bhp_bar = bhp_pa / 100000.0

        # Annular pressure observed at MWD/sensor depth near bit
        annular_pressure_bar = bhp_bar

        # 7. Equivalent Circulating Density (ECD):
        # ECD = BHP / (g * TVD)
        ecd_gcc = bhp_pa / (g * effective_tvd_m * 1000.0)

        # 8. Pressure Margins against Formation Pore & Fracture Pressures
        p_pore_pa = formation.pore_pressure_pa(tvdss_m, g) * pore_pressure_multiplier
        p_frac_pa = formation.fracture_pressure_pa(tvdss_m, g) * fracture_pressure_multiplier

        pp_margin_bar = (bhp_pa - p_pore_pa) / 100000.0
        fg_margin_bar = (p_frac_pa - bhp_pa) / 100000.0

        return {
            "flow_velocity_annulus_m_s": v_annulus_m_s,
            "hydrostatic_pa": p_hydrostatic_pa,
            "friction_pipe_pa": p_pipe_friction_pa,
            "friction_bit_pa": p_bit_pa,
            "friction_annulus_pa": p_annular_friction_pa,
            "spp_bar": max(0.0, spp_bar),
            "annular_pressure_bar": max(0.0, annular_pressure_bar),
            "bhp_pa": bhp_pa,
            "bhp_bar": max(0.0, bhp_bar),
            "ecd_gcc": max(0.0, ecd_gcc),
            "pp_margin_bar": pp_margin_bar,
            "fg_margin_bar": fg_margin_bar,
        }
