"""
Knowledge Repository, GIS Radius, Trajectory & Live Replay Routes.

Ported from backend-working's modules/02_nwis_backend/server.py (/api/v2/*)
into the unified /api/v1 surface:
  - GET /events/search              semantic "lessons learned" search (PS outcome iii)
  - GET /map/wells/nearby/{well_id} wells within a user-defined radius (PS outcome ii)
  - GET /trajectory/{well_id}       full survey-station list for trajectory views
  - GET /stratigraphic_depth_track/{well_id}  horizon alignment across top offsets (PS outcome iv)
  - GET /live/replay/{well_id}      Server-Sent Events risk/alert stream (PS outcome vi)

This router must be mounted BEFORE well_routes so /events/search is not
swallowed by the /events/{well_id} wildcard.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.modules.well_intelligence.services.data_store import NWISDataStore

router = APIRouter(tags=["Knowledge Repository & Live Replay"])

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _store() -> NWISDataStore:
    store = NWISDataStore()
    if not store.is_loaded():
        raise HTTPException(status_code=503, detail="Data store not loaded.")
    return store


def filter_events_structured(
    events: list,
    hazard_type: Optional[str] = None,
    formation: Optional[str] = None,
    min_severity: Optional[str] = None,
    depth_min: Optional[float] = None,
    depth_max: Optional[float] = None,
    well_id: Optional[str] = None,
) -> list:
    """Structured-field filtering shared by /events/search (and usable by /events)."""
    if well_id:
        events = [e for e in events if e.well_id == well_id]
    if hazard_type:
        events = [e for e in events if e.event_type.value == hazard_type.upper()]
    if formation:
        events = [e for e in events if e.formation and formation.lower() in e.formation.lower()]
    if depth_min is not None:
        events = [e for e in events if e.depth_start_md_m >= depth_min]
    if depth_max is not None:
        events = [e for e in events if e.depth_start_md_m <= depth_max]
    if min_severity:
        floor = SEVERITY_ORDER.get(min_severity.upper(), 0)
        events = [e for e in events if SEVERITY_ORDER.get(e.severity, 0) >= floor]
    return events


def compute_facets(events: list) -> dict:
    """Facet counts over the current (filtered) result set."""
    return {
        "hazard_type": dict(Counter(e.event_type.value for e in events)),
        "formation": dict(Counter(e.formation for e in events if e.formation)),
        "severity": dict(Counter(e.severity for e in events)),
        "well_id": dict(Counter(e.well_id for e in events)),
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@router.get("/events/search")
async def search_events_semantic(
    query: str = Query(..., min_length=1, description="Free text, e.g. 'pipe got stuck against the wall'"),
    hazard_type: Optional[str] = Query(None),
    formation: Optional[str] = Query(None),
    min_severity: Optional[str] = Query(None),
    depth_min: Optional[float] = Query(None, ge=0),
    depth_max: Optional[float] = Query(None, ge=0),
    well_id: Optional[str] = Query(None),
    top_n: int = Query(10, ge=1, le=50),
):
    """
    Semantic search over event narratives, mitigations and outcomes. Structured
    filters narrow candidates first; `query` then ranks them. `search_mode`
    reports whether ranking was semantic (sentence-transformers) or keyword fallback.
    """
    from app.modules.well_intelligence.search.knowledge_search import search_events as run_search

    store = _store()
    candidates = filter_events_structured(
        store.all_events, hazard_type, formation, min_severity, depth_min, depth_max, well_id
    )
    ranked, mode = run_search(query, candidates, top_n=top_n)
    return {
        "query": query,
        "search_mode": mode,
        "total_candidates": len(candidates),
        "total_returned": len(ranked),
        "facets": compute_facets(candidates),
        "results": [
            {"relevance_score": round(score, 4), "event": event.model_dump()}
            for event, score in ranked
        ],
    }


@router.get("/events/facets")
async def event_facets():
    """Facet counts over the entire event repository (for search filter chips)."""
    store = _store()
    return {"total": len(store.all_events), "facets": compute_facets(store.all_events)}


@router.get("/map/wells/nearby/{well_id}")
async def nearby_wells(
    well_id: str,
    radius_km: float = Query(25.0, gt=0, le=500, description="User-defined search radius (km)"),
):
    """
    Wells within `radius_km` of the active well's surface location, sorted by
    distance, each with event counts by hazard type for map colouring.
    """
    store = _store()
    center = store.wells_by_id.get(well_id)
    if center is None:
        raise HTTPException(404, f"Well '{well_id}' not found")

    wells = []
    for w in store.all_wells:
        dist = haversine_km(center.surface_lat, center.surface_lon, w.surface_lat, w.surface_lon)
        events = store.events_by_well.get(w.well_id, [])
        wells.append({
            "well_id": w.well_id,
            "well_name": w.well_name,
            "field": w.field,
            "lat": w.surface_lat,
            "lon": w.surface_lon,
            "status": w.status.value,
            "well_type": w.well_type.value,
            "total_depth_md_m": w.total_depth_md_m,
            "distance_km": round(dist, 3),
            "in_radius": dist <= radius_km,
            "is_active": w.well_id == well_id,
            "total_events": len(events),
            "npt_hours": round(sum(e.npt_hours for e in events), 1),
            "events_by_type": dict(Counter(e.event_type.value for e in events)),
        })
    wells.sort(key=lambda x: x["distance_km"])
    return {
        "center_well_id": well_id,
        "center": {"lat": center.surface_lat, "lon": center.surface_lon},
        "radius_km": radius_km,
        "total": len(wells),
        "in_radius": sum(1 for w in wells if w["in_radius"]),
        "wells": wells,
    }


@router.get("/trajectory/{well_id}")
async def get_trajectory(well_id: str):
    """Full survey-station list (md/inc/azi/tvd/ns/ew/tvdss) for a well."""
    store = _store()
    if well_id not in store.wells_by_id:
        raise HTTPException(404, f"Well '{well_id}' not found")
    traj = store.all_trajectories.get(well_id)
    if traj is None:
        raise HTTPException(404, f"No trajectory data for well '{well_id}'")
    return {
        "well_id": traj.well_id,
        "well_name": traj.well_name,
        "method": traj.method,
        "well_type": traj.well_type,
        "stations": [s.model_dump() for s in traj.stations],
    }


@router.get("/stratigraphic_depth_track/{well_id}")
async def stratigraphic_depth_track(
    well_id: str,
    depth: float = Query(..., ge=0, description="Active bit depth (m MD)"),
    top_n: int = Query(10, ge=1, le=50),
):
    """Equivalent formation depth in each top-ranked offset well (Trajectory-Trap safe)."""
    from app.modules.well_intelligence.services.dors_engine import rank_offset_wells
    from app.modules.well_intelligence.services.stratigraphic_correlator import (
        align_horizons_across_wells,
        formation_at_depth,
    )

    store = _store()
    active_well = store.wells_by_id.get(well_id)
    if not active_well:
        raise HTTPException(404, f"Well '{well_id}' not found")
    active_traj = store.all_trajectories.get(well_id)
    if active_traj is None:
        raise HTTPException(404, f"No trajectory data for well '{well_id}'")

    active_tops = store.formation_tops_by_well.get(well_id, [])
    active_fm = formation_at_depth(active_tops, depth)
    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=depth,
        active_formation=active_fm.formation_name if active_fm else None,
        all_wells=store.all_wells,
        all_trajectories=store.all_trajectories,
        all_formation_tops=store.formation_tops_by_well,
        all_events=store.events_by_well,
        top_n=top_n,
    )
    offset_wells = [store.wells_by_id[r.well_id] for r in rankings if r.well_id in store.wells_by_id]
    alignment = align_horizons_across_wells(
        active_md=depth,
        active_well=active_well,
        active_traj=active_traj,
        active_tops=active_tops,
        offset_wells=offset_wells,
        offset_trajs=store.all_trajectories,
        offset_tops_map=store.formation_tops_by_well,
    )
    return {
        "active_well_id": well_id,
        "depth_m": depth,
        "formation_at_bit": active_fm.formation_name if active_fm else None,
        "wells_aligned": len(alignment),
        "alignment": alignment,
    }


@router.get("/live/replay/{well_id}")
async def live_replay(
    request: Request,
    well_id: str,
    n_ticks: int = Query(80, ge=1, le=1000),
    tick_seconds: float = Query(0.5, ge=0.05, le=10.0),
    start_depth_m: Optional[float] = Query(None, ge=0),
    end_depth_m: Optional[float] = Query(None, ge=0),
):
    """
    Server-Sent Events: pushes a risk/alert summary as the replayed bit depth
    advances through the well's trajectory. Consume with the browser's EventSource.
    """
    from app.modules.well_intelligence.live.replay_engine import replay_well

    store = _store()
    if well_id not in store.wells_by_id:
        raise HTTPException(404, f"Well '{well_id}' not found")
    if well_id not in store.all_trajectories:
        raise HTTPException(404, f"No trajectory data for well '{well_id}' — cannot replay")

    async def event_stream():
        try:
            async for update in replay_well(
                store, well_id,
                n_ticks=n_ticks, tick_seconds=tick_seconds,
                start_depth_m=start_depth_m, end_depth_m=end_depth_m,
                is_disconnected=request.is_disconnected,
            ):
                yield f"data: {json.dumps(update, default=str)}\n\n"
        except ValueError as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
