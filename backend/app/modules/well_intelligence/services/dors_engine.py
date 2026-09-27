"""
NWIS Engine 01 â€” Dynamic Offset Relevance Engine (DORS)
Implements the 5-factor mathematical scoring formula:

  DORS(w, d_t) = 0.20Â·S_spatial + 0.30Â·S_formation + 0.20Â·S_depth
               + 0.15Â·S_trajectory + 0.15Â·S_hazard

From: logger/02_MATHEMATICAL_AND_ALGORITHMIC_FORMULATIONS.md
"""

from __future__ import annotations
import math
from typing import List, Optional
from app.core.logging import logger

from app.modules.well_intelligence.models.schemas import (
    Well, WellTrajectory, FormationTop, DrillingEvent,
    DORSComponentScores, OffsetWellRanking, HazardType
)

# Default DORS weights (sum = 1.0)
WEIGHTS = {
    "spatial":    0.20,
    "formation":  0.30,
    "depth":      0.20,
    "trajectory": 0.15,
    "hazard":     0.15,
}

# Severity weights for hazard density scoring
SEVERITY_WEIGHTS = {
    "CRITICAL": 1.0,
    "HIGH":     0.7,
    "MEDIUM":   0.4,
    "LOW":      0.2,
}

SIGMA_D = 25.0   # depth smoothing bandwidth (meters)


# ---------------------------------------------------------------------------
# Haversine Distance
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two surface coordinates (km)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
    return 2 * R * math.asin(math.sqrt(max(0.0, a)))


# ---------------------------------------------------------------------------
# Sub-score: S_spatial
# ---------------------------------------------------------------------------

def score_spatial(offset_well: Well, active_well: Well, r_max_km: float = 25.0) -> tuple[float, float]:
    """
    S_spatial = max(0, 1 - distance / R_max)
    Returns (score, distance_km)
    """
    dist = haversine_km(
        active_well.surface_lat, active_well.surface_lon,
        offset_well.surface_lat, offset_well.surface_lon,
    )
    score = max(0.0, 1.0 - dist / r_max_km)
    return round(score, 4), round(dist, 3)


# ---------------------------------------------------------------------------
# Sub-score: S_formation
# ---------------------------------------------------------------------------

ASSAM_FORMATION_GROUPS = {
    "UPPER_ASSAM": {"Alluvium", "Dihing", "Tipam Sandstone", "Girujan Clay"},
    "BARAIL":      {"Barail Sandstone", "Barail Coal-Shale"},
    "EOCENE":      {"Kopili", "Sylhet Limestone", "Langpar"},
    "BASEMENT":    {"Basement"},
}

def _formation_group(name: str) -> str:
    for group, members in ASSAM_FORMATION_GROUPS.items():
        if name in members:
            return group
    return "UNKNOWN"


def score_formation(
    offset_tops: List[FormationTop],
    active_formation: Optional[str],
    active_depth_m: float,
) -> float:
    """
    S_formation = 1.0 if same formation penetrated at same depth
                  0.6 if adjacent formation in same stratigraphic group
                  0.1 if different / unmapped
    """
    if not active_formation:
        return 0.3  # no formation info â€” partial credit

    offset_names = {t.formation_name for t in offset_tops}

    if active_formation in offset_names:
        # Check if it's actually penetrated at corresponding depth
        for top in offset_tops:
            if (top.formation_name == active_formation and
                    top.top_md_m <= active_depth_m <= top.base_md_m):
                return 1.0
        return 0.75  # Same formation but not same depth window

    # Check same group (adjacent formations)
    active_group = _formation_group(active_formation)
    for name in offset_names:
        if _formation_group(name) == active_group and active_group != "UNKNOWN":
            return 0.6

    return 0.1


# ---------------------------------------------------------------------------
# Sub-score: S_depth
# ---------------------------------------------------------------------------

def score_depth(
    offset_traj: WellTrajectory,
    active_depth_m: float,
    lookahead_m: float = 100.0,
    buffer_m: float = 50.0,
) -> float:
    """
    Overlap between offset well's drilled interval and the active lookahead window.
    Lookahead window: [d_t - 50m, d_t + 100m] (150m total window)
    """
    if not offset_traj.stations:
        return 0.0

    d_min = offset_traj.stations[0].md_m
    d_max = offset_traj.stations[-1].md_m

    win_start = active_depth_m - buffer_m
    win_end = active_depth_m + lookahead_m
    window_size = buffer_m + lookahead_m  # 150m

    overlap_start = max(d_min, win_start)
    overlap_end = min(d_max, win_end)
    overlap = max(0.0, overlap_end - overlap_start)

    return round(min(1.0, overlap / window_size), 4)


# ---------------------------------------------------------------------------
# Sub-score: S_trajectory
# ---------------------------------------------------------------------------

TRAJECTORY_TYPE_ORDER = {"Vertical": 0, "J-Type": 1, "S-Type": 2, "Horizontal": 3}


