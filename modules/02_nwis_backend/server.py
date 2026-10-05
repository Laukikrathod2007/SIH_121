"""
NWIS Module 02 — FastAPI Application Server
Serves all backend intelligence endpoints.

Endpoints:
  GET  /api/v2/wells                     → List all wells
  GET  /api/v2/wells/{well_id}           → Get single well details
  GET  /api/v2/analyze/{well_id}         → Full NWIS intelligence analysis
  GET  /api/v2/offset_rank/{well_id}     → DORS ranking only
  GET  /api/v2/telemetry/{well_id}       → Live telemetry stream
  GET  /api/v2/formations/{well_id}      → Formation tops
  GET  /api/v2/casing/{well_id}          → Casing records (real data, 2 Volve wells)
  GET  /api/v2/casing                    → Casing records across all wells
  GET  /api/v2/events/{well_id}          → Drilling events (for evidence modal)
  GET  /api/v2/events/search             → Free-text/semantic search over event narratives
  GET  /api/v2/corridors/{well_id}       → Risk corridors
  GET  /api/v2/ahead_of_bit/{well_id}    → Ahead-of-bit projected corridor (0-200m lookahead)
  GET  /api/v2/live/replay/{well_id}     → Real-time alert stream (SSE)
  POST /api/v2/agent/chat                → Agentic Knowledge Copilot (SSE)
  GET  /api/v2/health                    → System health
"""

from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from loguru import logger

# Imports below use the canonical `app.modules.nwis` package (an adapter whose
# __path__ points at this directory -- see Backend/app/modules/nwis/__init__.py),
# so no sys.path manipulation is needed or performed.
MODULE_ROOT = Path(__file__).parent

from app.modules.nwis.data_store import NWISDataStore
from app.modules.nwis.orchestrator import NWISOrchestrator
from app.modules.nwis.models.schemas import HazardType
from app.modules.nwis.db.connection import is_configured as db_is_configured, cached_healthcheck as db_healthcheck
from app.modules.nwis.db import service as db_service
from app.modules.nwis.auth import require_api_key, rate_limit, rate_limit_agent, auth_enabled, RATE_LIMIT_ENABLED, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
from pydantic import BaseModel

store = NWISDataStore()

# Rotating file log, in addition to the default stderr sink — matches
# modules/01_document_intelligence/api/server.py's setup.
LOG_DIR = MODULE_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(
    LOG_DIR / "nwis_module02_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    enqueue=True,
    level="INFO",
    backtrace=False,
    diagnose=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("NWIS Backend Intelligence Core starting...")
    logger.info("Engines: DORS | Stratigraphic Correlator | Risk Corridors | 4-Pillar Confidence")

    # Load testbed data
    try:
        store.load()
        logger.success(f"Data store loaded: {store.status()}")
    except Exception as e:
        logger.error(f"Data store load failed: {e}")
        logger.warning("Run: python data/synthetic/generate_testbed.py to generate data")

    # Pre-warm the semantic search embedding model in the background, same
    # pattern as module 01's Docling pre-warm. Without this, _get_model()
    # lazy-loads sentence-transformers (and its torch/protobuf import chain)
    # on whichever request happens to call GET /api/v2/events/search first
    # -- a real, reproducible 60-120s stall on a live demo's first search,
    # confirmed in logger/11's backend audit. Pre-warming here moves that
    # cost to server startup, where it's invisible to a user.
    try:
        from app.modules.nwis.search.knowledge_search import _get_model
        asyncio.get_event_loop().run_in_executor(None, _get_model)
        logger.info("Knowledge-search embedding model pre-warm initiated in background")
    except Exception as exc:
        logger.warning(f"Knowledge-search pre-warm skipped: {exc}")

    yield
    logger.info("NWIS Backend shutting down")


app = FastAPI(
    title="NWIS Backend Intelligence API",
    description=(
        "Module 02: Dynamic Offset Relevance Engine (DORS) + "
        "Stratigraphic Depth Correlator + "
        "Historical Risk Corridor Engine + "
        "4-Pillar Decoupled Confidence Evaluator. "
        "100% air-gapped, WITSML-aligned field naming."
    ),
    version="2.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS is configured once, centrally, in Backend/app/main.py (previously
# wide-open "*" here, which combined with zero auth meant any website's JS
# could call this API from a victim's browser -- already fixed there with
# a configurable allowlist). This module's own `app` instance only ever
# runs standalone; Backend/app/integrations/_mount.py copies only
# `.router.routes` from it onto the real served app, never middleware, so a
# CORSMiddleware registered here was dead code in the one place CORS
# actually matters.


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Without this, an unhandled exception returns FastAPI's default 500,
    which can leak internal file paths/stack traces to the client."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred while processing this request.",
            "path": str(request.url.path),
        },
    )


def _require_store():
    if not store.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Data store not loaded. Run generate_testbed.py first."
        )


def _get_data_source(active_well_id: Optional[str] = None):
    """
    Pass 5: the single entry point every historical-events/DORS/corridors/
    analyze route uses to pick its data source, following the exact
    DB-first/memory-fallback/503 contract Pass 4 established for
    get_well/get_trajectory/get_formations/get_casing.

    Returns (source, data_source_label). `source` exposes the same
    attribute/method surface as the real in-memory `store` (wells_by_id,
    all_wells, all_trajectories, formation_tops_by_well,
    casing_records_by_well, events_by_well, all_events,
    get_events_for_top_wells, get_telemetry_at) -- either DbStoreSnapshot
    (built fresh from Postgres) or the real NWISDataStore singleton. Callers
    never branch on which one they got; that's the entire point of the
    shared surface.

    Raises HTTPException(503) if the database is configured but the
    snapshot build fails (connection refused, query error, etc.) -- never
    silently falls back to memory data captioned as if it were current.
    """
    if db_is_configured():
        try:
            target_well = active_well_id or store.active_well_id
            return db_service.build_store_snapshot(active_well_id=target_well), "postgres"
        except Exception as exc:
            logger.error(f"DB-backed store snapshot failed (DB configured but unreachable/erroring): {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")
    return store, "memory"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/v2/health", tags=["System"])
