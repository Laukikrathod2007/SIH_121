"""
NWIS Module 01 — FastAPI Application Server
Serves the Document Intelligence Pipeline via REST API.

Endpoints:
  POST /api/v1/ingest          → Upload DDR/WCR PDF → Returns job_id
  GET  /api/v1/jobs/{job_id}   → Poll job status + progress
  GET  /api/v1/results/{doc_id} → Get full extraction result (WITSML JSON)
  GET  /api/v1/review/queue     → Documents awaiting human curation review
  POST /api/v1/review/{doc_id}/decision → Approve/reject a flagged document
  POST /api/v1/review/{doc_id}/annotate → Attach a field-level correction note
  GET  /api/v1/templates        → List all learned document templates
  GET  /api/v1/health           → Health check

CORS is open for local dev (React frontend on port 5173).
"""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from api.routes import ingest, status, results, review
from api.job_store import SQLiteJobStore
from api.auth import require_api_key, rate_limit_ingest, auth_enabled

# ---------------------------------------------------------------------------
# Upload Directory
# ---------------------------------------------------------------------------
UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Persistent Job Store (SQLite-backed — see api/job_store.py)
# ---------------------------------------------------------------------------
# Shared across all routes — imported by route modules. Survives restarts,
# unlike the plain in-memory dict this replaced.
JOB_STORE = SQLiteJobStore()

# ---------------------------------------------------------------------------
# File Logging (rotating, in addition to the default stderr sink)
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(
    LOG_DIR / "nwis_module01_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    enqueue=True,   # thread-safe — background pipeline jobs log from worker threads
    level="INFO",
    backtrace=False,
    diagnose=False,
)