def score_trajectory(
    offset_traj: WellTrajectory,
    active_well_type: str,
    active_avg_incl: float,
) -> float:
    """
    S_trajectory = 1.0 - |Î¸_active - Î¸_offset| / 90Â° Ã— 0.5 - 0.5 Ã— I(type mismatch)
    """
    offset_type = offset_traj.well_type.value
    offset_avg_incl = offset_traj.avg_inclination

    type_penalty = 0.0 if active_well_type == offset_type else 0.5
    incl_penalty = abs(active_avg_incl - offset_avg_incl) / 90.0 * 0.5

    score = max(0.0, 1.0 - type_penalty - incl_penalty)
    return round(score, 4)


# ---------------------------------------------------------------------------
# Sub-score: S_hazard
# ---------------------------------------------------------------------------

def score_hazard(
    offset_events: List[DrillingEvent],
    active_depth_m: float,
    hazard_filter: Optional[HazardType] = None,
) -> float:
    """
    S_hazard = min(1.0, Î£ Severity(e) Ã— exp(-(d_e - d_t)Â² / 2ÏƒÂ²))
    Ïƒ = 25m depth smoothing bandwidth
    """
    score = 0.0
    for event in offset_events:
        if hazard_filter and event.event_type != hazard_filter:
            continue
        sev = SEVERITY_WEIGHTS.get(event.severity, 0.4)
        d_e = event.depth_start_md_m
        gaussian = math.exp(-((d_e - active_depth_m) ** 2) / (2 * SIGMA_D ** 2))
        score += sev * gaussian

    return round(min(1.0, score), 4)


# ---------------------------------------------------------------------------
# Main DORS Scoring Function
# ---------------------------------------------------------------------------

def compute_dors(
    active_well: Well,
    active_depth_m: float,
    active_formation: Optional[str],
    active_well_type: str,
    active_avg_incl: float,
    offset_well: Well,
    offset_traj: WellTrajectory,
    offset_tops: List[FormationTop],
    offset_events: List[DrillingEvent],
    r_max_km: float = 25.0,
    weights: Optional[dict] = None,
) -> DORSComponentScores:
    """
    Compute the 5-factor Dynamic Offset Relevance Score for one candidate well.
    Returns DORSComponentScores with all sub-scores and total.
    """
    w = weights or WEIGHTS

    s_spatial, dist_km = score_spatial(offset_well, active_well, r_max_km)
    s_formation = score_formation(offset_tops, active_formation, active_depth_m)
    s_depth = score_depth(offset_traj, active_depth_m)
    s_trajectory = score_trajectory(offset_traj, active_well_type, active_avg_incl)
    s_hazard = score_hazard(offset_events, active_depth_m)

    total = (
        w["spatial"]    * s_spatial    +
        w["formation"]  * s_formation  +
        w["depth"]      * s_depth      +
        w["trajectory"] * s_trajectory +
        w["hazard"]     * s_hazard
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
# Rank All Offset Wells
# ---------------------------------------------------------------------------

def rank_offset_wells(
    active_well: Well,
    active_depth_m: float,
    active_formation: Optional[str],
    all_wells: List[Well],
    all_trajectories: dict[str, WellTrajectory],   # well_id â†’ traj
    all_formation_tops: dict[str, List[FormationTop]],  # well_id â†’ tops
    all_events: dict[str, List[DrillingEvent]],      # well_id â†’ events
    r_max_km: float = 25.0,
    top_n: int = 10,
) -> List[OffsetWellRanking]:
    """
    Rank all candidate offset wells by DORS score for the current active bit depth.
    Returns top_n ranked wells.
    """
    active_traj = all_trajectories.get(active_well.well_id)
    active_avg_incl = active_traj.avg_inclination if active_traj else 0.0

    rankings = []
    for offset in all_wells:
        if offset.well_id == active_well.well_id:
            continue  # skip self

        offset_traj = all_trajectories.get(offset.well_id)
        if offset_traj is None:
            continue

        offset_tops = all_formation_tops.get(offset.well_id, [])
        offset_events = all_events.get(offset.well_id, [])

        scores = compute_dors(
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

        # Count events near current depth
        events_in_window = sum(
            1 for e in offset_events
            if abs(e.depth_start_md_m - active_depth_m) <= 150
        )

        rankings.append(OffsetWellRanking(
            rank=0,  # filled after sort
            well_id=offset.well_id,
            well_name=offset.well_name,
            field=offset.field,
            well_type=offset.well_type.value,
            dors_score=scores.total,
            component_scores=scores,
            formation_match=active_formation or "N/A",
            events_in_lookahead=events_in_window,
            distance_km=scores.distance_km,
        ))

    # Sort by DORS score descending
    rankings.sort(key=lambda r: r.dors_score, reverse=True)

    # Assign ranks
    for i, r in enumerate(rankings[:top_n]):
        r.rank = i + 1

    return rankings[:top_n]

