"""
NWIS Engine 03 â€” Historical Risk Corridor Engine + 4-Pillar Confidence
Implements lookahead risk corridor clustering and the hybrid risk aggregation:

  R_H(t) = Î±Â·P_history + Î²Â·A_sensor + Î³Â·M_ML
  where Î±=0.45, Î²=0.35, Î³=0.20

Also computes the Decoupled 4-Pillar Confidence Matrix.
"""

from __future__ import annotations
import math
from collections import defaultdict
from typing import List, Optional, Dict

from app.modules.well_intelligence.models.schemas import (
    DrillingEvent, HazardType, RiskLevel, RiskCorridor,
    HazardRiskAssessment, FourPillarConfidence, EvidenceStrength,
    TelemetryRecord, OffsetWellRanking,
)

# ---------------------------------------------------------------------------
# Risk Aggregation Weights
# ---------------------------------------------------------------------------

ALPHA = 0.45  # Historical frequency weight
BETA  = 0.35  # Sensor anomaly weight
GAMMA = 0.20  # ML model weight (deterministic fallback used here)

# Corridor clustering buffer (Â±Î´ metres around event cluster)
DELTA_BUFFER = 30.0

# Lookahead threshold for early warning
EARLY_WARNING_M = 50.0  # warn when bit is within 50m of corridor

# Evidence strength thresholds
EVIDENCE_HIGH     = 5   # N >= 5 wells
EVIDENCE_MODERATE = 3   # N >= 3
EVIDENCE_LOW      = 1   # N >= 1


# ---------------------------------------------------------------------------
# Risk Level Thresholds
# ---------------------------------------------------------------------------

def risk_level_from_score(score: float) -> RiskLevel:
    if score < 0.25:
        return RiskLevel.LOW
    elif score < 0.50:
        return RiskLevel.MODERATE
    elif score < 0.75:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def severity_to_numeric(s: str) -> float:
    return {"CRITICAL": 1.0, "HIGH": 0.7, "MEDIUM": 0.4, "LOW": 0.2}.get(s, 0.3)


# ---------------------------------------------------------------------------
# Corridor Clustering
# ---------------------------------------------------------------------------

def identify_risk_corridors(
    events: List[DrillingEvent],
    hazard_type: HazardType,
    current_depth_m: float,
    cluster_window_m: float = 100.0,
    min_events: int = 2,
) -> List[RiskCorridor]:
    """
    Cluster historical events of a given hazard type into depth corridors.
    C_k = [min(d_start) - Î´, max(d_end) + Î´]

    Only returns corridors ahead of or containing the current drill bit.
    """
    matching = [e for e in events if e.event_type == hazard_type]
    if not matching:
        return []

    # Sort by depth
    matching.sort(key=lambda e: e.depth_start_md_m)

    corridors: List[RiskCorridor] = []
    cluster: List[DrillingEvent] = []
    cluster_start = None

    for event in matching:
        if not cluster:
            cluster = [event]
            cluster_start = event.depth_start_md_m
        elif event.depth_start_md_m - cluster_start <= cluster_window_m:
            cluster.append(event)
        else:
            # Flush current cluster
            if len(cluster) >= min_events or (len(cluster) == 1 and cluster[0].severity in ["CRITICAL", "HIGH"]):
                corridors.append(_build_corridor(cluster, hazard_type, current_depth_m))
            cluster = [event]
            cluster_start = event.depth_start_md_m

    if cluster and (len(cluster) >= min_events or (len(cluster) == 1 and cluster[0].severity in ["CRITICAL", "HIGH"])):
        corridors.append(_build_corridor(cluster, hazard_type, current_depth_m))

    # Filter: only include corridors ahead of or containing current depth
    relevant = [c for c in corridors if c.depth_end_m >= current_depth_m - 20]
    relevant.sort(key=lambda c: c.depth_start_m)
    return relevant


