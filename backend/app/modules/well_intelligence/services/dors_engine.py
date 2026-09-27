"""
NWIS Engine 01 — Dynamic Offset Relevance Engine (DORS) & Omega (Ω) Ranking.

Implements the official Module 4 multi-criteria offset-well ranking engine:

  Ω(w, z) = w1·S_distance + w2·S_geological + w3·S_trajectory + w4·S_completion

Baseline Specification Weights (Module 4 Sec 30):
  w1 = 0.25  (Distance)
  w2 = 0.40  (Geological Stratigraphy)
  w3 = 0.20  (Wellbore Trajectory)
  w4 = 0.15  (Completion / Well Geometry)

Hazard-Specific Weight Modulations (Module 4 Sec 35 / Competitive Research):
  - Lost Circulation: Prioritizes formation match & mud density history
  - Stuck Pipe: Prioritizes trajectory dogleg severity & BHA geometry
  - Gas Kick: Prioritizes formation overpressure & pore pressure margins

Structural Fault Gating:
  Applies barrier penalty (beta_fault = 0.20) if offset well is across a
  suspected structural fault boundary (POSSIBLE_FAULT_BOUNDARY).
"""

from __future__ import annotations

import math
from typing import List, Optional, Dict, Tuple, Any, Union

from app.core.logging import logger
from app.modules.well_intelligence.models.schemas import (
    Well,
    WellTrajectory,
    FormationTop,
    DrillingEvent,
    DORSComponentScores,
    OmegaComponentScores,
    OffsetWellRanking,
    HazardType,
    StructuralFaultStatus,
)
from app.modules.well_intelligence.services.xi_correlator import (
    check_structural_fault_heuristic,
    formation_top_tvdss,
)

# Baseline Ω weights
OMEGA_DEFAULT_WEIGHTS = {
    "distance": 0.25,
    "geological": 0.40,
    "trajectory": 0.20,
    "completion": 0.15,
}

DORS_W_DISTANCE = OMEGA_DEFAULT_WEIGHTS["distance"]
DORS_W_GEOLOGICAL = OMEGA_DEFAULT_WEIGHTS["geological"]
DORS_W_TRAJECTORY = OMEGA_DEFAULT_WEIGHTS["trajectory"]
DORS_W_COMPLETION = OMEGA_DEFAULT_WEIGHTS["completion"]

# Hazard-specific Ω weights
OMEGA_HAZARD_WEIGHTS = {
    HazardType.MUD_LOSS: {
        "distance": 0.20,
        "geological": 0.45,
        "trajectory": 0.15,
        "completion": 0.20,
    },
    HazardType.STUCK_PIPE: {
        "distance": 0.15,
        "geological": 0.30,
        "trajectory": 0.40,
        "completion": 0.15,
    },
    HazardType.KICK: {
        "distance": 0.20,
        "geological": 0.45,
        "trajectory": 0.15,
        "completion": 0.20,
    },
    HazardType.WELLBORE_INSTABILITY: {
        "distance": 0.20,
        "geological": 0.40,
        "trajectory": 0.25,
        "completion": 0.15,
    },
    HazardType.TORQUE_SPIKE: {
        "distance": 0.15,
        "geological": 0.25,
        "trajectory": 0.45,
        "completion": 0.15,
    },
}

HAZARD_WEIGHT_PROFILES = OMEGA_HAZARD_WEIGHTS


def calculate_omega_score(
    distance_km: float,
    geological_score: float,
    trajectory_score: float,
    completion_score: float,
    max_distance_km: float = 50.0,
    structural_status: Union[str, StructuralFaultStatus] = "SAME_FAULT_BLOCK",
    hazard_type: Optional[HazardType] = None,
) -> Tuple[float, OmegaComponentScores]:
    """
    Direct calculator for Omega score given normalized component scores.
    Uses 0.25/0.40/0.20/0.15 baseline weights or hazard-specific profiles.
    """
    status_str = structural_status.value if hasattr(structural_status, "value") else str(structural_status)
    s_dist = max(0.0, 1.0 - (distance_km / max_distance_km))
    if status_str == "POSSIBLE_FAULT_BOUNDARY":
        s_dist *= 0.20

    weights = OMEGA_HAZARD_WEIGHTS.get(hazard_type, OMEGA_DEFAULT_WEIGHTS)
    total = (
        weights["distance"] * s_dist +
        weights["geological"] * geological_score +
        weights["trajectory"] * trajectory_score +
        weights["completion"] * completion_score
    )
    comp = OmegaComponentScores(
        distance=round(s_dist, 4),
        geological=round(geological_score, 4),
        trajectory=round(trajectory_score, 4),
        completion=round(completion_score, 4),
        total_omega=round(total, 4),
        distance_km=round(distance_km, 3),
        structural_status=status_str,
    )
    return round(total, 4), comp


