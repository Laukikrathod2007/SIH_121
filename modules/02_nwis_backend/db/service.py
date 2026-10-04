"""
Service layer — business logic sits here, not in server.py's route handlers
and not in repositories.py's SQL. This is what task_claude.md's architecture
section means by:

    API route -> service/business logic -> repository -> database

Each function here opens its own pooled connection (via db.connection) and
shapes its result into the SAME response contract the existing in-memory
endpoints already return, so server.py's routes can swap their data source
without the frontend (or its TypeScript types) needing to know a database
exists underneath.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from app.modules.nwis.db.connection import get_connection
from app.modules.nwis.db.repositories import (
    WellRepository, TrajectoryRepository, FormationRepository, CasingRepository, EventRepository,
)
from app.modules.nwis.models.schemas import (
    Well, WellTrajectory, SurveyStation, FormationTop, DrillingEvent, CasingRecord,
)


class WellNotFoundError(Exception):
    def __init__(self, well_id: str):
        self.well_id = well_id
        super().__init__(f"Well '{well_id}' not found")


def _write_audit_log(conn, action: str, entity_id: Optional[str], metadata: dict) -> None:
    """Best-effort audit trail (task requirement #12). Never raises —
    a logging failure must not fail the read it's recording, so an
    exception here is caught and logged instead of propagated."""
    try:
        conn.execute(
            "INSERT INTO audit_log (actor, action, entity_type, entity_id, metadata) "
            "VALUES (%s, %s, %s, %s, %s)",
            ("system", action, "well", entity_id, _as_jsonb(metadata)),
        )
    except Exception as exc:
        logger.warning(f"audit_log write failed (non-fatal): {exc}")


def _as_jsonb(metadata: dict):
    import json
    return json.dumps(metadata)


def _well_row_to_api_shape(row: dict[str, Any]) -> dict[str, Any]:
    """Match the existing in-memory Well pydantic model's field names
    (models/schemas.py) exactly, so GET /api/v2/wells/{id}'s response shape
    is unchanged by which backend served it."""
    return {
        "well_id": row["well_id"],
        "well_name": row["well_name"],
        "field": row.get("field_name"),
        "field_code": row.get("field_code"),
        "operator": row.get("operator_name") or row.get("operator_code"),
        "surface_lat": row["surface_lat"],
        "surface_lon": row["surface_lon"],
        "kb_elevation_m": row.get("kb_elevation_m"),
        "total_depth_md_m": row["total_depth_md_m"],
        "well_type": row["well_type"],
        "spud_date": row.get("spud_date").isoformat() if row.get("spud_date") else None,
        "completion_date": row.get("completion_date").isoformat() if row.get("completion_date") else None,
        "status": row["status"],
        "witsml_uid": str(row["witsml_uid"]) if row.get("witsml_uid") else "",
        "source_type": row.get("source_type"),
    }


def get_well(well_id: str) -> dict[str, Any]:
    """Active-well lookup — the first leg of the migrated vertical slice.
    Raises WellNotFoundError (server.py maps this to HTTP 404, same as the
    in-memory path's HTTPException(404, ...))."""
    with get_connection() as conn:
        repo = WellRepository(conn)
        row = repo.get_by_id(well_id)
        if row is None:
            raise WellNotFoundError(well_id)
        _write_audit_log(conn, "QUERY", well_id, {"endpoint": "get_well"})
        return _well_row_to_api_shape(row)


def list_wells(field: Optional[str] = None, status: Optional[str] = None) -> dict[str, Any]:
    """Mirrors GET /api/v2/wells' existing response shape: {total, wells}."""
    with get_connection() as conn:
        repo = WellRepository(conn)
        rows = repo.list_all(field=field, status=status)
        return {
            "total": len(rows),
            "wells": [_well_row_to_api_shape(r) for r in rows],
        }


def get_map_wells(
    center_well_id: Optional[str] = None,
    radius_km: Optional[float] = None,
) -> dict[str, Any]:
    """
    The migrated GET /api/v2/map/wells vertical slice: active well lookup
    -> nearby wells -> well metadata, all database-side.

    Reproduces the exact existing contract (see server.py's current
    get_map_wells docstring, preserved verbatim as the semantics this
    function must not regress):
      - no params: every well, unfiltered, distance_km=null, exactly as
        the in-memory path already does.
      - center_well_id + radius_km: a genuine PostGIS ST_DWithin hard
        filter — a well strictly outside radius_km is excluded, not just
        down-scored. This is a DIFFERENT contract from offset_rank's
        radius_km (scoring decay), intentionally — unchanged from the
        in-memory version's own docstring distinction.
    """
    with get_connection() as conn:
        repo = WellRepository(conn)

        if center_well_id is None:
            all_wells = repo.list_all()
            center_row = None
        else:
            center_row = repo.get_by_id(center_well_id)
            if center_row is None:
                raise WellNotFoundError(center_well_id)
            # nearby() excludes the center well itself; re-attach it below
            # (distance_km=0.0) so center_well_id is still present in the
            # response, matching the in-memory version's behavior of
            # returning every well including the center one.
            neighbors = repo.nearby(center_well_id, max_distance_km=radius_km if radius_km is not None else None)
            all_wells = [center_row] + neighbors

        well_ids = [w["well_id"] for w in all_wells]
        event_counts = repo.event_count_by_well(well_ids)

        # active_well_id: the DB schema has no single "currently active
        # well" concept (that's a module-02-runtime/simulation notion, not
        # master data) — the in-memory store's store.active_well_id comes
        # from telemetry_stream.json's active_well_id field. Callers that
        # need it pass center_well_id explicitly; server.py's route layer
        # fills this from the existing in-memory store so the response
        # shape (`active_well_id` key always present) is unchanged.
        map_data = []
        for w in all_wells:
            distance_km = None
            if center_well_id is not None:
                distance_km = 0.0 if w["well_id"] == center_well_id else round(w.get("distance_km", 0.0), 3)
            map_data.append({
                "well_id": w["well_id"],
                "well_name": w["well_name"],
                "field": w.get("field_name"),
                "lat": w["surface_lat"],
                "lon": w["surface_lon"],
                "status": w["status"],
                "well_type": w["well_type"],
                "total_depth_md_m": w["total_depth_md_m"],
                "total_events": event_counts.get(w["well_id"], 0),
                "is_active": None,  # filled by server.py from the in-memory store's active_well_id
                "distance_km": distance_km,
                "source_type": w.get("source_type"),
            })

        _write_audit_log(conn, "QUERY", center_well_id, {
            "endpoint": "get_map_wells", "radius_km": radius_km, "result_count": len(map_data),
        })

        return {
            "total": len(map_data),
            "radius_filter_applied": center_well_id is not None and radius_km is not None,
            "wells": map_data,
        }


# -----------------------------------------------------------------------------
# Pass 4 extensions — trajectory / formations / casing. Same shape contract
# as the existing well/map endpoints: a WellNotFoundError-free "no data"
# result returns an empty/absent result exactly like the in-memory path
# (server.py decides 404 vs empty list), and server.py catches any other
# exception to raise 503 rather than silently falling back to memory.
# -----------------------------------------------------------------------------

def _station_row_to_api_shape(row: dict[str, Any]) -> dict[str, Any]:
    """Match models/schemas.py SurveyStation's field names exactly."""
    return {
        "md_m": float(row["md_m"]),
        "inclination_deg": float(row["inclination_deg"]),
        "azimuth_deg": float(row["azimuth_deg"]),
        "tvd_m": float(row["tvd_m"]),
        "ns_m": float(row["ns_m"]),
        "ew_m": float(row["ew_m"]),
        "tvdss_m": float(row["tvdss_m"]),
    }


def get_trajectory(well_id: str) -> Optional[dict[str, Any]]:
    """Returns None if the well itself doesn't exist OR has no trajectory
    rows — server.py distinguishes "well not found" (checked separately
    against get_well) from "no trajectory for this well" the same way it
    already does for the in-memory path."""
    with get_connection() as conn:
        well_repo = WellRepository(conn)
        well_row = well_repo.get_by_id(well_id)
        if well_row is None:
            raise WellNotFoundError(well_id)

        stations = TrajectoryRepository(conn).for_well(well_id)
        if not stations:
            return None

        return {
            "well_id": well_id,
            "well_name": well_row["well_name"],
            "method": stations[0]["method"],
            "well_type": well_row["well_type"],
            "stations": [_station_row_to_api_shape(s) for s in stations],
        }


def _top_row_to_api_shape(well_id: str, row: dict[str, Any]) -> dict[str, Any]:
    """Match models/schemas.py FormationTop's field names exactly."""
    return {
        "well_id": well_id,
        "well_name": well_id,  # in-memory FormationTop reuses well_id as well_name too
        "formation_name": row["formation_name"],
        "top_md_m": float(row["top_md_m"]),
        "top_tvd_m": float(row["top_tvd_m"]),
        "base_md_m": float(row["base_md_m"]),
        "thickness_m": float(row["thickness_m"]) if row.get("thickness_m") is not None else 0.0,
        "pore_pressure_gradient_ppg": float(row["pore_pressure_gradient_ppg"]) if row.get("pore_pressure_gradient_ppg") is not None else 9.0,
        "lithology": row.get("lithology"),
    }


def get_formations_for_well(well_id: str) -> Optional[list[dict[str, Any]]]:
    """None means "no formation data for this well" (server.py 404s on
    that, matching the in-memory path's `tops is None` check) — distinct
    from an empty list, which this never returns (an absent well in
    formation_tops always means zero rows, so both cases collapse to
    None here; server.py's contract only needs to tell "nothing" apart
    from "something")."""
    with get_connection() as conn:
        rows = FormationRepository(conn).for_well(well_id)
        if not rows:
            return None
        return [_top_row_to_api_shape(well_id, r) for r in rows]


def get_all_formations(formation_name: Optional[str] = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = FormationRepository(conn).all_tops(formation_name=formation_name)
        return [_top_row_to_api_shape(r["well_id"], r) for r in rows]


def _casing_row_to_api_shape(well_id: str, row: dict[str, Any]) -> dict[str, Any]:
    """Match models/schemas.py CasingRecord's field names exactly."""
    return {
        "well_id": well_id,
        "casing_size_inches": float(row["casing_size_inches"]) if row.get("casing_size_inches") is not None else None,
        "shoe_depth_md_m": float(row["shoe_depth_md_m"]),
        "top_of_cement_md_m": float(row["top_of_cement_md_m"]) if row.get("top_of_cement_md_m") is not None else None,
    }


def get_casing_for_well(well_id: str) -> list[dict[str, Any]]:
    """Real casing data exists for 2 Volve wells only — an empty list for
    every other well is correct, not an error (matches the in-memory
    path's own contract, server.py never 404s here)."""
    with get_connection() as conn:
        rows = CasingRepository(conn).for_well(well_id)
        return [_casing_row_to_api_shape(well_id, r) for r in rows]


def get_all_casing() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = CasingRepository(conn).all_records()
        return [_casing_row_to_api_shape(r["well_id"], r) for r in rows]


# -----------------------------------------------------------------------------
# Pass 5 — DbStoreSnapshot: a single object exposing the exact attribute/
# method surface of NWISDataStore (data_store.py) so server.py's remaining
# in-memory routes (events, offset_rank, corridors, ahead_of_bit, analyze,
# stratigraphic_depth_track) and NWISOrchestrator.analyze() work against it
# completely unmodified.
#
# Why this shape, not a per-route patch: tracing every `store.*` reference
# in server.py and orchestrator.py (not just the final engine call in each
# route) showed the in-memory coupling is pervasive — active_well lookups,
# trajectory/formation-tops lookups, and the all_wells/all_trajectories/
# all_formation_tops/all_events dicts are all read directly from the store
# object multiple times per handler. Swapping only the outermost engine
# call's keyword arguments while leaving `store.wells_by_id.get(...)` etc.
# untouched would still be memory-backed underneath a DB-looking response.
# One object with the same surface, built once per request from Postgres,
# is what actually closes that gap end-to-end.
#
# Deliberately NOT included: get_telemetry_at(). NWISOrchestrator.analyze()
# is the only caller, and that call reads data/synthetic/telemetry_stream.
# json — a single flat, well-id-blind list scoped to WELL-HGJ-012 (the
# only well with any volume of telemetry, in-memory OR in Postgres: the DB
# has rows for just 2 of 14 wells, 3600 for WELL-HGJ-012 and 57 from a
# previous pass's own live verification writes for WELL-NHK-001).
# Migrating this one call would not fix that pre-existing well-id-blindness
# (same ~2-well coverage either way) and would add a new DB-failure mode
# for the other 12 wells where today it silently returns "whatever's in
# the global list" — see AUDIT/13_PRODUCT_COMPLETION.md for the full note.
# orchestrator.py composes DbStoreSnapshot with the real in-memory store's
# get_telemetry_at for this one field rather than this class defining its
# own (deliberately absent, not an oversight).
# -----------------------------------------------------------------------------

def _well_row_to_model(row: dict[str, Any]) -> Well:
    """Reconstructs a real models.schemas.Well (not the API-shaped dict
    _well_row_to_api_shape produces) — the engines (dors_engine.py,
    risk_corridor_engine.py, stratigraphic_correlator.py) take typed Well/
    WellTrajectory/FormationTop/DrillingEvent instances, not plain dicts.
    Well.field/.operator are non-optional str on the Pydantic model; a DB
    row can have field_name/operator_name = NULL (no join match) — default
    to "" rather than raise, matching how data_store.py already treats a
    well with no recorded field/operator."""
    return Well(
        well_id=row["well_id"],
        well_name=row["well_name"],
        field=row.get("field_name") or "",
        field_code=row.get("field_code") or "",
        operator=row.get("operator_name") or row.get("operator_code") or "",
        surface_lat=row["surface_lat"],
        surface_lon=row["surface_lon"],
        kb_elevation_m=row.get("kb_elevation_m", 10.0),
        total_depth_md_m=row["total_depth_md_m"],
        well_type=row.get("well_type") or "Vertical",
        spud_date=row.get("spud_date").isoformat() if row.get("spud_date") else None,
        completion_date=row.get("completion_date").isoformat() if row.get("completion_date") else None,
        status=row.get("status") or "COMPLETED",
        witsml_uid=str(row["witsml_uid"]) if row.get("witsml_uid") else "",
    )


def _station_row_to_model(well_id: str, well_name: str, well_type, rows: list[dict[str, Any]]) -> Optional[WellTrajectory]:
    """well_type must be passed explicitly from the owning Well, not left
    to WellTrajectory's own Pydantic default (WellType.VERTICAL) — found
    live, not theoretical: dors_engine.py's score_trajectory() reads
    offset_traj.well_type.value directly (not Well.well_type) for its
    same-type-bonus/different-type-penalty logic, so omitting it here
    silently coerced every non-vertical well's trajectory to VERTICAL and
    produced a DORS score ~0.075-0.5 lower than the memory-backed path for
    the exact same underlying station data — caught by a direct
    memory-vs-DB ranking-parity comparison before this reached a route."""
    if not rows:
        return None
    stations = [
        SurveyStation(
            md_m=float(r["md_m"]), inclination_deg=float(r["inclination_deg"]),
            azimuth_deg=float(r["azimuth_deg"]), tvd_m=float(r["tvd_m"]),
            ns_m=float(r["ns_m"]), ew_m=float(r["ew_m"]), tvdss_m=float(r["tvdss_m"]),
        )
        for r in rows
    ]
    return WellTrajectory(
        well_id=well_id, well_name=well_name, well_type=well_type,
        method=rows[0].get("method") or "MINIMUM_CURVATURE", stations=stations,
    )


def _top_row_to_model(well_id: str, row: dict[str, Any]) -> FormationTop:
    return FormationTop(
        well_id=well_id, well_name=well_id,
        formation_name=row["formation_name"],
        top_md_m=float(row["top_md_m"]), top_tvd_m=float(row["top_tvd_m"]), base_md_m=float(row["base_md_m"]),
        thickness_m=float(row["thickness_m"]) if row.get("thickness_m") is not None else 0.0,
        pore_pressure_gradient_ppg=float(row["pore_pressure_gradient_ppg"]) if row.get("pore_pressure_gradient_ppg") is not None else 9.0,
        lithology=row.get("lithology"),
    )


def _casing_row_to_model(well_id: str, row: dict[str, Any]) -> CasingRecord:
    return CasingRecord(
        well_id=well_id,
        casing_size_inches=float(row["casing_size_inches"]) if row.get("casing_size_inches") is not None else None,
        shoe_depth_md_m=float(row["shoe_depth_md_m"]),
        top_of_cement_md_m=float(row["top_of_cement_md_m"]) if row.get("top_of_cement_md_m") is not None else None,
    )


def _event_row_to_model(row: dict[str, Any]) -> DrillingEvent:
    return DrillingEvent(
        event_id=row["event_id"], well_id=row["well_id"], event_type=row["event_type"],
        severity=row.get("severity") or "MEDIUM",
        depth_start_md_m=float(row["depth_start_md_m"]),
        depth_end_md_m=float(row["depth_end_md_m"]) if row.get("depth_end_md_m") is not None else None,
        formation=row.get("formation"), raw_narrative=row.get("raw_narrative") or "",
        npt_hours=float(row["npt_hours"]) if row.get("npt_hours") is not None else 0.0,
        loss_rate_bbl_hr=float(row["loss_rate_bbl_hr"]) if row.get("loss_rate_bbl_hr") is not None else None,
        mitigation_description=row.get("mitigation_description"), outcome=row.get("outcome"),
        confidence=float(row["confidence"]) if row.get("confidence") is not None else 0.90,
        source_document=row.get("source_document_id"), source_page=row.get("source_page"),
    )


class DbStoreSnapshot:
    """Built once per request by build_store_snapshot(). Read-only;
    nothing here writes to the database."""

    def __init__(
        self,
        wells_by_id: dict[str, Well],
        all_trajectories: dict[str, WellTrajectory],
        formation_tops_by_well: dict[str, list[FormationTop]],
        casing_records_by_well: dict[str, list[CasingRecord]],
        events_by_well: dict[str, list[DrillingEvent]],
        active_well_id: Optional[str],
    ):
        self.wells_by_id = wells_by_id
        self.all_wells = list(wells_by_id.values())
        self.all_trajectories = all_trajectories
        self.formation_tops_by_well = formation_tops_by_well
        self.casing_records_by_well = casing_records_by_well
        self.events_by_well = events_by_well
        self.all_events = [e for evs in events_by_well.values() for e in evs]
        self.active_well_id = active_well_id

    def get_events_for_top_wells(self, top_well_ids: list[str]) -> list[DrillingEvent]:
        result: list[DrillingEvent] = []
        for wid in top_well_ids:
            result.extend(self.events_by_well.get(wid, []))
        return result

    def get_telemetry_at(self, depth_m: float, window: int = 120):
        """Deliberately NOT backed by telemetry_records — see this
        module's section docstring above DbStoreSnapshot for the full
        reasoning (the DB has rows for only 2 of 14 wells; the in-memory
        source is equally well-id-blind today, so migrating this one call
        would add a new DB-failure mode without fixing the pre-existing
        gap). Composed from the real in-memory NWISDataStore singleton at
        call time instead -- NWISOrchestrator.analyze() is this method's
        only caller, and it needs SOME answer for sensor-anomaly scoring
        even when every other field in this snapshot is DB-backed."""
        from app.modules.nwis.data_store import NWISDataStore
        return NWISDataStore().get_telemetry_at(depth_m, window=window)


def build_store_snapshot(active_well_id: Optional[str] = None) -> DbStoreSnapshot:
    """Assembles one DbStoreSnapshot from Postgres. The N+1-shaped per-well
    trajectory fetch below is explicit, not hidden: TrajectoryRepository.
    for_well() is called once per well (14 wells in the current catalog) —
    acceptable at today's data volume, matching this codebase's own stated
    policy elsewhere (search/knowledge_search.py's module docstring) of not
    pre-optimizing for a scale this system isn't at. Raises on any DB
    error — the caller (server.py) already wraps every DB-backed call in
    try/except -> 503, established in Pass 4; this function adds no new
    error-handling pattern."""
    with get_connection() as conn:
        well_rows = WellRepository(conn).list_all()
        wells_by_id = {r["well_id"]: _well_row_to_model(r) for r in well_rows}

        traj_repo = TrajectoryRepository(conn)
        all_trajectories: dict[str, WellTrajectory] = {}
        for well_id, well in wells_by_id.items():
            station_rows = traj_repo.for_well(well_id)
            traj = _station_row_to_model(well_id, well.well_name, well.well_type, station_rows)
            if traj is not None:
                all_trajectories[well_id] = traj

        top_rows = FormationRepository(conn).all_tops()
        formation_tops_by_well: dict[str, list[FormationTop]] = {}
        for r in top_rows:
            formation_tops_by_well.setdefault(r["well_id"], []).append(_top_row_to_model(r["well_id"], r))

        casing_rows = CasingRepository(conn).all_records()
        casing_records_by_well: dict[str, list[CasingRecord]] = {}
        for r in casing_rows:
            casing_records_by_well.setdefault(r["well_id"], []).append(_casing_row_to_model(r["well_id"], r))

        event_rows = EventRepository(conn).all_events()
        events_by_well: dict[str, list[DrillingEvent]] = {}
        for r in event_rows:
            events_by_well.setdefault(r["well_id"], []).append(_event_row_to_model(r))

    return DbStoreSnapshot(
        wells_by_id=wells_by_id,
        all_trajectories=all_trajectories,
        formation_tops_by_well=formation_tops_by_well,
        casing_records_by_well=casing_records_by_well,
        events_by_well=events_by_well,
        active_well_id=active_well_id,
    )