def _build_corridor(
    events: List[DrillingEvent],
    hazard_type: HazardType,
    current_depth_m: float,
) -> RiskCorridor:
    d_starts = [e.depth_start_md_m for e in events]
    d_ends = [e.depth_end_md_m or e.depth_start_md_m + 30 for e in events]

    start = min(d_starts) - DELTA_BUFFER
    end = max(d_ends) + DELTA_BUFFER

    avg_npt = sum(e.npt_hours for e in events) / len(events)
    max_sev = max(events, key=lambda e: severity_to_numeric(e.severity)).severity
    freq = min(1.0, len(events) / 10.0)  # normalize 10+ events = 1.0

    lead_dist = start - current_depth_m

    # Risk level: CRITICAL if active bit inside corridor
    if current_depth_m >= start:
        risk_level = RiskLevel.CRITICAL if max_sev == "CRITICAL" else RiskLevel.HIGH
    elif lead_dist <= EARLY_WARNING_M:
        risk_level = RiskLevel.HIGH if max_sev in ["CRITICAL", "HIGH"] else RiskLevel.MODERATE
    else:
        risk_level = risk_level_from_score(freq * severity_to_numeric(max_sev))

    # Recommended action
    actions = {
        HazardType.MUD_LOSS: "Pre-mix LCM pill (25â€“30 bbl); reduce ECD; have cementing crew standby",
        HazardType.STUCK_PIPE: "Condition mud; short trips; maintain minimum WOB; spot freeing agent",
        HazardType.KICK: "Weight up kill mud; verify BOP function; reduce ROP through transition zone",
        HazardType.WELLBORE_INSTABILITY: "Raise KCl inhibitor; increase mud weight; ream frequently",
        HazardType.TORQUE_SPIKE: "Reduce WOB; reciprocate string; check stabilizer size",
        HazardType.CEMENTING_FAILURE: "Review cement design; verify centralizer placement; re-run caliper",
    }

    formation = max(events, key=lambda e: severity_to_numeric(e.severity)).formation

    return RiskCorridor(
        hazard_type=hazard_type,
        depth_start_m=round(start, 1),
        depth_end_m=round(end, 1),
        contributing_wells=list({e.well_id for e in events}),
        contributing_events=[e.event_id for e in events],
        event_count=len(events),
        avg_npt_hours=round(avg_npt, 2),
        max_severity=max_sev,
        historical_frequency=round(freq, 3),
        lead_distance_m=round(lead_dist, 1) if lead_dist > 0 else 0.0,
        risk_level=risk_level,
        recommended_action=actions.get(hazard_type, "Monitor closely"),
        formation=formation,
    )


# ---------------------------------------------------------------------------
# Sensor Anomaly Score (A_sensor)
# ---------------------------------------------------------------------------

def compute_sensor_anomaly(
    hazard_type: HazardType,
    recent_telemetry: List[TelemetryRecord],
    window: int = 120,
) -> float:
    """
    Compute real-time sensor anomaly score for a specific hazard type.
    Uses Z-score deviation on the most relevant sensor signals.

    Returns A_sensor âˆˆ [0, 1]
    """
    if len(recent_telemetry) < 10:
        return 0.0

    records = recent_telemetry[-window:]

    def z_score_latest(values: List[float]) -> float:
        if len(values) < 5:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0.001
        z = abs(values[-1] - mean) / std
        return min(1.0, z / 4.0)  # normalize: Z=4 â†’ 1.0

    if hazard_type == HazardType.MUD_LOSS:
        # Flow discrepancy: flow_in - flow_out suddenly spikes
        discrepancies = [abs(r.flow_in_lpm - r.flow_out_lpm) for r in records]
        pit_vols = [r.pit_volume_bbl for r in records]
        flow_z = z_score_latest(discrepancies)
        pit_z = z_score_latest(pit_vols)
        return round(max(flow_z, pit_z), 4)

    elif hazard_type == HazardType.STUCK_PIPE:
        torques = [r.torque_kn_m for r in records]
        spps = [r.standpipe_pressure_psi for r in records]
        return round(max(z_score_latest(torques), z_score_latest(spps) * 0.7), 4)

    elif hazard_type == HazardType.KICK:
        flows_out = [r.flow_out_lpm for r in records]
        pits = [r.pit_volume_bbl for r in records]
        # Kick: flow_out INCREASES, pit volume INCREASES
        flow_delta = [flows_out[i] - flows_out[i-1] for i in range(1, len(flows_out))]
        pit_delta = [pits[i] - pits[i-1] for i in range(1, len(pits))]
        pos_flow = max(0, sum(d for d in flow_delta if d > 0) / (len(flow_delta) + 1))
        pos_pit = max(0, sum(d for d in pit_delta if d > 0) / (len(pit_delta) + 1))
        return round(min(1.0, (pos_flow / 50.0 + pos_pit / 2.0) / 2.0), 4)

    elif hazard_type == HazardType.WELLBORE_INSTABILITY:
        torques = [r.torque_kn_m for r in records]
        return round(z_score_latest(torques) * 0.7, 4)

    elif hazard_type == HazardType.TORQUE_SPIKE:
        torques = [r.torque_kn_m for r in records]
        return round(z_score_latest(torques), 4)

    return 0.0


