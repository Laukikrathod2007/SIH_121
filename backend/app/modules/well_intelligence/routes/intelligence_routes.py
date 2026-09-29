"""
NWIS Intelligence & Risk Analytics Routes.
Exposes endpoints for DORS ranking, full NWIS analysis, and lookahead risk corridors.
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query

from app.modules.well_intelligence.controllers.well_controller import well_controller

router = APIRouter(tags=["NWIS Intelligence & Risk Analytics"])


@router.get("/analyze/{well_id}")
async def analyze_well(
    well_id: str,
    depth: float = Query(..., description="Current drill bit depth (m MD)"),
    radius_km: float = Query(25.0, description="Spatial search radius (km)"),
    mud_weight_ppg: float = Query(9.5, description="Current active mud weight (ppg)"),
):
    """
    Execute full NWIS Intelligence Pipeline at a specified bit depth.
    Runs: DORS 5-Factor Ranking → Stratigraphic Alignment → Risk Corridors → 4-Pillar Decoupled Confidence.
    """
    return well_controller.analyze_well(
        well_id=well_id,
        depth=depth,
        radius_km=radius_km,
        mud_weight_ppg=mud_weight_ppg,
    )


@router.get("/offset_rank/{well_id}")
@router.get("/correlate/offsets/{well_id}")
async def rank_offsets(
    well_id: str,
    depth: float = Query(..., description="Current bit depth (m MD)"),
    radius_km: float = Query(25.0, description="Search radius (km)"),
    top_n: int = Query(10, description="Number of top offset wells to return"),
):
    """
    Run the DORS 5-Factor mathematical offset ranking engine.
    Computes spatial, formation, depth, trajectory, and hazard component scores.
    """
    return well_controller.rank_offsets(
        well_id=well_id,
        depth=depth,
        radius_km=radius_km,
        top_n=top_n,
    )


@router.get("/corridors/{well_id}")
async def get_risk_corridors(
    well_id: str,
    depth: float = Query(..., description="Current bit depth (m MD)"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard type"),
):
    """
    Get all historical risk corridors ahead of the current drill bit depth.
    """
    return well_controller.get_risk_corridors(
        well_id=well_id,
        depth=depth,
        hazard_type=hazard_type,
    )


@router.get("/xi_correlate/{well_id}")
@router.get("/correlate/xi/{well_id}")
async def xi_correlate(
    well_id: str,
    depth: float = Query(..., description="Current active-well bit depth (m MD)"),
    offset_well_id: Optional[str] = Query(
        None, description="Correlate against a single offset well; omit to correlate against all wells"
    ),
    window_m: float = Query(
        50.0, description="Historical event search window (+/- meters TVDSS) around the mapped equivalent horizon"
    ),
):
    """
    Module 4 stratigraphic xi correlation.

    Runs the deterministic MD -> TVDSS -> formation -> xi -> offset
    equivalent-depth -> historical event search chain per the Module 4
    specification. Returns the active well's xi context plus, for each
    offset well, the mapped equivalent TVDSS and any historical events
    found within the search window.
    """
    return well_controller.correlate_xi(
        well_id=well_id,
        depth=depth,
        offset_well_id=offset_well_id,
        window_m=window_m,
    )


@router.get("/corridors/ahead/{well_id}")
async def get_ahead_corridor(
    well_id: str,
    depth: float = Query(..., description="Current bit depth (m MD)"),
    max_lookahead_m: float = Query(200.0, description="Lookahead projection distance (m)"),
    step_m: float = Query(10.0, description="Step size along trajectory (m)"),
    window_m: float = Query(50.0, description="Event correlation window around equivalent horizon (m)"),
):
    """
    Ahead-of-bit projection corridor (0-20m immediate, 20-50m short-term, 50-200m proactive).
    Computes projected TVDSS, formation penetration, stratigraphic xi, offset equivalent depths,
    and hazard risk probabilities along the trajectory.
    """
    return well_controller.get_ahead_corridor(
        well_id=well_id,
        depth=depth,
        max_lookahead_m=max_lookahead_m,
        step_m=step_m,
        window_m=window_m,
    )


@router.post("/survey/calculate")
async def calculate_survey(
    payload: dict,
):
    """
    Calculate directional 3D trajectory using SPE/API Minimum Curvature method.
    Accepts list of survey stations (md_m, inclination_deg, azimuth_deg) and wellhead_elevation_m.
    Returns computed stations with TVD, TVDSS, North, East, Dogleg, DLS, and method.
    """
    stations = payload.get("stations", [])
    wellhead_elevation_m = float(payload.get("wellhead_elevation_m", 0.0))
    well_id = payload.get("well_id", "CUSTOM_WELL")
    return well_controller.calculate_survey(
        stations=stations,
        wellhead_elevation_m=wellhead_elevation_m,
        well_id=well_id,
    )

