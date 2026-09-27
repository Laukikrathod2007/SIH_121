"""
ML Data Engineering Pipeline -- Depth/Time Alignment.

Implements Module 5 Data Pipeline Sections 10, 58-59:
- Uses Module 4 as the authoritative geological coordinate resolver.
- Synchronizes time-indexed telemetry with depth-indexed wellbore state:
  timestamp -> MD -> TVD -> TVDSS -> formation -> stratigraphic coordinate (xi).
- Calculates distance to formation boundaries (top and base).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.modules.well_intelligence.services.xi_correlator import compute_xi
from app.modules.physics_engine.services.formation import FormationModel, default_demo_formations


class DepthTimeAligner:
    """Synchronizes time-series telemetry with Module 4 geological coordinates."""

    def __init__(self, formation_model: Optional[FormationModel] = None):
        self.formation_model = formation_model or FormationModel(default_demo_formations())

    def align_record(
        self,
        record: Dict[str, Any],
        kb_elevation_m: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Enriches a raw or cleaned telemetry record with synchronized geological coordinates.
        """
        depth_info = record.get("depth", {})
        md_m = float(depth_info.get("md_m", record.get("channels", {}).get("md_m", 0.0)))
        tvd_m = float(depth_info.get("tvd_m", md_m))
        tvdss_m = float(depth_info.get("tvdss_m", tvd_m - kb_elevation_m))

        fm = self.formation_model.at_depth(tvdss_m)
        if fm:
            formation_name = fm.name
            thickness = max(1.0, fm.thickness_m)
            xi = (tvdss_m - fm.top_tvdss_m) / thickness
            dist_top = tvdss_m - fm.top_tvdss_m
            dist_base = fm.base_tvdss_m - tvdss_m
        else:
            formation_name = "Unknown"
            xi = 0.0
            dist_top = 0.0
            dist_base = 0.0

        enriched = dict(record)
        enriched["geology"] = {
            "formation_name": formation_name,
            "xi": round(xi, 4),
            "top_tvdss_m": fm.top_tvdss_m if fm else 0.0,
            "base_tvdss_m": fm.base_tvdss_m if fm else 0.0,
            "distance_to_top_m": round(dist_top, 2),
            "distance_to_base_m": round(dist_base, 2),
        }
        return enriched

    def align_batch(
        self,
        records: List[Dict[str, Any]],
        kb_elevation_m: float = 10.0,
    ) -> List[Dict[str, Any]]:
        return [self.align_record(r, kb_elevation_m) for r in records]