# ---------------------------------------------------------------------------
# Deterministic ML Score (physics-based fallback)
# ---------------------------------------------------------------------------

def compute_ml_score(
    hazard_type: HazardType,
    current_depth_m: float,
    formation: Optional[str],
    mud_weight_ppg: float = 9.5,
    pore_pressure_ppg: float = 9.2,
) -> float:
    """
    Deterministic ML proxy score based on physics relationships.
    Replaces a true trained model for demonstration without training data.
    M_ML âˆˆ [0, 1]
    """
    score = 0.0

    # Overbalance window: if mud weight is close to pore pressure â†’ higher risk
    overbalance = mud_weight_ppg - pore_pressure_ppg
    if overbalance < 0.3:
        score += 0.5
    elif overbalance < 0.7:
        score += 0.25

    # Formation-specific risk
    high_risk_formations = {
        HazardType.MUD_LOSS: {"Tipam Sandstone", "Sylhet Limestone", "Kopili"},
        HazardType.STUCK_PIPE: {"Girujan Clay", "Barail Coal-Shale"},
        HazardType.KICK: {"Barail Sandstone", "Sylhet Limestone"},
        HazardType.WELLBORE_INSTABILITY: {"Girujan Clay", "Barail Coal-Shale"},
    }
    if formation and hazard_type in high_risk_formations:
        if formation in high_risk_formations[hazard_type]:
            score += 0.35

    # Depth-based trend (deeper = higher risk in Assam basin)
    if current_depth_m > 2500:
        score += 0.15
    elif current_depth_m > 2000:
        score += 0.08

    return round(min(1.0, score), 4)


# ---------------------------------------------------------------------------
# 4-Pillar Confidence Evaluator
# ---------------------------------------------------------------------------

def compute_confidence(
    n_analog_wells: int,
    sensor_anomaly: float,
    data_quality: float,
    has_source_docs: bool,
) -> FourPillarConfidence:
    """
    Compute the 4-pillar decoupled confidence matrix:
    1. Evidence Strength (N)
    2. Sensor Anomaly Score (Z-score)
    3. Data Quality Index (completeness %)
    4. Audit Status (document-grounded)
    """
    if n_analog_wells >= EVIDENCE_HIGH:
        ev_strength = EvidenceStrength.HIGH
    elif n_analog_wells >= EVIDENCE_MODERATE:
        ev_strength = EvidenceStrength.MODERATE
    elif n_analog_wells >= EVIDENCE_LOW:
        ev_strength = EvidenceStrength.LOW
    else:
        ev_strength = EvidenceStrength.INSUFFICIENT

    audit = "GROUNDED" if has_source_docs else "PARTIAL"

    # Weighted overall confidence
    ev_score = {
        EvidenceStrength.HIGH: 1.0,
        EvidenceStrength.MODERATE: 0.70,
        EvidenceStrength.LOW: 0.40,
        EvidenceStrength.INSUFFICIENT: 0.05,
    }[ev_strength]

    overall = round(
        0.40 * ev_score +
        0.25 * sensor_anomaly +
        0.20 * data_quality +
        0.15 * (1.0 if has_source_docs else 0.4),
        4
    )

    return FourPillarConfidence(
        evidence_strength=ev_strength,
        evidence_count=n_analog_wells,
        sensor_anomaly_score=sensor_anomaly,
        data_quality_index=data_quality,
        audit_status=audit,
        overall_confidence=overall,
    )


