"""
eRTMAC-NWIS Unified Backend Application.
Master FastAPI application serving Document Intelligence, DORS, Risk Corridors, and Telemetry.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure backend directory is in sys.path regardless of execution CWD
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import logger
from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 70)
    logger.info("Starting eRTMAC-NWIS Unified Backend Application...")
    logger.info(f"Version: {settings.VERSION} | Environment: Production-Ready")
    logger.info("Modules Active:")
    logger.info("  1. Document Intelligence Pipeline (Tier 1/2 OCR + NER + Rules + Layer 5 Physics)")
    logger.info("  2. Well Intelligence Core (DORS + Stratigraphy + Risk Corridors + 4-Pillar Confidence)")

    # Load synthetic testbed data into memory
    from app.core.bootstrap import ensure_demo_data, run_startup_pipeline
    try:
        ensure_demo_data()
    except Exception as exc:
        logger.error(f"Demo data generation failed: {exc}")

    store = NWISDataStore()
    try:
        store.load()
        logger.success(f"NWIS Data Store loaded successfully: {store.status()}")
        # Run the pipeline (bundled reports -> extraction -> knowledge repository -> alert scan)
        run_startup_pipeline()
    except Exception as exc:
        logger.error(f"Failed to load testbed data store: {exc}")

    # Pre-warm Module 5 Predictive Risk Inference Service & ML Models
    try:
        from app.modules.predictive_analytics.services.realtime_inference import RealTimeRiskInferenceService
        inference_service = RealTimeRiskInferenceService()
        logger.success("Module 5 Real-Time Risk Inference Service initialized & warmed up with pre-trained models.")
    except Exception as exc:
        logger.error(f"Failed to pre-warm Module 5 Predictive Risk service: {exc}")

    # Auto-start physics simulation so telemetry flows immediately on boot
    try:
        from app.modules.physics_engine.services.telemetry_streamer import LiveTelemetryStreamer
        streamer = LiveTelemetryStreamer()
        streamer.set_speed(5.0)
        streamer.physics_hz = 25.0
        streamer.broadcast_hz = 25.0
        await streamer.start()
        logger.success("Physics simulation auto-started at 5x | 25 Hz physics | 25 Hz broadcast.")
    except Exception as exc:
        logger.error(f"Failed to auto-start physics simulation: {exc}")

    yield

    # Graceful shutdown
    logger.info("Shutting down eRTMAC-NWIS Backend Core...")
    try:
        from app.modules.physics_engine.services.telemetry_streamer import LiveTelemetryStreamer
        await LiveTelemetryStreamer().pause()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Master Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "api_v1_docs": "/docs",
        "api_v1_prefix": settings.API_V1_STR,
        "status": "operational",
    }
