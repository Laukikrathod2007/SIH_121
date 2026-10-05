"""
ONE combined lifespan for the unified app.

Startup runs each module's initialisation as an independent step: a failure
in one is logged and the others still run (the same "degrade, don't raise"
philosophy the NWIS store already used). Nothing in here is triggered by
merely importing a module -- every background task and heavy resource is
started here, exactly once, and released in the matching shutdown steps.

The legacy services' own per-module lifespans never run (FastAPI only enters
the lifespan of the app that is actually served, this one).
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.integrations import m01_document_intel, m02_nwis_backend, m04_physics_predictive


def _log_prewarm_result(name: str):
    def _done(fut: "asyncio.Future") -> None:
        exc = fut.exception()
        if exc is not None:
            logger.warning(f"{name} pre-warm failed (feature degrades, app continues): {exc}")
        else:
            logger.info(f"{name} pre-warm complete")

    return _done


# How often the database reachability probe runs. GET /health reads the cached
# result of this instead of probing inline -- see cached_healthcheck() in
# modules/02_nwis_backend/db/connection.py for why that mattered. 30s keeps the
# reported status recent enough to be useful while reducing the probe rate from
# "every healthcheck poll, forever" (~17k round trips/day against a free-tier
# database) to 2/minute.
_DB_HEALTH_REFRESH_SECONDS = 30.0


async def _db_health_refresh_loop() -> None:
    """Keep the database-status cache warm, off the request path.

    Every iteration is contained: this task is created once and never awaited,
    so an escaping exception would kill it silently and freeze the reported
    status at whatever it last saw -- stale data presented as current. A failed
    probe is already captured as a result by healthcheck() itself; this guard is
    for anything unexpected around it.
    """
    from app.modules.nwis.db.connection import is_configured, refresh_health_cache

    if not is_configured():
        logger.info("Database not configured -- health refresh loop not started")
        return

    while True:
        try:
            await asyncio.to_thread(refresh_health_cache)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Database health refresh raised unexpectedly")
        await asyncio.sleep(_DB_HEALTH_REFRESH_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("NWIS Unified Backend starting...")
    logger.info("=" * 60)
    loop = asyncio.get_running_loop()

    try:
        fut = loop.run_in_executor(None, m01_document_intel.docling_prewarm())
        fut.add_done_callback(_log_prewarm_result("M01 Docling"))
        logger.info("M01 Docling pre-warm scheduled in background")
    except Exception:
        logger.exception("M01 Docling pre-warm failed to schedule")

    try:
        m02_nwis_backend.store().load()
        logger.success("M02 data store loaded")
    except Exception:
        logger.exception("M02 data store load failed")  # store.load() also self-catches

    try:
        fut = loop.run_in_executor(None, m02_nwis_backend.search_prewarm())
        fut.add_done_callback(_log_prewarm_result("M02 embedding model"))
        logger.info("M02 embedding pre-warm scheduled in background")
    except Exception:
        logger.exception("M02 embedding pre-warm failed to schedule")

    try:
        started = await m04_physics_predictive.start_sim_loop()
        logger.info("M04 physics simulation loop " + ("started" if started else "already running (not restarted)"))
    except Exception:
        logger.exception("M04 simulation loop failed to start")

    db_health_task: "asyncio.Task | None" = None
    try:
        db_health_task = asyncio.create_task(_db_health_refresh_loop(), name="nwis-db-health-refresh")
        logger.info("Database health refresh loop started")
    except Exception:
        logger.exception("Database health refresh loop failed to start")

    logger.success("NWIS Unified Backend ready")
    yield

    logger.info("NWIS Unified Backend shutting down...")
    if db_health_task is not None:
        db_health_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await db_health_task
    try:
        await m04_physics_predictive.stop_sim_loop()
    except Exception:
        logger.exception("M04 simulation loop failed to stop cleanly")
    try:
        from app.modules.nwis.db.connection import close_pool

        if close_pool():
            logger.info("NWIS database connection pool closed")
    except Exception:
        logger.exception("NWIS database pool failed to close cleanly")
    logger.info("NWIS Unified Backend shutdown complete")