# Legacy DORS 5-factor weights (for backward compatibility)
DORS_WEIGHTS = {
    "spatial": 0.20,
    "formation": 0.30,
    "depth": 0.20,
    "trajectory": 0.15,
    "hazard": 0.15,
}

SEVERITY_WEIGHTS = {
    "CRITICAL": 1.0,
    "HIGH": 0.7,
    "MEDIUM": 0.4,
    "LOW": 0.2,
}

SIGMA_D = 25.0  # meters depth smoothing bandwidth


# ---------------------------------------------------------------------------
# Geodesic / Spatial Distance
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two surface coordinates (km)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * R * math.asin(math.sqrt(max(0.0, a)))


def score_distance_omega(
    offset_well: Well,
    active_well: Well,
    max_distance_km: float = 50.0,
    structural_status: str = "SAME_FAULT_BLOCK",
) -> Tuple[float, float]:
    """
    S_distance = max(0, 1 - distance / max_dist)
    Applies structural barrier penalty if across a possible fault.
    """
    dist_km = haversine_km(
        active_well.surface_lat, active_well.surface_lon,
        offset_well.surface_lat, offset_well.surface_lon,
    )
    base_score = max(0.0, 1.0 - (dist_km / max_distance_km))

    # Structural fault barrier penalty (Module 4 Sec 40)
    if structural_status == "POSSIBLE_FAULT_BOUNDARY":
        base_score *= 0.20  # Strong discount across fault boundaries

    return round(base_score, 4), round(dist_km, 3)


# ---------------------------------------------------------------------------
# Geological Stratigraphy Scoring
# ---------------------------------------------------------------------------

ASSAM_FORMATION_GROUPS = {
    "UPPER_ASSAM": {"Alluvium", "Dihing", "Tipam Sandstone", "Girujan Clay"},
    "BARAIL": {"Barail Sandstone", "Barail Coal-Shale", "Barail Lower Sand"},
    "EOCENE": {"Kopili", "Sylhet Limestone", "Langpar"},
    "BASEMENT": {"Basement"},
}


def _formation_group(name: str) -> str:
    for group, members in ASSAM_FORMATION_GROUPS.items():
        if name in members:
            return group
    return "UNKNOWN"


def score_geological_omega(
    offset_tops: List[FormationTop],
    active_formation: Optional[str],
    offset_events: List[DrillingEvent],
    active_depth_m: float,
) -> float:
    """
    S_geological = 0.5 * formation_match + 0.5 * npt_cluster_match
    """
    if not active_formation:
        return 0.3

    offset_names = {t.formation_name for t in offset_tops}

    # 1. Formation match flag
    if active_formation in offset_names:
        fm_match = 1.0
    else:
        active_group = _formation_group(active_formation)
        if any(_formation_group(n) == active_group and active_group != "UNKNOWN" for n in offset_names):
            fm_match = 0.6
        else:
            fm_match = 0.1

    # 2. NPT cluster match (events occurring within active formation)
    relevant_events = [e for e in offset_events if e.formation == active_formation]
    if relevant_events:
        npt_match = min(1.0, 0.4 + 0.2 * len(relevant_events))
    else:
        npt_match = 0.5  # Neutral if no historical incidents

    return round(0.5 * fm_match + 0.5 * npt_match, 4)


# ---------------------------------------------------------------------------
# Trajectory Similarity Scoring
# ---------------------------------------------------------------------------

def score_trajectory_omega(
    offset_traj: Optional[WellTrajectory],
    active_traj: Optional[WellTrajectory],
    active_well_type: str,
) -> float:
    """
    S_trajectory: Compares average inclination, azimuth, and trajectory shape.
    """
    if not offset_traj or not offset_traj.stations:
        return 0.5 if active_well_type == "Vertical" else 0.3

    offset_incl = offset_traj.avg_inclination
    active_incl = active_traj.avg_inclination if active_traj else 0.0

    incl_diff = abs(active_incl - offset_incl)
    incl_score = max(0.0, 1.0 - (incl_diff / 45.0))

    type_match = 1.0 if active_well_type == offset_traj.well_type.value else 0.6
    return round(0.7 * incl_score + 0.3 * type_match, 4)


# ---------------------------------------------------------------------------
# Completion / Well Geometry Scoring
# ---------------------------------------------------------------------------

def score_completion_omega(active_well_type: str, offset_well_type: str) -> float:
    """
    S_completion heuristic (Module 4 Sec 34):
      both vertical -> 1.0
      both deviated, similar type -> 0.9
      one vertical / one deviated -> 0.5
    """
    if active_well_type == "Vertical" and offset_well_type == "Vertical":
        return 1.0
    if active_well_type != "Vertical" and offset_well_type != "Vertical":
        return 0.9 if active_well_type == offset_well_type else 0.7
    return 0.5