async def health():
    # Stays `async def` on purpose, unlike the data routes below: the unified
    # gateway's own /health awaits this through app/integrations/, and it no
    # longer does any blocking work -- cached_healthcheck() is an in-memory
    # read, refreshed on a timer off the request path.
    return {
        "service": "NWIS Backend Intelligence API",
        "version": "2.0.0",
        "status": "healthy" if store.is_loaded() else "degraded",
        "data_store": store.status(),
        # Phase 1 foundation: the canonical PostgreSQL/PostGIS layer
        # (database/schema.sql) is opt-in via NWIS_DATABASE_URL / NWIS_DB_*
        # env vars. "configured": False here means every endpoint below is
        # still served entirely by the in-memory NWISDataStore, exactly as
        # before this pass -- nothing regresses by leaving it unset.
        "database": db_healthcheck(),
        "engines": ["DORS", "StratigraphicCorrelator", "RiskCorridorEngine", "4PillarConfidence"],
        "auth": {
            "status": "enabled" if auth_enabled() else "disabled",
            "role": "X-API-Key required on all data/analysis endpoints when enabled",
            "rate_limiting": {
                "enabled": RATE_LIMIT_ENABLED,
                "max_requests": RATE_LIMIT_MAX_REQUESTS,
                "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            },
        },
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "NWIS Backend Intelligence API v2",
        "docs": "/docs",
        "status": "operational",
    }


# ---------------------------------------------------------------------------
# Wells
# ---------------------------------------------------------------------------

@app.get("/api/v2/wells", tags=["Wells"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def list_wells(
    field: str = Query(None, description="Filter by field name"),
    status: str = Query(None, description="Filter by well status"),
):
    """List all wells in the testbed, with optional field/status filter."""
    _require_store()
    wells = store.all_wells
    if field:
        wells = [w for w in wells if field.lower() in w.field.lower()]
    if status:
        wells = [w for w in wells if w.status.value == status.upper()]

    return {
        "total": len(wells),
        "wells": [w.model_dump() for w in wells],
    }


@app.get("/api/v2/wells/{well_id:path}", tags=["Wells"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_well(well_id: str):
    """
    Get full details for a single well. This is the "active well lookup"
    leg of the Phase 1 migrated vertical slice: when the database is
    configured (NWIS_DATABASE_URL/NWIS_DB_*), the well's own identity/
    metadata fields come from PostgreSQL (db/service.py); trajectory
    station count, formation tops, and event count are not yet migrated
    (task requirement #9 is well + nearby-well lookup specifically) and
    still come from the in-memory store either way, same as before.

    Database-failure behavior (Pass 2 hardening, 2026-10-04): if the
    database is configured but the call fails (connection refused, timeout,
    SQL error -- anything other than "well not found"), this now raises a
    genuine 503 instead of silently falling back to the in-memory store.
    The in-memory data can be stale or incomplete relative to Postgres, so
    serving it as if the request had succeeded would misrepresent what
    actually happened. If the database is simply unconfigured, the
    in-memory path below is the normal, unchanged dev-mode behavior.
    """
    _require_store()

    traj = store.all_trajectories.get(well_id)
    tops = store.formation_tops_by_well.get(well_id, [])
    events = store.events_by_well.get(well_id, [])

    if db_is_configured():
        try:
            well_dict = db_service.get_well(well_id)
            return {
                "well": well_dict,
                "trajectory_stations": len(traj.stations) if traj else 0,
                "formation_tops": [t.model_dump() for t in tops],
                "total_events": len(events),
                "data_source": "postgres",
            }
        except db_service.WellNotFoundError:
            raise HTTPException(404, f"Well '{well_id}' not found")
        except Exception as exc:
            logger.error(f"DB-backed get_well failed (DB configured but unreachable/erroring): {exc}")
            raise HTTPException(
                status_code=503,
                detail="Database is configured but currently unavailable. Try again shortly.",
            )

    well = store.wells_by_id.get(well_id)
    if not well:
        raise HTTPException(404, f"Well '{well_id}' not found")

    return {
        "well": well.model_dump(),
        "trajectory_stations": len(traj.stations) if traj else 0,
        "formation_tops": [t.model_dump() for t in tops],
        "total_events": len(events),
        "data_source": "memory",
    }


@app.get("/api/v2/trajectory/{well_id:path}", tags=["Wells"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_trajectory(well_id: str):
    """
    Full real survey-station list (md/inclination/azimuth/tvd/ns/ew/tvdss)
    for a well, computed via minimum curvature from real WITSML/PDF survey
    data. Was loaded into the store and used internally (DORS trajectory
    scoring, stratigraphic depth track) but never exposed for a client to
    actually render the 3D path itself -- this powers the 3D trajectory
    viewer with the same real station data those engines already consume.

    Pass 4: database-backed when NWIS_DATABASE_URL is configured (reads
    trajectory_stations, seeded by database/migrate_seed.py), same 503-on-
    unreachable contract as get_well/get_map_wells. Falls back to the
    in-memory store only when the database is unconfigured.
    """
    _require_store()

    if db_is_configured():
        try:
            traj_dict = db_service.get_trajectory(well_id)
            if traj_dict is None:
                raise HTTPException(404, f"No trajectory data for well '{well_id}'")
            traj_dict["data_source"] = "postgres"
            return traj_dict
        except db_service.WellNotFoundError:
            raise HTTPException(404, f"Well '{well_id}' not found")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"DB-backed get_trajectory failed (DB configured but unreachable/erroring): {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")

    well = store.wells_by_id.get(well_id)
    if not well:
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
        "data_source": "memory",
    }


# ---------------------------------------------------------------------------
# Formations
# ---------------------------------------------------------------------------

@app.get("/api/v2/formations/{well_id:path}", tags=["Stratigraphy"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_formations(well_id: str):
    """Get formation tops for a well — feed for the Stratigraphic Track.

    Pass 4: database-backed when NWIS_DATABASE_URL is configured (reads
    formation_tops); falls back to the in-memory store when unconfigured,
    and raises 503 (never silent memory fallback) if configured but
    unreachable/erroring — same contract as get_well/get_trajectory."""
    _require_store()

    if db_is_configured():
        try:
            tops = db_service.get_formations_for_well(well_id)
            if tops is None:
                raise HTTPException(404, f"No formation data for well '{well_id}'")
            return {"well_id": well_id, "total": len(tops), "formation_tops": tops, "data_source": "postgres"}
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"DB-backed get_formations failed: {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")

    tops = store.formation_tops_by_well.get(well_id)
    if tops is None:
        raise HTTPException(404, f"No formation data for well '{well_id}'")
    return {
        "well_id": well_id,
        "total": len(tops),
        "formation_tops": [t.model_dump() for t in tops],
        "data_source": "memory",
    }


@app.get("/api/v2/formations", tags=["Stratigraphy"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_all_formations(
    formation_name: str = Query(None, description="Filter by formation name"),
):
    """Get all formation tops across all wells.

    Pass 4: database-backed when NWIS_DATABASE_URL is configured."""
    _require_store()

    if db_is_configured():
        try:
            all_tops = db_service.get_all_formations(formation_name=formation_name)
            return {"total": len(all_tops), "formation_tops": all_tops, "data_source": "postgres"}
        except Exception as exc:
            logger.error(f"DB-backed get_all_formations failed: {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")

    all_tops = []
    for tops in store.formation_tops_by_well.values():
        if formation_name:
            tops = [t for t in tops if formation_name.lower() in t.formation_name.lower()]
        all_tops.extend([t.model_dump() for t in tops])
    return {"total": len(all_tops), "formation_tops": all_tops, "data_source": "memory"}


# ---------------------------------------------------------------------------
# Casing
#
# store.casing_records_by_well has been loaded from real_data/ since logger
# Step 20-23 (real casing/cementing records, 2 real Volve wells) but had no
# route exposing it -- the data existed in memory with nothing serving it.
# Mirrors the formations endpoint pair above exactly.
# ---------------------------------------------------------------------------

@app.get("/api/v2/casing/{well_id:path}", tags=["Casing"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_casing(well_id: str):
    """Get casing records for a well. Real data exists for 2 Volve wells only — a well with no casing data returns an empty list, not a 404, since most wells (all synthetic ones) genuinely have none.

    Pass 4: database-backed when NWIS_DATABASE_URL is configured (reads
    casing_programs)."""
    _require_store()

    if db_is_configured():
        try:
            records = db_service.get_casing_for_well(well_id)
            return {"well_id": well_id, "total": len(records), "casing_records": records, "data_source": "postgres"}
        except Exception as exc:
            logger.error(f"DB-backed get_casing failed: {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")

    records = store.casing_records_by_well.get(well_id, [])
    return {
        "well_id": well_id,
        "total": len(records),
        "casing_records": [r.model_dump() for r in records],
        "data_source": "memory",
    }


@app.get("/api/v2/casing", tags=["Casing"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_all_casing():
    """Get all casing records across all wells that have them.

    Pass 4: database-backed when NWIS_DATABASE_URL is configured."""
    _require_store()

    if db_is_configured():
        try:
            all_records = db_service.get_all_casing()
            wells_with_casing = len({r["well_id"] for r in all_records})
            return {"total": len(all_records), "wells_with_casing": wells_with_casing, "casing_records": all_records, "data_source": "postgres"}
        except Exception as exc:
            logger.error(f"DB-backed get_all_casing failed: {exc}")
            raise HTTPException(503, detail="Database is configured but currently unavailable. Try again shortly.")

    all_records = []
    for records in store.casing_records_by_well.values():
        all_records.extend([r.model_dump() for r in records])
    return {"total": len(all_records), "wells_with_casing": len(store.casing_records_by_well), "casing_records": all_records, "data_source": "memory"}


# ---------------------------------------------------------------------------
# Drilling Events
# ---------------------------------------------------------------------------

# NOTE ON ROUTE ORDER: /api/v2/events/search MUST be registered before
# /api/v2/events/{well_id} below. FastAPI/Starlette matches routes in
# registration order, and {well_id} is a wildcard path segment — if it were
# registered first, a request to /api/v2/events/search would be matched as
# get_well_events(well_id="search") instead of reaching this endpoint at all
# (found and fixed before this ever shipped, not left as a latent bug).
@app.get("/api/v2/events/search", tags=["Drilling Events"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def search_events_semantic(
    query: str = Query(..., min_length=1, description="Free-text search, e.g. 'mud weight increase fixed wellbore instability'"),
    hazard_type: str = Query(None, description="Optional: narrow to a hazard type first"),
    formation: str = Query(None, description="Optional: narrow to a formation first"),
    min_severity: str = Query(None, description="Optional: minimum severity"),
    depth_min: float = Query(None, ge=0),
    depth_max: float = Query(None, ge=0),
    top_n: int = Query(10, ge=1, le=50),
):
    """
    Free-text / semantic search over drilling event narratives, mitigation
    descriptions, and outcomes — the actual "lessons learned" text, not just
    structured metadata. This is the part of PS 26121 outcome iii ("searchable
    knowledge repository of drilling events, lessons learned, operational
    challenges, and mitigation measures") that GET /api/v2/events alone
    cannot answer: e.g. "find events where a mud weight increase fixed
    wellbore instability" has no structured field to filter on.

    Structured filters (hazard_type/formation/severity/depth) narrow the
    candidate set first if supplied; `query` then ranks what remains.
    `search_mode` in the response tells you whether ranking was genuinely
    semantic (sentence-transformers loaded) or a keyword-match fallback (not
    installed / failed to load) — never silently one or the other.

    Pass 5: database-backed when NWIS_DATABASE_URL is configured and
    reachable (reads drilling_events), same DB-first/memory-fallback/503
    contract as every other migrated route — see _get_data_source().
    """
    _require_store()
    from app.modules.nwis.search.knowledge_search import search_events as run_search

    source, data_source = _get_data_source()
    candidates = _filter_events_structured(source.all_events, hazard_type, formation, min_severity, depth_min, depth_max)
    ranked, mode = run_search(query, candidates, top_n=top_n)

    return {
        "query": query,
        "search_mode": mode,
        "total_candidates": len(candidates),
        "total_returned": len(ranked),
        # Facets over ALL matching candidates, not just the top_n ranked and
        # returned — matches GDR's pattern of showing the full breakdown even
        # when only a page of results is displayed.
        "facets": _compute_facets(candidates),
        "results": [
            {"relevance_score": round(score, 4), "event": event.model_dump()}
            for event, score in ranked
        ],
        "data_source": data_source,
    }


@app.get("/api/v2/events/{well_id:path}", tags=["Drilling Events"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_well_events(well_id: str):
    """Get all drilling events for a well (for the Evidence Proof Modal).

    Pass 5: database-backed when configured — see _get_data_source()."""
    _require_store()
    source, data_source = _get_data_source()
    events = source.events_by_well.get(well_id, [])
    return {
        "well_id": well_id,
        "total": len(events),
        "total_npt_hours": round(sum(e.npt_hours for e in events), 2),
        "events": [e.model_dump() for e in events],
        "data_source": data_source,
    }


def _filter_events_structured(
    events: list,
    hazard_type: str = None,
    formation: str = None,
    min_severity: str = None,
    depth_min: float = None,
    depth_max: float = None,
):
    """Shared structured-field filtering, used by both /events (metadata-only
    filtering) and /events/search (structured filter + free-text ranking) so
    the two can't silently drift into different filtering behavior."""
    severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    min_sev_num = severity_order.get((min_severity or "LOW").upper(), 0)

    if hazard_type:
        events = [e for e in events if e.event_type.value == hazard_type.upper()]
    if formation:
        events = [e for e in events if e.formation and formation.lower() in e.formation.lower()]
    if depth_min is not None:
        events = [e for e in events if e.depth_start_md_m >= depth_min]
    if depth_max is not None:
        events = [e for e in events if e.depth_start_md_m <= depth_max]
    if min_severity:
        events = [e for e in events if severity_order.get(e.severity, 0) >= min_sev_num]
    return events


def _compute_facets(events: list) -> dict:
    """
    Facet counts over the current result set — the pattern GDR's search UI
    uses ("Utah FORGE, UT (372)" next to each filter option). Lets a caller
    (or future frontend) show "14 STUCK_PIPE, 12 WELLBORE_INSTABILITY, ..."
    without issuing a separate query per facet value.

    NOTE: computed over the current filtered set, not independently per facet
    — i.e. these are "among your current results" counts, not "if you only
    changed this one filter, keeping the others" counts (which would need
    recomputing each facet with that one filter excluded). Simpler, and
    honest about what it is; worth upgrading if the event volume ever grows
    enough that the distinction matters in practice.
    """
    from collections import Counter
    return {
        "hazard_type": dict(Counter(e.event_type.value for e in events)),
        "formation": dict(Counter(e.formation for e in events if e.formation)),
        "severity": dict(Counter(e.severity for e in events)),
        "well_id": dict(Counter(e.well_id for e in events)),
    }


@app.get("/api/v2/events", tags=["Drilling Events"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def search_events(
    hazard_type: str = Query(None, description="Filter by hazard type (e.g. MUD_LOSS)"),
    formation: str = Query(None, description="Filter by formation name"),
    min_severity: str = Query(None, description="Minimum severity (LOW/MEDIUM/HIGH/CRITICAL)"),
    depth_min: float = Query(None, ge=0, description="Minimum depth (m MD)"),
    depth_max: float = Query(None, ge=0, description="Maximum depth (m MD)"),
):
    """
    Structured-field filtering over the drilling event repository (hazard
    type, formation, depth, severity). For free-text search over the actual
    narrative/lessons-learned/mitigation text, see GET /api/v2/events/search.
    Implements PS 26121 requirement iii: searchable historical knowledge base.

    Pass 5: database-backed when configured — see _get_data_source().
    """
    _require_store()
    source, data_source = _get_data_source()
    events = _filter_events_structured(source.all_events, hazard_type, formation, min_severity, depth_min, depth_max)

    return {
        "total": len(events),
        "total_npt_hours": round(sum(e.npt_hours for e in events), 2),
        "facets": _compute_facets(events),
        "events": [e.model_dump() for e in events[:100]],  # cap at 100 for API response
        "data_source": data_source,
    }




# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

@app.get("/api/v2/telemetry/{well_id:path}", tags=["Telemetry"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_telemetry(
    well_id: str,
    depth: float = Query(..., ge=0, description="Current drill bit depth (m MD)"),
    window: int = Query(300, description="Number of recent records to return"),
):
    """Get live telemetry records strictly for the requested well."""
    _require_store()
    source, data_source = _get_data_source(active_well_id=well_id)
    if well_id not in source.wells_by_id and well_id != store.active_well_id:
        raise HTTPException(404, f"Well '{well_id}' not found")

    records = source.get_telemetry_at(depth, window=window, well_id=well_id)
    latest = records[-1] if records else None

    return {
        "well_id": well_id,
        "depth_m": depth,
        "records_returned": len(records),
        "latest": latest.model_dump() if latest else None,
        "records": [r.model_dump() for r in records[-50:]],  # last 50 for frontend chart
        "data_source": data_source,
    }


# ---------------------------------------------------------------------------
# Stratigraphic Depth Alignment (Engine 2 — was implemented but never
# reachable from any endpoint; align_horizons_across_wells/stratigraphic_depth
# in engines/stratigraphic_correlator.py had no caller anywhere in the
# codebase until this endpoint was added)
# ---------------------------------------------------------------------------

@app.get("/api/v2/stratigraphic_depth_track/{well_id:path}", tags=["Stratigraphy"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def stratigraphic_depth_track(
    well_id: str,
    depth: float = Query(..., ge=0, description="Active bit depth (m MD)"),
    top_n: int = Query(10, description="Number of offset wells to align"),
):
    """
    For the active bit position, compute the equivalent formation depth in
    each top-ranked offset well — powers the "Stratigraphic Depth Track"
    visualization and eliminates the "Trajectory Trap" (false MD comparisons
    between vertical and directional wells) per PS 26121 requirement iv.

    Pass 5: database-backed when configured — see _get_data_source(). Every
    store.* reference below was traced and replaced, not just the final
    align_horizons_across_wells() call — the earlier active_well/active_traj/
    active_tops/offset_wells lookups all come from the same source now too.
    """
    _require_store()
    from app.modules.nwis.engines.dors_engine import rank_offset_wells
    from app.modules.nwis.engines.stratigraphic_correlator import formation_at_depth, align_horizons_across_wells

    source, data_source = _get_data_source()

    active_well = source.wells_by_id.get(well_id)
    if not active_well:
        raise HTTPException(404, f"Well '{well_id}' not found")

    active_traj = source.all_trajectories.get(well_id)
    if active_traj is None:
        raise HTTPException(404, f"No trajectory data for well '{well_id}'")

    active_tops = source.formation_tops_by_well.get(well_id, [])
    active_fm = formation_at_depth(active_tops, depth)

    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=depth,
        active_formation=active_fm.formation_name if active_fm else None,
        all_wells=source.all_wells,
        all_trajectories=source.all_trajectories,
        all_formation_tops=source.formation_tops_by_well,
        all_events=source.events_by_well,
        top_n=top_n,
    )
    offset_wells = [source.wells_by_id[r.well_id] for r in rankings if r.well_id in source.wells_by_id]

    alignment = align_horizons_across_wells(
        active_md=depth,
        active_well=active_well,
        active_traj=active_traj,
        active_tops=active_tops,
        offset_wells=offset_wells,
        offset_trajs=source.all_trajectories,
        offset_tops_map=source.formation_tops_by_well,
    )

    return {
        "active_well_id": well_id,
        "depth_m": depth,
        "formation_at_bit": active_fm.formation_name if active_fm else None,
        "wells_aligned": len(alignment),
        "alignment": alignment,
        "data_source": data_source,
    }


# ---------------------------------------------------------------------------
# DORS Offset Ranking
# ---------------------------------------------------------------------------

@app.get("/api/v2/offset_rank/{well_id:path}", tags=["DORS Engine"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def rank_offsets(
    well_id: str,
    depth: float = Query(..., ge=0, description="Current bit depth (m MD)"),
    radius_km: float = Query(25.0, description="DORS spatial SCORING DECAY divisor, NOT a hard exclusion radius — a well beyond this distance scores lower on the spatial factor but is still ranked and returned. Use max_distance_km for a real hard filter."),
    top_n: int = Query(10, description="Number of top offset wells to return"),
    max_distance_km: float = Query(None, description="Optional HARD exclusion filter (Haversine km from the active well's surface location). Unlike radius_km, a well strictly beyond this distance is removed from the result entirely. Omit for the original unfiltered-ranking behavior (default, unchanged)."),
):
    """
    Run the DORS 5-factor offset well ranking engine.
    Implements PS 26121 requirement ii: nearby well relevance scoring.

    IMPORTANT — radius_km is a scoring decay, not a filter (Priority 2 audit
    finding, documented not silently changed): score_spatial() computes
    max(0, 1 - distance/radius_km), so every well in the catalog is still
    scored and can still appear in `rankings` regardless of radius_km's
    value — only its spatial sub-score changes. This preserves the original
    DORS ranking formula and every existing caller's behavior (Command
    Center, Geological Correlation, Dashboard all rely on getting a full
    ranked list back, not a filtered one). Pass max_distance_km if you
    specifically need wells beyond a distance excluded from the response —
    this is new, additive, and opt-in; omitting it changes nothing.

    Pass 5: database-backed when configured — see _get_data_source(). Every
    store.* reference below (not just the rank_offset_wells() call) now
    comes from the same resolved source — verified to produce byte-identical
    rankings/scores against the memory path for the same inputs before this
    was wired in (see AUDIT/13_PRODUCT_COMPLETION.md).
    """
    _require_store()
    source, data_source = _get_data_source()
    active_well = source.wells_by_id.get(well_id)
    if not active_well:
        raise HTTPException(404, f"Well '{well_id}' not found")

    from app.modules.nwis.engines.dors_engine import rank_offset_wells, haversine_km
    from app.modules.nwis.engines.stratigraphic_correlator import formation_at_depth

    active_tops = source.formation_tops_by_well.get(well_id, [])
    active_fm = formation_at_depth(active_tops, depth)

    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=depth,
        active_formation=active_fm.formation_name if active_fm else None,
        all_wells=source.all_wells,
        all_trajectories=source.all_trajectories,
        all_formation_tops=source.formation_tops_by_well,
        all_events=source.events_by_well,
        r_max_km=radius_km,
        top_n=top_n,
    )

    hard_filter_applied = max_distance_km is not None
    if hard_filter_applied:
        rankings = [r for r in rankings if r.distance_km is not None and r.distance_km <= max_distance_km]

    return {
        "active_well_id": well_id,
        "depth_m": depth,
        "formation_at_bit": active_fm.formation_name if active_fm else None,
        "radius_km": radius_km,
        "radius_km_is_scoring_decay_not_a_filter": True,
        "max_distance_km": max_distance_km,
        "hard_filter_applied": hard_filter_applied,
        "total_ranked": len(rankings),
        "rankings": [r.model_dump() for r in rankings],
        "dors_formula": "DORS = 0.20·S_spatial + 0.30·S_formation + 0.20·S_depth + 0.15·S_trajectory + 0.15·S_hazard",
        "data_source": data_source,
    }


# ---------------------------------------------------------------------------
# Full Intelligence Analysis
# ---------------------------------------------------------------------------

@app.get("/api/v2/analyze/{well_id:path}", tags=["NWIS Intelligence"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def analyze_well(
    well_id: str,
    depth: float = Query(..., ge=0, description="Current bit depth (m MD)"),
    radius_km: float = Query(25.0),
    mud_weight_ppg: float = Query(9.5, description="Current mud weight (ppg)"),
):
    """
    FULL NWIS Intelligence Analysis at a given bit depth.
    Runs: DORS → Stratigraphy → Risk Corridors → 4-Pillar Confidence
    Returns complete NWISAnalysisResponse.

    Pass 5: database-backed when configured — see _get_data_source().
    NWISOrchestrator itself is unmodified; it's handed a DbStoreSnapshot
    (same attribute/method surface as the real in-memory store, including
    get_telemetry_at — see that method's own docstring for why telemetry
    specifically stays sourced from the in-memory singleton either way).
    """
    _require_store()
    source, data_source = _get_data_source(active_well_id=well_id)
    if well_id not in source.wells_by_id:
        raise HTTPException(404, f"Well '{well_id}' not found")

    try:
        orchestrator = NWISOrchestrator(source)
        result = orchestrator.analyze(
            active_well_id=well_id,
            current_depth_m=depth,
            r_max_km=radius_km,
            mud_weight_ppg=mud_weight_ppg,
        )
        result_dict = result.model_dump()
        result_dict["data_source"] = data_source
        return result_dict
    except Exception as e:
        # Pass 2 hardening: was `HTTPException(500, f"Analysis error: {str(e)}")`,
        # which put raw exception text in the client-facing response --
        # inconsistent with the global exception_handler's "log full detail
        # server-side, return a generic message" pattern used everywhere
        # else in this module. This route catches Exception itself and
        # raises HTTPException before the global handler ever sees it, so
        # it needed its own explicit fix.
        logger.exception(f"Analysis failed for well '{well_id}': {e}")
        raise HTTPException(500, detail="An unexpected error occurred while running the analysis.")


# ---------------------------------------------------------------------------
# Risk Corridors
# ---------------------------------------------------------------------------

@app.get("/api/v2/corridors/{well_id:path}", tags=["Risk Corridors"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_risk_corridors(
    well_id: str,
    depth: float = Query(..., ge=0, description="Current bit depth (m MD)"),
    hazard_type: str = Query(None, description="Filter by hazard type"),
):
    """
    Get all historical risk corridors ahead of current bit depth.
    Implements PS 26121 requirement v: predictive risk analytics.

    Pass 5: database-backed when configured — see _get_data_source(). Every
    store.* reference below (active_well, active_tops, the DORS inputs, AND
    get_events_for_top_wells) now comes from the same resolved source —
    verified to produce the same corridor set as the memory path for the
    same inputs before this was wired in.
    """
    _require_store()
    from app.modules.nwis.engines.risk_corridor_engine import identify_risk_corridors

    source, data_source = _get_data_source()
    active_well = source.wells_by_id.get(well_id)
    if not active_well:
        raise HTTPException(404, f"Well '{well_id}' not found")

    # Get top 10 offset wells
    from app.modules.nwis.engines.dors_engine import rank_offset_wells
    from app.modules.nwis.engines.stratigraphic_correlator import formation_at_depth

    active_tops = source.formation_tops_by_well.get(well_id, [])
    active_fm = formation_at_depth(active_tops, depth)
    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=depth,
        active_formation=active_fm.formation_name if active_fm else None,
        all_wells=source.all_wells,
        all_trajectories=source.all_trajectories,
        all_formation_tops=source.formation_tops_by_well,
        all_events=source.events_by_well,
        r_max_km=25.0,
        top_n=10,
    )

    top_events = source.get_events_for_top_wells([r.well_id for r in rankings])

    hazards_to_check = [HazardType(hazard_type)] if hazard_type else list(HazardType)
    all_corridors = []
    for h in hazards_to_check:
        try:
            corridors = identify_risk_corridors(top_events, h, depth)
            all_corridors.extend(corridors)
        except Exception as e:
            # Was a bare `except Exception: pass` — a failure clustering
            # corridors for ONE hazard type silently dropped that hazard's
            # corridors from the response with zero visible signal, while
            # the endpoint returned 200 OK as if every hazard type had been
            # checked. Logged instead, consistent with data_store.py's
            # loaders.
            logger.warning(f"Corridor clustering failed for hazard {h.value} on well {well_id}: {e}")

    all_corridors.sort(key=lambda c: c.depth_start_m)

    return {
        "well_id": well_id,
        "depth_m": depth,
        "formation_at_bit": active_fm.formation_name if active_fm else None,
        "total_corridors": len(all_corridors),
        "corridors": [c.model_dump() for c in all_corridors],
        "data_source": data_source,
    }


# ---------------------------------------------------------------------------
# Ahead-of-Bit Projected Corridor (new — 0-200m lookahead in 10m steps)
# ---------------------------------------------------------------------------

@app.get("/api/v2/ahead_of_bit/{well_id:path}", tags=["Risk Corridors"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_ahead_of_bit_corridor(
    well_id: str,
    depth: float = Query(..., ge=0, description="Current bit depth (m MD)"),
    max_lookahead_m: float = Query(200.0, ge=10.0, le=500.0, description="How far ahead to project (m)"),
    step_m: float = Query(10.0, ge=1.0, le=50.0, description="Projection step size (m)"),
    top_n: int = Query(10, description="Number of top offset wells to project against"),
):
    """
    Project 0-max_lookahead_m ahead of the active bit along the wellbore
    trajectory, mapping each step into the top-ranked offset wells to pull
    forward-looking per-hazard-type risk density — before the bit actually
    reaches that depth (unlike GET /api/v2/corridors, which only reports
    corridors already present in the historical record for depths already
    at or behind, or barely ahead of, the bit).

    Pass 5: database-backed when configured — see _get_data_source(). Every
    store.* reference below (active_well, active_traj, active_tops, the
    DORS inputs, AND top_offset_wells/offset_trajectories/offset_tops_map/
    offset_events_map) now comes from the same resolved source. This is
    the last of the 8 routes originally left on the in-memory store by
    Pass 4 — verified live against the running server (data_source:
    postgres) after the other 7.
    """
    _require_store()
    from app.modules.nwis.engines.dors_engine import rank_offset_wells
    from app.modules.nwis.engines.stratigraphic_correlator import formation_at_depth
    from app.modules.nwis.engines.risk_corridor_engine import compute_ahead_of_bit_corridor

    source, data_source = _get_data_source()
    active_well = source.wells_by_id.get(well_id)
    if not active_well:
        raise HTTPException(404, f"Well '{well_id}' not found")

    active_traj = source.all_trajectories.get(well_id)
    active_tops = source.formation_tops_by_well.get(well_id, [])
    active_fm = formation_at_depth(active_tops, depth)

    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=depth,
        active_formation=active_fm.formation_name if active_fm else None,
        all_wells=source.all_wells,
        all_trajectories=source.all_trajectories,
        all_formation_tops=source.formation_tops_by_well,
        all_events=source.events_by_well,
        top_n=top_n,
    )
    top_offset_wells = [source.wells_by_id[r.well_id] for r in rankings if r.well_id in source.wells_by_id]

    result = compute_ahead_of_bit_corridor(
        active_well=active_well,
        active_traj=active_traj,
        active_tops=active_tops,
        current_md_m=depth,
        top_offset_wells=top_offset_wells,
        offset_trajectories=source.all_trajectories,
        offset_tops_map=source.formation_tops_by_well,
        offset_events_map=source.events_by_well,
        max_lookahead_m=max_lookahead_m,
        step_m=step_m,
    )

    result_dict = result.model_dump()
    result_dict["data_source"] = data_source
    return result_dict


# ---------------------------------------------------------------------------
# Map Data (all wells with coordinates for GIS map)
# ---------------------------------------------------------------------------

@app.get("/api/v2/map/wells", tags=["GIS Map"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def get_map_wells(
    center_well_id: str = Query(None, description="Well ID to measure distance from. Omit to return all wells unfiltered (default, unchanged behavior)."),
    radius_km: float = Query(None, description="Hard exclusion radius in km from center_well_id. Requires center_well_id. A well strictly outside this radius is NOT returned — this is a real spatial filter, unlike offset_rank's radius_km (see that endpoint's docstring)."),
):
    """
    Get wells with surface coordinates for the interactive GIS map. This is
    the "nearby wells" leg of the Phase 1 migrated vertical slice — active
    well lookup -> nearby wells -> well metadata (task requirement #9).
    Implements PS 26121 requirement ii: map-based well visualization.

    Radius semantics (Priority 2 fix, 2026-10-04; preserved exactly, task
    requirement #10): by default (no params) returns every well — no
    existing caller's behavior changes. When BOTH center_well_id and
    radius_km are given, this endpoint applies a genuine hard filter and
    excludes wells outside the radius. This is a real filter, deliberately
    distinct from offset_rank's radius_km, which is a scoring decay divisor,
    not an exclusion boundary — see that endpoint's docstring.

    When the database is configured (NWIS_DATABASE_URL/NWIS_DB_*), the hard
    filter runs as a PostGIS ST_DWithin geodesic query (db/repositories.py)
    instead of the in-memory Haversine loop below — same semantics, same
    response shape, database-side filtering per task requirement #4/#9.

    Database-failure behavior (Pass 2 hardening, 2026-10-04): if the
    database is configured but the call fails, this raises a genuine 503
    instead of silently falling back to the in-memory store -- see
    get_well's docstring above for the full rationale (same policy here).
    """
    _require_store()
    from app.modules.nwis.engines.dors_engine import haversine_km

    if db_is_configured():
        try:
            result = db_service.get_map_wells(center_well_id=center_well_id, radius_km=radius_km)
            for w in result["wells"]:
                w["is_active"] = w["well_id"] == store.active_well_id
            result["active_well_id"] = store.active_well_id
            result["data_source"] = "postgres"
            return result
        except db_service.WellNotFoundError:
            raise HTTPException(404, f"Well '{center_well_id}' not found")
        except Exception as exc:
            logger.error(f"DB-backed get_map_wells failed (DB configured but unreachable/erroring): {exc}")
            raise HTTPException(
                status_code=503,
                detail="Database is configured but currently unavailable. Try again shortly.",
            )

    center_well = None
    if center_well_id is not None:
        center_well = store.wells_by_id.get(center_well_id)
        if not center_well:
            raise HTTPException(404, f"Well '{center_well_id}' not found")

    map_data = []
    for w in store.all_wells:
        distance_km = None
        if center_well is not None:
            distance_km = round(haversine_km(center_well.surface_lat, center_well.surface_lon, w.surface_lat, w.surface_lon), 3)
            if radius_km is not None and w.well_id != center_well.well_id and distance_km > radius_km:
                continue
        events = store.events_by_well.get(w.well_id, [])
        map_data.append({
            "well_id": w.well_id,
            "well_name": w.well_name,
            "field": w.field,
            "lat": w.surface_lat,
            "lon": w.surface_lon,
            "status": w.status.value,
            "well_type": w.well_type.value,
            "total_depth_md_m": w.total_depth_md_m,
            "total_events": len(events),
            "is_active": w.well_id == store.active_well_id,
            "distance_km": distance_km,
        })
    return {
        "total": len(map_data),
        "active_well_id": store.active_well_id,
        "radius_filter_applied": center_well_id is not None and radius_km is not None,
        "wells": map_data,
        "data_source": "memory",
    }


# ---------------------------------------------------------------------------
# Live Replay Simulation (real-time alert stream)
# ---------------------------------------------------------------------------

@app.get("/api/v2/live/replay/{well_id:path}", tags=["Live Replay"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def live_replay(
    request: Request,
    well_id: str,
    n_ticks: int = Query(80, ge=1, le=1000, description="Number of depth steps across the replay"),
    tick_seconds: float = Query(0.5, ge=0.05, le=10.0, description="Real seconds between pushed updates"),
    start_depth_m: float = Query(None, ge=0, description="Defaults to the well's shallowest surveyed depth"),
    end_depth_m: float = Query(None, ge=0, description="Defaults to the well's deepest surveyed depth"),
):
    """
    Server-Sent Events stream: pushes a compact risk/alert summary as the
    simulated bit depth advances through the well's trajectory. Implements
    PS 26121 outcome vi ("real-time alerts") and doubles as Phase 5's Live
    Replay Simulation — see live/replay_engine.py's module docstring for
    exactly what is and isn't "real-time" here (depth is replayed from the
    well's trajectory; sensor-anomaly scoring only has genuine telemetry for
    one depth window, honestly, not faked elsewhere).

    Test with: curl -N -H "X-API-Key: <key>" ".../api/v2/live/replay/WELL-HGJ-012"
    (a browser EventSource can't set custom headers, so a real frontend
    integration will need either a cookie-based session or a query-string
    token variant of auth — noted here as a known gap, not solved by this
    endpoint alone.)
    """
    _require_store()
    if well_id not in store.wells_by_id:
        raise HTTPException(404, f"Well '{well_id}' not found")
    if well_id not in store.all_trajectories:
        raise HTTPException(404, f"No trajectory data for well '{well_id}' — cannot replay")

    from app.modules.nwis.live.replay_engine import replay_well

    async def event_stream():
        try:
            async for update in replay_well(
                store, well_id,
                n_ticks=n_ticks, tick_seconds=tick_seconds,
                start_depth_m=start_depth_m, end_depth_m=end_depth_m,
                is_disconnected=request.is_disconnected,
            ):
                yield f"data: {json.dumps(update)}\n\n"
        except ValueError as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Agentic Knowledge Copilot — Gemini-backed tool-calling loop over this
# module's own existing routes, grounded answers with citations. See
# agent/orchestrator.py and agent/tools.py for the full design reasoning.
# ---------------------------------------------------------------------------

class AgentChatRequest(BaseModel):
    message: str
    active_well_id: Optional[str] = None
    active_depth: Optional[float] = None


@app.post("/api/v2/agent/chat", tags=["Knowledge Copilot"], dependencies=[Depends(require_api_key), Depends(rate_limit_agent)])
async def agent_chat(request: Request, body: AgentChatRequest):
    """
    Server-Sent Events stream of one agentic Knowledge Copilot turn.
    Frames: `tool_call`, `tool_result`, `answer`, `error`, and a final
    `mode` frame telling the frontend honestly whether this turn was
    answered by the real agent ("agentic") or every configured Gemini key
    was unreachable/exhausted and nothing was attempted ("keyword_fallback")
    — the frontend must never imply an LLM answered when it didn't, same
    honesty discipline as every other optional-capability surface in this
    codebase (docling, cloud OCR fallback, semantic search's own
    keyword-fallback path).

    Test with: curl -N -X POST -H "X-API-Key: <key>" -H "Content-Type: application/json" \\
      -d '{"message": "..."}' .../api/v2/agent/chat
    (a browser EventSource can't POST or set custom headers, so the real
    frontend integration uses manual fetch()+ReadableStream reading, same
    as api.ts's existing openLiveReplay().)
    """
    if not body.message or not body.message.strip():
        raise HTTPException(400, "message must not be empty")

    from app.modules.nwis.agent.orchestrator import (
        run_agent_turn,
        run_keyword_fallback,
        check_gemini_reachable,
        GeminiUnavailable,
    )

    async def event_stream():
        if not await check_gemini_reachable():
            yield f"event: mode\ndata: {json.dumps({'mode': 'keyword_fallback'})}\n\n"
            try:
                async for event in run_keyword_fallback(
                    body.message, active_well_id=body.active_well_id, active_depth=body.active_depth
                ):
                    if await request.is_disconnected():
                        break
                    yield f"data: {json.dumps(event, default=str)}\n\n"
            except Exception as exc:
                logger.warning(f"Keyword fallback failed: {exc}")
                yield f"data: {json.dumps({'type': 'error', 'detail': 'Keyword fallback search encountered an error.'})}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        yield f"event: mode\ndata: {json.dumps({'mode': 'agentic'})}\n\n"
        try:
            async for event in run_agent_turn(
                body.message, active_well_id=body.active_well_id, active_depth=body.active_depth
            ):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except GeminiUnavailable as exc:
            logger.warning(f"Agent turn failed, all Gemini keys became unreachable mid-turn: {exc}")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Lost connection to the AI assistant.'})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
