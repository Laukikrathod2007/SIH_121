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
