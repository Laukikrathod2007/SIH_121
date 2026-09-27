"""
NWIS Module 02 â€” Master Analysis Orchestrator
Single entry point for the entire backend intelligence pipeline.

Call:
    result = NWISOrchestrator(store).analyze(active_well_id, current_depth_m)

Pipeline:
    1. DORS Engine â€” rank all offset wells
    2. Stratigraphic Correlator â€” align at equivalent geological horizon
    3. Risk Corridor Engine â€” cluster historical hazards into depth windows
    4. 4-Pillar Confidence â€” evidence + sensor + quality + audit
    5. Assemble NWISAnalysisResponse
"""

from __future__ import annotations
from typing import Optional, List
from app.core.logging import logger

from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.modules.well_intelligence.models.schemas import (
    NWISAnalysisResponse, HazardType, RiskLevel,
    DrillingEvent, TelemetryRecord
)
from app.modules.well_intelligence.services.dors_engine import rank_offset_wells
from app.modules.well_intelligence.services.stratigraphic_correlator import formation_at_depth
from app.modules.well_intelligence.services.risk_corridor_engine import (
    assess_hazard,
    identify_risk_corridors,
    compute_ahead_of_bit_corridor,
)

import datetime

# All 5 hazard families from PS 26121
ALL_HAZARDS = [
    HazardType.MUD_LOSS,
    HazardType.STUCK_PIPE,
    HazardType.KICK,
    HazardType.WELLBORE_INSTABILITY,
    HazardType.TORQUE_SPIKE,
]


class NWISOrchestrator:
    def __init__(self, store: NWISDataStore):
        self.store = store

    def analyze(
        self,
        active_well_id: str,
        current_depth_m: float,
        r_max_km: float = 25.0,
        top_n: int = 10,
        mud_weight_ppg: float = 9.5,
    ) -> NWISAnalysisResponse:
        """
        Full NWIS intelligence pipeline for the active drill bit position.
        Returns the complete NWISAnalysisResponse for the API layer.
        """
        store = self.store

        # ---------------------------------------------------------------
        # 0. Get active well context
        # ---------------------------------------------------------------
        active_well = store.wells_by_id.get(active_well_id)
        if active_well is None:
            raise ValueError(f"Active well '{active_well_id}' not found in data store")

        active_traj = store.all_trajectories.get(active_well_id)
        active_tops = store.formation_tops_by_well.get(active_well_id, [])

        # Formation at current bit depth
        active_fm_obj = formation_at_depth(active_tops, current_depth_m)
        active_fm_name = active_fm_obj.formation_name if active_fm_obj else None
        pore_pp = active_fm_obj.pore_pressure_gradient_ppg if active_fm_obj else 9.2

        logger.info(
            f"NWIS Analysis | Well: {active_well_id} | "
            f"Depth: {current_depth_m:.0f}m | Formation: {active_fm_name}"
        )

        # ---------------------------------------------------------------
        # 1. DORS â€” rank offset wells
        # ---------------------------------------------------------------
        rankings = rank_offset_wells(
            active_well=active_well,
            active_depth_m=current_depth_m,
            active_formation=active_fm_name,
            all_wells=store.all_wells,
            all_trajectories=store.all_trajectories,
            all_formation_tops=store.formation_tops_by_well,
            all_events=store.events_by_well,
            r_max_km=r_max_km,
            top_n=top_n,
        )

        top_well_ids = [r.well_id for r in rankings]
        top_events = store.get_events_for_top_wells(top_well_ids)

        # ---------------------------------------------------------------
        # 2. Live telemetry slice for sensor anomaly scoring
        # ---------------------------------------------------------------
        recent_telemetry = store.get_telemetry_at(current_depth_m, window=180)

        # ---------------------------------------------------------------
        # 3. Hazard Assessments for all 5 families
        # ---------------------------------------------------------------
        hazard_assessments = []
        all_corridors = []

        for hazard_type in ALL_HAZARDS:
            assessment = assess_hazard(
                hazard_type=hazard_type,
                current_depth_m=current_depth_m,
                formation=active_fm_name,
                top_offset_events=top_events,
                top_offset_rankings=rankings,
                recent_telemetry=recent_telemetry,
                mud_weight_ppg=mud_weight_ppg,
                pore_pressure_ppg=pore_pp,
            )
            hazard_assessments.append(assessment)
            if assessment.active_corridor:
                all_corridors.append(assessment.active_corridor)

        # Deduplicate corridors by corridor_id
        seen_ids = set()
        unique_corridors = []
        for c in all_corridors:
            if c.corridor_id not in seen_ids:
                seen_ids.add(c.corridor_id)
                unique_corridors.append(c)

        # ---------------------------------------------------------------
        # 4. Ahead-of-Bit Projection Corridor (0-20m, 20-50m, 50-200m)
        # ---------------------------------------------------------------
        top_offset_well_objs = [
            store.wells_by_id[r.well_id]
            for r in rankings
            if r.well_id in store.wells_by_id
        ]
        ahead_corridor = compute_ahead_of_bit_corridor(
            active_well=active_well,
            active_traj=active_traj,
            active_tops=active_tops,
            top_offset_wells=top_offset_well_objs,
            offset_trajectories=store.all_trajectories,
            offset_tops_map=store.formation_tops_by_well,
            offset_events_map=store.events_by_well,
            current_md_m=current_depth_m,
            max_lookahead_m=200.0,
            step_m=10.0,
            window_m=50.0,
        )

        # ---------------------------------------------------------------
        # 5. Overall risk level (worst hazard family)
        # ---------------------------------------------------------------
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MODERATE: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        overall_risk = max(hazard_assessments, key=lambda h: risk_order[h.risk_level]).risk_level

        # ---------------------------------------------------------------
        # 6. Alert message (for lead-time corridor)
        # ---------------------------------------------------------------
        alert_msg = None
        critical_assessment = next(
            (h for h in hazard_assessments
             if h.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
             and h.lead_time_meters is not None and h.lead_time_meters <= 50),
            None,
        )
        if critical_assessment:
            top_well = rankings[0].well_name if rankings else "analog well"
            alert_msg = (
                f"{critical_assessment.lead_time_meters:.0f}m to historical "
                f"{critical_assessment.hazard_type.value.replace('_', ' ')} zone "
                f"({top_well} analog) â€” {critical_assessment.recommended_action[:80]}"
            )

        return NWISAnalysisResponse(
            active_well_id=active_well_id,
            current_depth_m=current_depth_m,
            analysis_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            offset_rankings=rankings,
            hazard_assessments=hazard_assessments,
            active_risk_corridors=unique_corridors,
            ahead_of_bit_corridor=ahead_corridor,
            formation_at_bit=active_fm_name,
            overall_risk_level=overall_risk,
            alert_message=alert_msg,
        )

