"""
Typed request/response Pydantic models for the migrated (database-backed)
endpoints — task requirement #12. Field names match models/schemas.py's
existing `Well` model and the in-memory server.py routes' current JSON
shape exactly, so these are response contracts the frontend already
satisfies, not a new/different one.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class WellOut(BaseModel):
    well_id: str
    well_name: str
    field: Optional[str] = None
    field_code: Optional[str] = None
    operator: Optional[str] = None
    surface_lat: float
    surface_lon: float
    kb_elevation_m: Optional[float] = None
    total_depth_md_m: float
    well_type: str
    spud_date: Optional[str] = None
    completion_date: Optional[str] = None
    status: str
    witsml_uid: str = ""
    # Not present on the in-memory Well model — additive. Lets a client
    # distinguish REAL/SYNTHETIC/SIMULATED/IMPORTED/DERIVED rows now that
    # the canonical store actually tracks it (task requirement #2).
    source_type: Optional[str] = None


class WellListOut(BaseModel):
    total: int
    wells: list[WellOut]


class MapWellOut(BaseModel):
    well_id: str
    well_name: str
    field: Optional[str] = None
    lat: float
    lon: float
    status: str
    well_type: str
    total_depth_md_m: float
    total_events: int
    is_active: Optional[bool] = None
    distance_km: Optional[float] = None
    source_type: Optional[str] = None


class MapWellsOut(BaseModel):
    total: int
    active_well_id: Optional[str] = None
    radius_filter_applied: bool
    wells: list[MapWellOut]
    # Which backend actually served this response — opt-in observability for
    # the migration itself (task requirement #17: no hidden contract
    # mismatches). Not present on the pre-migration in-memory response;
    # additive, so no existing consumer breaks by ignoring an unknown field.
    data_source: str = "memory"
