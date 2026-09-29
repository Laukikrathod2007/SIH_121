"""
Well Intelligence Routes Package.
"""

from app.modules.well_intelligence.routes.well_routes import router as well_router
from app.modules.well_intelligence.routes.intelligence_routes import router as intelligence_router
from app.modules.well_intelligence.routes.telemetry_routes import router as telemetry_router
from app.modules.well_intelligence.routes.knowledge_routes import router as knowledge_router
from app.modules.well_intelligence.routes.decision_routes import router as decision_router

__all__ = ["well_router", "intelligence_router", "telemetry_router", "knowledge_router", "decision_router"]
