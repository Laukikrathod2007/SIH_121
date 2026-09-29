"""
Live Telemetry & Sensor Analytics API Routes.
Exposes endpoints for real-time and playback drilling telemetry streams.
"""

from __future__ import annotations
from fastapi import APIRouter, Query

from app.modules.well_intelligence.controllers.well_controller import well_controller

router = APIRouter(tags=["Telemetry Stream"])


@router.get("/telemetry/{well_id}")
async def get_telemetry(
    well_id: str,
    depth: float = Query(..., description="Current drill bit depth (m MD)"),
    window: int = Query(300, description="Number of historical telemetry records to query"),
):
    """
    Retrieve real-time / replayed drilling telemetry records at the active depth.
    Includes ROP, WOB, RPM, Torque, SPP, Flow rates, Pit Volume, Mud Weight, and D-exponent.
    """
    return well_controller.get_telemetry(well_id=well_id, depth=depth, window=window)