# ---------------------------------------------------------------------------
# App Lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("NWIS Document Intelligence API starting...")
    logger.info("6-Layer Pipeline: PyMuPDF → Docling → NER → Template → Physics → JSON")
    logger.info("100% Air-Gapped | Zero Cloud Dependencies | WITSML Compliant")
    logger.info("=" * 60)

    # Pre-warm Docling converter (downloads model weights on first run)
    try:
        from pipeline.tier2_ocr_engine import _get_docling_converter
        asyncio.get_event_loop().run_in_executor(None, _get_docling_converter)
        logger.info("Docling pre-warm initiated in background")
    except Exception as exc:
        logger.warning(f"Docling pre-warm skipped: {exc}")

    yield

    logger.info("NWIS Document Intelligence API shutting down")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NWIS Document Intelligence API",
    description=(
        "Module 01: AI-powered OCR and entity extraction pipeline for "
        "Oil & Gas Daily Drilling Reports (DDR) and Well Completion Reports (WCR). "
        "6-layer architecture: PyMuPDF → Docling → NER → Template Learning → "
        "Physics Validation → WITSML JSON. "
        "100% air-gapped, no cloud APIs required."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Extra origins for a deployed frontend can be added via NWIS_CORS_ORIGINS
# (comma-separated) without touching code — e.g. the production cockpit URL.
_default_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
_extra_origins = [o.strip() for o in os.environ.get("NWIS_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------
# Without this, an unhandled exception anywhere in a route returns FastAPI's
# default 500 response — fine in dev, but it can leak internal file paths /
# stack traces to the client in production. Log the full traceback server-side,
# return a clean, stable error shape to the caller.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred while processing this request.",
            "path": str(request.url.path),
        },
    )


# ---------------------------------------------------------------------------
# Inject shared state into route modules
# ---------------------------------------------------------------------------
ingest.JOB_STORE = JOB_STORE
ingest.UPLOAD_DIR = UPLOAD_DIR
status.JOB_STORE = JOB_STORE
results.OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
review.OUTPUT_DIR = results.OUTPUT_DIR

# ---------------------------------------------------------------------------
# Include Routers
# ---------------------------------------------------------------------------
# Every route below requires X-API-Key when NWIS_API_KEY is configured (see
# api/auth.py) — these are the routes that mutate state, serve extracted
# document content, or (via ingest -> cloud_fallback) can trigger a paid
# third-party API call. Root/health/docs stay open for monitoring.
# rate_limit_ingest additionally caps /ingest specifically, since that's the
# one endpoint an attacker could use to burn cloud-fallback credits.
app.include_router(
    ingest.router, prefix="/api/v1", tags=["Document Ingestion"],
    dependencies=[Depends(require_api_key), Depends(rate_limit_ingest)],
)
app.include_router(
    status.router, prefix="/api/v1", tags=["Job Status"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    results.router, prefix="/api/v1", tags=["Extraction Results"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    review.router, prefix="/api/v1", tags=["Human Review"],
    dependencies=[Depends(require_api_key)],
)


# ---------------------------------------------------------------------------
# Root + Health
# ---------------------------------------------------------------------------
@app.get("/", tags=["System"])
async def root():
    return {
        "service": "NWIS Document Intelligence API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "pipeline": "6-layer air-gapped OCR + NER + Physics Validation",
        "compliance": "WITSML 2.0 | OSDU | IADC NPT Taxonomy",
    }


@app.get("/api/v1/health", tags=["System"])
async def health():
    """
    Health check endpoint — verifies pipeline components are available.

    Only PyMuPDF is a hard requirement (Tier 1 native extraction; nothing
    processes without it). Docling is an optional enhancement — its absence
    means scanned/raster PDF pages fall back to a plain-text extraction
    instead of layout-aware OCR, but native digital PDFs are unaffected. The
    entity extractor (Tier 3) is pure regex/rules-based and never depends on
    spaCy, so spaCy's presence is reported for visibility only and never
    affects overall status.
    """
    checks = {}
    required_ok = True

    # PyMuPDF — REQUIRED. Nothing in the pipeline runs without it.
    try:
        import fitz
        checks["pymupdf"] = {"status": "ok", "required": True, "version": fitz.version[0]}
    except ImportError:
        checks["pymupdf"] = {"status": "missing", "required": True, "install": "pip install pymupdf"}
        required_ok = False

    # Docling — OPTIONAL. Enables Tier 2 layout-aware OCR for scanned pages;
    # without it, scanned pages still get a best-effort text fallback.
    try:
        from docling.document_converter import DocumentConverter  # noqa: F401
        checks["docling"] = {"status": "ok", "required": False, "role": "Tier 2 OCR for scanned pages"}
    except ImportError:
        checks["docling"] = {
            "status": "not_installed",
            "required": False,
            "role": "Tier 2 OCR for scanned pages",
            "impact": "Scanned pages fall back to plain-text extraction (native digital PDFs unaffected)",
            "install": "pip install docling",
        }

    # spaCy — INFORMATIONAL ONLY. Tier 3 entity extraction is pure regex and
    # does not import spaCy; this check exists purely so the roadmap toward
    # a spaCy-based NER upgrade path is visible, not because it's load-bearing.
    try:
        import spacy
        checks["spacy"] = {"status": "ok", "required": False, "role": "not currently used by the pipeline", "version": spacy.__version__}
    except ImportError:
        checks["spacy"] = {"status": "not_installed", "required": False, "role": "not currently used by the pipeline"}

    # Cloud fallback (Reducto / Extend.ai) — OPTIONAL, and OFF unless an API
    # key is configured. Surfaced here because this is the one component that
    # can send document content outside the air-gapped boundary — its status
    # should always be visible at a glance, not just discoverable in logs.
    from pipeline.cloud_fallback import (
        CLOUD_FALLBACK_ENABLED,
        REDUCTO_API_KEY,
        EXTEND_API_KEY,
        CONFIDENCE_THRESHOLD,
        cloud_fallback_configured,
    )
    checks["cloud_fallback"] = {
        "status": "configured" if cloud_fallback_configured() else "not_configured",
        "required": False,
        "role": "Reducto/Extend.ai fallback for pages below the local confidence threshold",
        "reducto_key_set": bool(REDUCTO_API_KEY),
        "extend_key_set": bool(EXTEND_API_KEY),
        "master_switch_enabled": CLOUD_FALLBACK_ENABLED,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "note": "Sends the affected page's content to a third-party API when active — see pipeline/cloud_fallback.py",
    }

    # Auth — deliberately not gated behind the API key itself (this endpoint
    # is intentionally public), but visible so it's obvious at a glance
    # whether the deployment is actually protected.
    from api.auth import auth_enabled, RATE_LIMIT_ENABLED, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
    checks["auth"] = {
        "status": "enabled" if auth_enabled() else "disabled",
        "required": False,
        "role": "X-API-Key required on /ingest, /jobs, /results when enabled",
        "rate_limiting": {
            "enabled": RATE_LIMIT_ENABLED,
            "max_requests": RATE_LIMIT_MAX_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        },
    }

    return {
        "status": "healthy" if required_ok else "unhealthy",
        "components": checks,
        "jobs_in_queue": len(JOB_STORE),
    }


@app.get("/api/v1/templates", tags=["Template Learning"])
async def list_templates():
    """List all learned document coordinate templates."""
    from pipeline.layer4_template_learner import get_all_templates_summary
    templates = get_all_templates_summary()
    return {
        "total_templates": len(templates),
        "templates": templates,
        "description": (
            "Each template represents a learned DDR/WCR form layout. "
            "After 3+ documents of the same type, the system uses the template "
            "for near-instant extraction (< 50ms/page vs 2s/page)."
        ),
    }
