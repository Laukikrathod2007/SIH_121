"""
Well Intelligence Controller.
Handles orchestration of well repository queries, DORS ranking runs, hazard assessments, and telemetry streams.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import HTTPException

from app.core.logging import logger
from app.modules.well_intelligence.models.schemas import (
    Well,
    WellTrajectory,
    FormationTop,
    DrillingEvent,
    HazardType,
    RiskLevel,
    OffsetWellRanking,
    RiskCorridor,
    NWISAnalysisResponse,
)
from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.modules.well_intelligence.services.dors_engine import rank_offset_wells
from app.modules.well_intelligence.services.stratigraphic_correlator import formation_at_depth
from app.modules.well_intelligence.services.risk_corridor_engine import identify_risk_corridors
from app.modules.well_intelligence.services.orchestrator import NWISOrchestrator


class WellController:
    """Controller managing Well queries, DORS calculations, and risk analytics."""

    def __init__(self, store: Optional[NWISDataStore] = None):
        self.store = store or NWISDataStore()

    def _require_store(self):
        if not self.store.is_loaded():
            raise HTTPException(
                status_code=503,
                detail="Data store not loaded. Generate testbed data or start server cleanly."
            )

    def list_wells(self, field: Optional[str] = None, status: Optional[str] = None) -> dict:
        self._require_store()
        wells = self.store.all_wells
        if field:
            wells = [w for w in wells if field.lower() in w.field.lower()]
        if status:
            wells = [w for w in wells if w.status.value == status.upper()]
        return {
            "total": len(wells),
            "wells": [w.model_dump() for w in wells],
        }

    def get_well_details(self, well_id: str) -> dict:
        self._require_store()
        well = self.store.wells_by_id.get(well_id)
        if not well:
            raise HTTPException(404, f"Well '{well_id}' not found")

        traj = self.store.all_trajectories.get(well_id)
        tops = self.store.formation_tops_by_well.get(well_id, [])
        events = self.store.events_by_well.get(well_id, [])

        return {
            "well": well.model_dump(),
            "trajectory_stations": len(traj.stations) if traj else 0,
            "formation_tops": [t.model_dump() for t in tops],
            "total_events": len(events),
        }

    def get_formation_tops(self, well_id: str) -> dict:
        self._require_store()
        tops = self.store.formation_tops_by_well.get(well_id)
        if tops is None:
            raise HTTPException(404, f"No formation data for well '{well_id}'")
        return {
            "well_id": well_id,
            "total": len(tops),
            "formation_tops": [t.model_dump() for t in tops],
        }

    def get_all_formations(self, formation_name: Optional[str] = None) -> dict:
        self._require_store()
        all_tops = []
        for tops in self.store.formation_tops_by_well.values():
            if formation_name:
                tops = [t for t in tops if formation_name.lower() in t.formation_name.lower()]
            all_tops.extend([t.model_dump() for t in tops])
        return {"total": len(all_tops), "formation_tops": all_tops}

    def get_well_events(self, well_id: str) -> dict:
        self._require_store()
        events = self.store.events_by_well.get(well_id, [])
        return {
            "well_id": well_id,
            "total": len(events),
            "total_npt_hours": round(sum(e.npt_hours for e in events), 2),
            "events": [e.model_dump() for e in events],
        }

    def search_events(
        self,
        hazard_type: Optional[str] = None,
        formation: Optional[str] = None,
        min_severity: Optional[str] = None,
        depth_min: Optional[float] = None,
        depth_max: Optional[float] = None,
    ) -> dict:
        self._require_store()
        severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        min_sev_num = severity_order.get((min_severity or "LOW").upper(), 0)

        events = self.store.all_events
        if hazard_type:
            events = [e for e in events if e.event_type.value == hazard_type.upper()]
        if formation:
            events = [e for e in events if e.formation and formation.lower() in e.formation.lower()]
        if depth_min is not None:
            events = [e for e in events if e.depth_start_md_m >= depth_min]
        if depth_max is not None:
            events = [e for e in events if e.depth_start_md_m <= depth_max]
        if min_severity:
            events = [e for e in events if severity_order.get(e.severity, 0) >= min_sev_num]

        return {
            "total": len(events),
            "total_npt_hours": round(sum(e.npt_hours for e in events), 2),
            "events": [e.model_dump() for e in events[:100]],
        }

    def get_telemetry(self, well_id: str, depth: float, window: int = 300) -> dict:
        self._require_store()
        if well_id != self.store.active_well_id and well_id not in self.store.wells_by_id:
            raise HTTPException(404, f"Well '{well_id}' not found")

        records = self.store.get_telemetry_at(depth, window=window)
        latest = records[-1] if records else None

        return {
            "well_id": well_id,
            "depth_m": depth,
            "records_returned": len(records),
            "latest": latest.model_dump() if latest else None,
            "records": [r.model_dump() for r in records[-50:]],
        }

    def rank_offsets(
        self,
        well_id: str,
        depth: float,
        radius_km: float = 25.0,
        top_n: int = 10,
    ) -> dict:
        self._require_store()
        active_well = self.store.wells_by_id.get(well_id)
        if not active_well:
            raise HTTPException(404, f"Well '{well_id}' not found")

        active_tops = self.store.formation_tops_by_well.get(well_id, [])
        active_fm = formation_at_depth(active_tops, depth)

        rankings = rank_offset_wells(
            active_well=active_well,
            active_depth_m=depth,
            active_formation=active_fm.formation_name if active_fm else None,
            all_wells=self.store.all_wells,
            all_trajectories=self.store.all_trajectories,
            all_formation_tops=self.store.formation_tops_by_well,
            all_events=self.store.events_by_well,
            r_max_km=radius_km,
            top_n=top_n,
        )

        return {
            "active_well_id": well_id,
            "depth_m": depth,
            "formation_at_bit": active_fm.formation_name if active_fm else None,
            "radius_km": radius_km,
            "total_ranked": len(rankings),
            "rankings": [r.model_dump() for r in rankings],
            "dors_formula": "DORS = 0.20·S_spatial + 0.30·S_formation + 0.20·S_depth + 0.15·S_trajectory + 0.15·S_hazard",
        }

    def analyze_well(
        self,
        well_id: str,
        depth: float,
        radius_km: float = 25.0,
        mud_weight_ppg: float = 9.5,
    ) -> dict:
        self._require_store()
        if well_id not in self.store.wells_by_id:
            raise HTTPException(404, f"Well '{well_id}' not found")

        try:
            orchestrator = NWISOrchestrator(self.store)
            result = orchestrator.analyze(
                active_well_id=well_id,
                current_depth_m=depth,
                r_max_km=radius_km,
                mud_weight_ppg=mud_weight_ppg,
            )
            return result.model_dump()
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise HTTPException(500, f"Analysis error: {str(e)}")

    def get_risk_corridors(
        self,
        well_id: str,
        depth: float,
        hazard_type: Optional[str] = None,
    ) -> dict:
        self._require_store()
        active_well = self.store.wells_by_id.get(well_id)
        if not active_well:
            raise HTTPException(404, f"Well '{well_id}' not found")

        active_tops = self.store.formation_tops_by_well.get(well_id, [])
        active_fm = formation_at_depth(active_tops, depth)
        rankings = rank_offset_wells(
            active_well=active_well,
            active_depth_m=depth,
            active_formation=active_fm.formation_name if active_fm else None,
            all_wells=self.store.all_wells,
            all_trajectories=self.store.all_trajectories,
            all_formation_tops=self.store.formation_tops_by_well,
            all_events=self.store.events_by_well,
            r_max_km=25.0,
            top_n=10,
        )

        top_events = self.store.get_events_for_top_wells([r.well_id for r in rankings])
        hazards_to_check = [HazardType(hazard_type)] if hazard_type else list(HazardType)
        all_corridors = []
        for h in hazards_to_check:
            try:
                corridors = identify_risk_corridors(top_events, h, depth)
                all_corridors.extend(corridors)
            except Exception:
                pass

        all_corridors.sort(key=lambda c: c.depth_start_m)

        return {
            "well_id": well_id,
            "depth_m": depth,
            "formation_at_bit": active_fm.formation_name if active_fm else None,
            "total_corridors": len(all_corridors),
            "corridors": [c.model_dump() for c in all_corridors],
        }

    def get_map_wells(self) -> dict:
        self._require_store()
        map_data = []
        for w in self.store.all_wells:
            events = self.store.events_by_well.get(w.well_id, [])
            map_data.append({
                "well_id": w.well_id,
                "well_name": w.well_name,
                "field": w.field,
                "lat": w.surface_lat,
                "lon": w.surface_lon,
                "status": w.status.value,
                "well_type": w.well_type.value,
                "total_depth_md_m": w.total_depth_md_m,
                "total_events": len(events),
                "is_active": w.well_id == self.store.active_well_id,
            })
        return {
            "total": len(map_data),
            "active_well_id": self.store.active_well_id,
            "wells": map_data,
        }


well_controller = WellController()
