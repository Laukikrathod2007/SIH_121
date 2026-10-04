"""
NWIS Unified Backend -- ONE FastAPI application serving all of:
  Module 01 (Document Intelligence)     /api/v1/...
  Module 02 (NWIS well/geospatial/risk) /api/v2/...
  Module 04/05 (Physics + Predictive)   /api/v3/...
  Evidence/PDF delivery                 /api/evidence/...

The business logic of each module is untouched and lives where it always
did (modules/NN_*/). It is reached through canonical packages --
app.modules.document_intelligence / nwis / physics / predictive_analytics
(see app/modules/__init__.py) -- so every internal import is an ordinary,
unambiguous package import: no sys.path switching, no sys.modules surgery,
and nothing that depends on which request arrives first.

Run: cd Backend && python run.py
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import evidence
from app.core.config import CORS_ORIGINS, startup_security_check
from app.core.errors import register_exception_handlers
from app.core.lifecycle import lifespan
from app.core.logging import setup_logging
from app.integrations import m01_document_intel, m02_nwis_backend, m04_physics_predictive

startup_security_check()
setup_logging()

app = FastAPI(
    title="NWIS Unified Backend",
    description=(
        "eRTMAC-NWIS (SIH PS 26121) unified API: document intelligence, "
        "well/geospatial intelligence, physics digital twin + predictive "
        "analytics, and evidence/PDF delivery -- served by one process."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Each mount() imports its service once (ordinary import) and appends its
# already-built routes. Auth/rate-limit dependencies on those routes are the
# shared app.core.auth objects (the legacy auth modules re-export them).
m01_document_intel.mount(app)
m02_nwis_backend.mount(app)
m04_physics_predictive.mount(app)
app.include_router(evidence.router)


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "NWIS Unified Backend",
        "docs": "/docs",
        "status": "operational",
        "modules": ["document_intelligence", "nwis_backend", "physics_predictive", "evidence"],
    }


async def _module_health(name: str, probe, results: dict) -> bool:
    """Run one module's own health probe; never let it break the rollup."""
    try:
        results[name] = await probe()
        return results[name].get("status", "healthy") == "healthy"
    except Exception as exc:  # report the failure, don't hide it
        results[name] = {"status": "error", "detail": type(exc).__name__}
        return False


@app.get("/health", tags=["System"])
async def health():
    """Truthful aggregate health: each module's OWN health check, not a
    re-implementation. A missing optional dependency degrades that module's
    entry; it does not make the whole API look dead."""
    results: dict = {}
    oks = [
        await _module_health("document_intelligence", m01_document_intel.health, results),
        await _module_health("nwis_backend", m02_nwis_backend.health, results),
        await _module_health("physics_predictive", m04_physics_predictive.health, results),
        await _module_health("evidence", evidence.evidence_health, results),
    ]
    return {"status": "healthy" if all(oks) else "degraded", "modules": results}


@app.get("/ready", tags=["System"])
async def ready():
    """Readiness: cheap check that the module singletons exist and the NWIS
    store is loaded. Does NOT load models -- that happens once, at startup."""
    return {
        "ready": True,
        "m02_store_loaded": m02_nwis_backend.store().is_loaded(),
        "physics_sim_loop_running": m04_physics_predictive.sim_loop_running(),
    }
