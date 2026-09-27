"""
Well Intelligence Services Package.
"""

from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.modules.well_intelligence.services.dors_engine import (
    score_spatial,
    score_formation,
    score_depth,
    score_trajectory,
    score_hazard,
    compute_dors,
    rank_offset_wells,
    haversine_km,
)
from app.modules.well_intelligence.services.stratigraphic_correlator import (
    tvd_at_md,
    tvdss_at_md,
    formation_at_depth,
    stratigraphic_depth,
    align_horizons_across_wells,
)
from app.modules.well_intelligence.services.risk_corridor_engine import (
    identify_risk_corridors,
    compute_confidence,
    assess_hazard,
    risk_level_from_score,
    severity_to_numeric,
)
from app.modules.well_intelligence.services.orchestrator import (
    NWISOrchestrator,
    ALL_HAZARDS,
)

__all__ = [
    "NWISDataStore",
    "score_spatial",
    "score_formation",
    "score_depth",
    "score_trajectory",
    "score_hazard",
    "compute_dors",
    "rank_offset_wells",
    "haversine_km",
    "tvd_at_md",
    "tvdss_at_md",
    "formation_at_depth",
    "stratigraphic_depth",
    "align_horizons_across_wells",
    "identify_risk_corridors",
    "compute_confidence",
    "assess_hazard",
    "risk_level_from_score",
    "severity_to_numeric",
    "NWISOrchestrator",
    "ALL_HAZARDS",
]
