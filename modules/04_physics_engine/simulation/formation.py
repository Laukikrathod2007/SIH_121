"""
Physics Engine -- Formation Model.

Holds an ordered catalog of FormationParams and resolves "which formation
is at this TVDSS" for the physics engine (Module 5 section 12-13, 27-28).

This is independent from Module 4's `stratigraphic_correlator.py` /
`xi_correlator.py`, which operate on real (or synthetic-testbed) well
formation-top records loaded from the data store. The physics engine
needs its own lightweight, fully parameterized formation catalog because
it must be constructible in isolation for unit tests and CLI simulation
runs without depending on the well_intelligence data store.
"""

from __future__ import annotations

from typing import List, Optional

from app.modules.physics.models.state import FormationParams


class FormationModel:
    """An ordered stack of formations, queried by TVDSS."""

    def __init__(self, formations: List[FormationParams]):
        if not formations:
            raise ValueError("FormationModel requires at least one formation")
        self.formations = sorted(formations, key=lambda f: f.top_tvdss_m)
        self._validate_no_gaps_or_overlaps()

    def _validate_no_gaps_or_overlaps(self) -> None:
        for i in range(1, len(self.formations)):
            prev = self.formations[i - 1]
            curr = self.formations[i]
            if curr.top_tvdss_m < prev.base_tvdss_m:
                raise ValueError(
                    f"Formation overlap: '{prev.name}' base={prev.base_tvdss_m} "
                    f"overlaps '{curr.name}' top={curr.top_tvdss_m}"
                )

    def at_depth(self, tvdss_m: float) -> Optional[FormationParams]:
        for fm in self.formations:
            if fm.contains(tvdss_m):
                return fm
        # Below the deepest known formation: extend the last formation's
        # properties rather than returning None, so the physics engine
        # always has valid properties to integrate with once drilling has
        # started (Module 5 gives no explicit "unknown formation" fallback,
        # and an undefined formation would stall the mechanics/hydraulics
        # equations entirely).
        if tvdss_m >= self.formations[-1].base_tvdss_m:
            return self.formations[-1]
        if tvdss_m < self.formations[0].top_tvdss_m:
            return self.formations[0]
        return None


def default_demo_formations() -> List[FormationParams]:
    """
    A small demo formation stack matching the illustrative Upper Assam
    sequence used throughout the Module 4/5 worked examples (Tipam,
    Barail, Kopili). All values are DEMO parameters, not sourced field
    data -- see Module 5 section 4 (data provenance policy: SYNTHETIC).
    """
    return [
        FormationParams(
            name="Tipam Sandstone", top_tvdss_m=0.0, base_tvdss_m=1400.0,
            rock_density_gcc=2.10, ucs_mpa=20.0, youngs_modulus_gpa=6.0,
            pore_pressure_gradient_gcc=1.00, fracture_gradient_gcc=1.50,
            friction_coefficient=0.20, leakoff_coefficient=0.01,
            drillability_coefficient=1.4,
        ),
        FormationParams(
            name="Barail Sandstone", top_tvdss_m=1400.0, base_tvdss_m=2940.0,
            rock_density_gcc=2.25, ucs_mpa=35.0, youngs_modulus_gpa=8.0,
            pore_pressure_gradient_gcc=1.02, fracture_gradient_gcc=1.55,
            friction_coefficient=0.25, leakoff_coefficient=0.02,
            drillability_coefficient=1.0,
        ),
        FormationParams(
            name="Barail Lower Sand", top_tvdss_m=2940.0, base_tvdss_m=3380.0,
            rock_density_gcc=2.30, ucs_mpa=42.0, youngs_modulus_gpa=9.5,
            pore_pressure_gradient_gcc=1.05, fracture_gradient_gcc=1.58,
            friction_coefficient=0.27, leakoff_coefficient=0.025,
            drillability_coefficient=0.85,
        ),
        FormationParams(
            name="Kopili Formation", top_tvdss_m=3380.0, base_tvdss_m=4200.0,
            rock_density_gcc=2.40, ucs_mpa=55.0, youngs_modulus_gpa=12.0,
            pore_pressure_gradient_gcc=1.15, fracture_gradient_gcc=1.62,
            friction_coefficient=0.30, leakoff_coefficient=0.015,
            drillability_coefficient=0.6,
        ),
    ]
