"""
eRTMAC-NWIS Unified Backend Application.
Master FastAPI application serving Document Intelligence, DORS, Risk Corridors, and Telemetry.
"""

from __future__ import annotations
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
    store = NWISDataStore()
    try:
        store.load()
        logger.success(f"NWIS Data Store loaded successfully: {store.status()}")
    except Exception as exc:
        logger.error(f"Failed to load testbed data store: {exc}")

    yield

    logger.info("Shutting down eRTMAC-NWIS Backend Core...")


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
