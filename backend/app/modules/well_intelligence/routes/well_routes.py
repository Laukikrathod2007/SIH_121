"""
Well & Geological Track API Routes.
Exposes endpoints for well metadata, formation tops, GIS map data, and searchable historical events.
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query

from app.modules.well_intelligence.controllers.well_controller import well_controller

router = APIRouter(tags=["Wells & Geology"])


@router.get("/wells")
async def list_wells(
    field: Optional[str] = Query(None, description="Filter by field name"),
    status: Optional[str] = Query(None, description="Filter by well status"),
):
    """List all wells in the repository with optional field/status filters."""
    return well_controller.list_wells(field=field, status=status)


@router.get("/wells/{well_id}")
async def get_well(well_id: str):
    """Get full details for a single well, including trajectory and events count."""
    return well_controller.get_well_details(well_id)


@router.get("/map/wells")
async def get_map_wells():
    """Get surface coordinates and metadata for all wells on the GIS map."""
    return well_controller.get_map_wells()


@router.get("/formations/{well_id}")
async def get_formations(well_id: str):
    """Get formation tops for a well (feed for stratigraphic viewer)."""
    return well_controller.get_formation_tops(well_id)


@router.get("/formations")
async def get_all_formations(
    formation_name: Optional[str] = Query(None, description="Filter by formation name"),
):
    """Get all formation tops across all wells in the field."""
    return well_controller.get_all_formations(formation_name)


@router.get("/events/{well_id}")
async def get_well_events(well_id: str):
    """Get all drilling hazard events for a specific well (Evidence Proof modal)."""
    return well_controller.get_well_events(well_id)


@router.get("/events")
async def search_events(
    hazard_type: Optional[str] = Query(None, description="Filter by hazard type (e.g. MUD_LOSS)"),
    formation: Optional[str] = Query(None, description="Filter by formation name"),
    min_severity: Optional[str] = Query(None, description="Minimum severity (LOW/MEDIUM/HIGH/CRITICAL)"),
    depth_min: Optional[float] = Query(None, description="Minimum depth (m MD)"),
    depth_max: Optional[float] = Query(None, description="Maximum depth (m MD)"),
):
    """Searchable historical drilling event repository."""
    return well_controller.search_events(
        hazard_type=hazard_type,
        formation=formation,
        min_severity=min_severity,
        depth_min=depth_min,
        depth_max=depth_max,
    )