# ---------------------------------------------------------------------------
# Master Ω Scoring Engine
# ---------------------------------------------------------------------------

def compute_omega(
    active_well: Well,
    active_depth_m: float,
    active_formation: Optional[str],
    active_traj: Optional[WellTrajectory],
    offset_well: Well,
    offset_traj: Optional[WellTrajectory],
    offset_tops: List[FormationTop],
    offset_events: List[DrillingEvent],
    active_top_tvdss: Optional[float] = None,
    hazard_filter: Optional[HazardType] = None,
    max_distance_km: float = 50.0,
) -> OmegaComponentScores:
    """
    Computes 4-component Omega (Ω) relevance score for one offset well.
    """
    # Detect structural fault status
    structural_status = "SAME_FAULT_BLOCK"
    if active_formation and active_top_tvdss is not None:
        matching_top = next((t for t in offset_tops if t.formation_name == active_formation), None)
        if matching_top:
            o_top_z = formation_top_tvdss(matching_top, offset_well)
            dist_km = haversine_km(
                active_well.surface_lat, active_well.surface_lon,
                offset_well.surface_lat, offset_well.surface_lon,
            )
            structural_status = check_structural_fault_heuristic(active_top_tvdss, o_top_z, dist_km)

    s_dist, dist_km = score_distance_omega(offset_well, active_well, max_distance_km, structural_status)
    s_geol = score_geological_omega(offset_tops, active_formation, offset_events, active_depth_m)
    s_traj = score_trajectory_omega(offset_traj, active_traj, active_well.well_type.value)
    s_comp = score_completion_omega(active_well.well_type.value, offset_well.well_type.value)

    weights = OMEGA_HAZARD_WEIGHTS.get(hazard_filter, OMEGA_DEFAULT_WEIGHTS)
    total_omega = (
        weights["distance"] * s_dist +
        weights["geological"] * s_geol +
        weights["trajectory"] * s_traj +
        weights["completion"] * s_comp
    )

    return OmegaComponentScores(
        distance=s_dist,
        geological=s_geol,
        trajectory=s_traj,
        completion=s_comp,
        total_omega=round(total_omega, 4),
        distance_km=dist_km,
        structural_status=structural_status,
    )


# ---------------------------------------------------------------------------
# Legacy DORS Sub-scores (Preserved for compatibility)
# ---------------------------------------------------------------------------

def score_spatial(offset_well: Well, active_well: Well, r_max_km: float = 25.0) -> Tuple[float, float]:
    dist = haversine_km(
        active_well.surface_lat, active_well.surface_lon,
        offset_well.surface_lat, offset_well.surface_lon,
    )
    score = max(0.0, 1.0 - dist / r_max_km)
    return round(score, 4), round(dist, 3)


def score_formation(
    offset_tops: List[FormationTop],
    active_formation: Optional[str],
    active_depth_m: float,
) -> float:
    if not active_formation:
        return 0.3
    offset_names = {t.formation_name for t in offset_tops}
    if active_formation in offset_names:
        for top in offset_tops:
            if top.formation_name == active_formation and top.top_md_m <= active_depth_m <= top.base_md_m:
                return 1.0
        return 0.75
    active_group = _formation_group(active_formation)
    for name in offset_names:
        if _formation_group(name) == active_group and active_group != "UNKNOWN":
            return 0.6
    return 0.1


def score_depth(
    offset_traj: Optional[WellTrajectory],
    active_depth_m: float,
    lookahead_m: float = 100.0,
    buffer_m: float = 50.0,
) -> float:
    if not offset_traj or not offset_traj.stations:
        return 0.0
    d_min = offset_traj.stations[0].md_m
    d_max = offset_traj.stations[-1].md_m
    win_start = active_depth_m - buffer_m
    win_end = active_depth_m + lookahead_m
    window_size = buffer_m + lookahead_m
    overlap = max(0.0, min(d_max, win_end) - max(d_min, win_start))
    return round(min(1.0, overlap / window_size), 4)


def score_trajectory(
    offset_traj: Optional[WellTrajectory],
    active_well_type: str,
    active_avg_incl: float,
) -> float:
    if not offset_traj or not offset_traj.stations:
        return 0.3
    offset_type = offset_traj.well_type.value
    offset_avg_incl = offset_traj.avg_inclination
    type_penalty = 0.0 if active_well_type == offset_type else 0.5
    incl_penalty = abs(active_avg_incl - offset_avg_incl) / 90.0 * 0.5
    return round(max(0.0, 1.0 - type_penalty - incl_penalty), 4)


