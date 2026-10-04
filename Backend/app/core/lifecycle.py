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

    logger.success("NWIS Unified Backend ready")
    yield

    logger.info("NWIS Unified Backend shutting down...")
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
