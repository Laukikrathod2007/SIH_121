"""
NWIS Well Intelligence Module.
Provides DORS ranking, stratigraphic depth correlation, risk corridors, and telemetry analytics.
"""

from app.modules.well_intelligence.controllers.well_controller import (
    WellController,
    well_controller,
)
from app.modules.well_intelligence.routes import (
    well_router,
    intelligence_router,
    telemetry_router,
)

__all__ = [
    "WellController",
    "well_controller",
    "well_router",
    "intelligence_router",
    "telemetry_router",
]