# ---------------------------------------------------------------------------
# Full Hazard Risk Assessment for One Hazard Family
# ---------------------------------------------------------------------------

def assess_hazard(
    hazard_type: HazardType,
    current_depth_m: float,
    formation: Optional[str],
    top_offset_events: List[DrillingEvent],
    top_offset_rankings: List[OffsetWellRanking],
    recent_telemetry: List[TelemetryRecord],
    mud_weight_ppg: float = 9.5,
    pore_pressure_ppg: float = 9.2,
) -> HazardRiskAssessment:
    """
    Full R_H(t) = Î±Â·P_history + Î²Â·A_sensor + Î³Â·M_ML for one hazard family.
    """
    # Identify corridors for this hazard
    corridors = identify_risk_corridors(
        top_offset_events, hazard_type, current_depth_m
    )

    # Closest active corridor
    active_corridor = corridors[0] if corridors else None

    # P_history: fraction of top-N offset wells that had this hazard in lookahead
    n_top = len(top_offset_rankings)
    if n_top == 0:
        p_history = 0.0
    else:
        event_depths = {e.depth_start_md_m for e in top_offset_events if e.event_type == hazard_type}
        hazard_wells_in_window = sum(
            1 for r in top_offset_rankings
            if any(abs(d - current_depth_m) <= 150 for d in
                   [e.depth_start_md_m for e in top_offset_events
                    if e.event_type == hazard_type and e.well_id == r.well_id])
        )
        p_history = min(1.0, hazard_wells_in_window / max(n_top, 1))

        # Boost if active corridor exists and is within EARLY_WARNING_M
        if active_corridor:
            if active_corridor.depth_start_m <= current_depth_m <= active_corridor.depth_end_m:
                p_history = max(p_history, 0.80)
            elif (active_corridor.lead_distance_m or 999) <= EARLY_WARNING_M:
                p_history = max(p_history, 0.65)

    # A_sensor
    a_sensor = compute_sensor_anomaly(hazard_type, recent_telemetry)

    # M_ML
    m_ml = compute_ml_score(hazard_type, current_depth_m, formation, mud_weight_ppg, pore_pressure_ppg)

    # Composite score
    composite = ALPHA * p_history + BETA * a_sensor + GAMMA * m_ml
    composite = round(composite, 4)

    risk_level = risk_level_from_score(composite)

    # 4-Pillar confidence
    n_analog = len({e.well_id for e in top_offset_events if e.event_type == hazard_type})
    has_docs = any(e.source_document for e in top_offset_events if e.event_type == hazard_type)
    data_quality = min(1.0, n_analog / max(n_top, 1)) if n_top > 0 else 0.3
    confidence = compute_confidence(n_analog, a_sensor, data_quality, has_docs)

    # Lead time
    lead_time = active_corridor.lead_distance_m if active_corridor else None

    # Recommended action
    recommended_actions = {
        HazardType.MUD_LOSS: "Pre-mix 25 bbl medium-nut-plug LCM pill; prepare lost circulation contingency; monitor pit volume continuously",
        HazardType.STUCK_PIPE: "Condition mud prior to entering shale; short trip every 300m; maintain constant rotation",
        HazardType.KICK: "Verify kill mud on standby; slow ROP through high-PP zones; monitor flow and pit volume",
        HazardType.WELLBORE_INSTABILITY: "Increase KCl inhibitor concentration; raise MW to 11.0 ppg; limit drilling breaks",
        HazardType.TORQUE_SPIKE: "Reduce WOB by 30%; check top-drive parameters; prepare for string reciprocation",
        HazardType.CEMENTING_FAILURE: "Review centralizer spacing; ensure caliper data; use foam cement for narrow annuli",
    }

    evidence_event_ids = [e.event_id for e in top_offset_events if e.event_type == hazard_type][:10]

    return HazardRiskAssessment(
        hazard_type=hazard_type,
        risk_level=risk_level,
        composite_score=composite,
        p_history=p_history,
        a_sensor=a_sensor,
        m_ml=m_ml,
        confidence=confidence,
        active_corridor=active_corridor,
        lead_time_meters=lead_time,
        recommended_action=recommended_actions.get(hazard_type, "Monitor closely"),
        evidence_events=evidence_event_ids,
    )

