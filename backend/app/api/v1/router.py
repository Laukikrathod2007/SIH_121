"""
Master API v1 Router.
Combines Document Intelligence, Well Intelligence, Risk Analytics, and System Health routes.
"""

from fastapi import APIRouter
from app.modules.document_intelligence.routes import document_router
from app.modules.well_intelligence.routes import (
    well_router,
    intelligence_router,
    telemetry_router,
    knowledge_router,
    decision_router,
    benchmark_router,
)
from app.modules.physics_engine.routes.physics_routes import physics_router
from app.modules.predictive_analytics.routes.predictive_routes import predictive_router
from app.modules.well_intelligence.services.data_store import NWISDataStore

api_router = APIRouter()

# Mount Domain Sub-Routers
api_router.include_router(document_router)
# knowledge_router first: its /events/search must win over well_router's /events/{well_id}
api_router.include_router(knowledge_router)
api_router.include_router(decision_router)
api_router.include_router(benchmark_router)
api_router.include_router(well_router)
api_router.include_router(intelligence_router)
api_router.include_router(telemetry_router)
api_router.include_router(physics_router)
api_router.include_router(predictive_router)


@api_router.get("/health", tags=["System"])
async def health():
    """System health check and engine readiness report."""
    store = NWISDataStore()
    return {
        "service": "NWIS Backend Intelligence Core API",
        "version": "1.0.0",
        "status": "healthy" if store.is_loaded() else "degraded",
        "data_store": store.status(),
        "engines": [
            "DocumentIntelligencePipeline",
            "DORSEngine",
            "StratigraphicCorrelator",
            "RiskCorridorEngine",
            "FourPillarConfidenceEvaluator",
        ],
    }