def score_hazard(
    offset_events: List[DrillingEvent],
    active_depth_m: float,
    hazard_filter: Optional[HazardType] = None,
) -> float:
    score = 0.0
    for event in offset_events:
        if hazard_filter and event.event_type != hazard_filter:
            continue
        sev = SEVERITY_WEIGHTS.get(event.severity, 0.4)
        d_e = event.depth_start_md_m
        gaussian = math.exp(-((d_e - active_depth_m) ** 2) / (2 * SIGMA_D ** 2))
        score += sev * gaussian
    return round(min(1.0, score), 4)


def compute_dors(
    active_well: Well,
    active_depth_m: float,
    active_formation: Optional[str],
    active_well_type: str,
    active_avg_incl: float,
    offset_well: Well,
    offset_traj: Optional[WellTrajectory],
    offset_tops: List[FormationTop],
    offset_events: List[DrillingEvent],
    r_max_km: float = 25.0,
    weights: Optional[dict] = None,
) -> DORSComponentScores:
    w = weights or DORS_WEIGHTS
    s_spatial, dist_km = score_spatial(offset_well, active_well, r_max_km)
    s_formation = score_formation(offset_tops, active_formation, active_depth_m)
    s_depth = score_depth(offset_traj, active_depth_m)
    s_trajectory = score_trajectory(offset_traj, active_well_type, active_avg_incl)
    s_hazard = score_hazard(offset_events, active_depth_m)

    total = (
        w["spatial"] * s_spatial +
        w["formation"] * s_formation +
        w["depth"] * s_depth +
        w["trajectory"] * s_trajectory +
        w["hazard"] * s_hazard
    )

    return DORSComponentScores(
        spatial=s_spatial,
        formation=s_formation,
        depth=s_depth,
        trajectory=s_trajectory,
        hazard=s_hazard,
        total=round(total, 4),
        distance_km=dist_km,
    )


# ---------------------------------------------------------------------------
# Master Rank All Offset Wells
# ---------------------------------------------------------------------------

def rank_offset_wells(
    active_well: Well,
    active_depth_m: float,
    active_formation: Optional[str],
    all_wells: List[Well],
    all_trajectories: Dict[str, WellTrajectory],
    all_formation_tops: Dict[str, List[FormationTop]],
    all_events: Dict[str, List[DrillingEvent]],
    r_max_km: float = 50.0,
    hazard_filter: Optional[HazardType] = None,
    active_top_tvdss: Optional[float] = None,
    top_n: int = 10,
) -> List[OffsetWellRanking]:
    """
    Ranks all candidate offset wells by Omega (and DORS) for the active well depth.
    Dynamic re-ranking occurs whenever depth or formation changes.
    """
    active_traj = all_trajectories.get(active_well.well_id)
    active_avg_incl = active_traj.avg_inclination if active_traj else 0.0

    rankings: List[OffsetWellRanking] = []
    for offset in all_wells:
        if offset.well_id == active_well.well_id:
            continue

        offset_traj = all_trajectories.get(offset.well_id)
        offset_tops = all_formation_tops.get(offset.well_id, [])
        offset_events = all_events.get(offset.well_id, [])

        # Legacy DORS score
        dors_scores = compute_dors(
            active_well=active_well,
            active_depth_m=active_depth_m,
            active_formation=active_formation,
            active_well_type=active_well.well_type.value,
            active_avg_incl=active_avg_incl,
            offset_well=offset,
            offset_traj=offset_traj,
            offset_tops=offset_tops,
            offset_events=offset_events,
            r_max_km=r_max_km,
        )

        # Module 4 Master Omega score
        omega_scores = compute_omega(
            active_well=active_well,
            active_depth_m=active_depth_m,
            active_formation=active_formation,
            active_traj=active_traj,
            offset_well=offset,
            offset_traj=offset_traj,
            offset_tops=offset_tops,
            offset_events=offset_events,
            active_top_tvdss=active_top_tvdss,
            hazard_filter=hazard_filter,
            max_distance_km=r_max_km,
        )

        events_in_window = sum(
            1 for e in offset_events
            if abs(e.depth_start_md_m - active_depth_m) <= 150
        )

        rankings.append(
            OffsetWellRanking(
                rank=0,
                well_id=offset.well_id,
                well_name=offset.well_name,
                field=offset.field,
                well_type=offset.well_type.value,
                dors_score=dors_scores.total,
                component_scores=dors_scores,
                omega_score=omega_scores.total_omega,
                omega_components=omega_scores,
                structural_status=omega_scores.structural_status,
                formation_match=active_formation or "N/A",
                events_in_lookahead=events_in_window,
                distance_km=omega_scores.distance_km,
            )
        )

    # Sort primarily by Omega score descending (or DORS if identical)
    rankings.sort(key=lambda r: (r.omega_score or r.dors_score), reverse=True)

    for i, r in enumerate(rankings[:top_n]):
        r.rank = i + 1

    return rankings[:top_n]
