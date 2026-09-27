"""
NWIS Engine 02 â€” Stratigraphic Depth Correlator
Computes True Vertical Depth Subsea (TVDSS), stratigraphic normalized depth,
and aligns offset wells at equivalent geological horizons.

Formula:
  d_strat(w, d) = TVD(w, d) - Top_TVD(Formation_k, w)

Eliminates the "Trajectory Trap" â€” false MD comparisons between vertical
and directional wells drilling through the same geological formation.
"""

from __future__ import annotations
from typing import List, Optional, Dict
from app.modules.well_intelligence.models.schemas import Well, WellTrajectory, FormationTop, SurveyStation
from app.modules.well_intelligence.services.trajectory_engine import (
    RawSurveyStation,
    calculate_minimum_curvature_trajectory,
    interpolate_trajectory_at_md,
    TrajectoryResult,
)


# ---------------------------------------------------------------------------
# Minimum Curvature TVD Calculator
# ---------------------------------------------------------------------------

def get_computed_trajectory(trajectory: Optional[WellTrajectory], wellhead_elevation_m: float = 0.0) -> TrajectoryResult:
    """Helper to convert schema WellTrajectory to computed Minimum Curvature TrajectoryResult."""
    if not trajectory or not trajectory.stations:
        return calculate_minimum_curvature_trajectory([], wellhead_elevation_m=wellhead_elevation_m)
    
    raw_stations = [
        RawSurveyStation(
            md_m=s.md_m,
            inclination_deg=s.inclination_deg,
            azimuth_deg=s.azimuth_deg,
        )
        for s in trajectory.stations
    ]
    return calculate_minimum_curvature_trajectory(
        raw_stations=raw_stations,
        wellhead_elevation_m=wellhead_elevation_m,
        well_id=trajectory.well_id,
    )


def tvd_at_md(trajectory: Optional[WellTrajectory], target_md: float) -> float:
    """
    Interpolate TVD at any MD using minimum curvature method.
    Returns TVD in meters. Fallback to vertical assumption when no stations exist.
    If survey stations already contain pre-calculated tvd_m, interpolates between stations.
    """
    if not trajectory or not trajectory.stations:
        return target_md  # assume vertical

    # Sort stations by MD
    stations = sorted(trajectory.stations, key=lambda s: s.md_m)

    # Check if stations already have pre-calculated tvd_m (e.g. from existing survey or test fixture)
    has_precalculated_tvd = any(s.tvd_m > 0 for s in stations[1:]) if len(stations) > 1 else False
    if has_precalculated_tvd:
        if target_md <= stations[0].md_m:
            frac = target_md / max(stations[0].md_m, 0.001)
            return stations[0].tvd_m * frac

        for i in range(1, len(stations)):
            s_prev = stations[i - 1]
            s_curr = stations[i]
            if s_curr.md_m >= target_md:
                span = s_curr.md_m - s_prev.md_m
                if span <= 0:
                    return s_curr.tvd_m
                frac = (target_md - s_prev.md_m) / span
                return s_prev.tvd_m + frac * (s_curr.tvd_m - s_prev.tvd_m)

        # Extrapolate beyond last station
        if len(stations) >= 2:
            last = stations[-1]
            prev = stations[-2]
            d_md = last.md_m - prev.md_m
            if d_md > 0:
                rate = (last.tvd_m - prev.tvd_m) / d_md
                return last.tvd_m + (target_md - last.md_m) * rate
        return stations[-1].tvd_m

    # Otherwise, calculate from raw inclination/azimuth via SPE/API Minimum Curvature
    computed = get_computed_trajectory(trajectory, wellhead_elevation_m=0.0)
    interp = interpolate_trajectory_at_md(computed, target_md)
    return interp.tvd_m


def tvdss_at_md(trajectory: Optional[WellTrajectory], well: Well, target_md: float) -> float:
    """
    TVD Subsea = TVD - KB_Elevation.
    Negative values = above sea level.
    """
    tvd = tvd_at_md(trajectory, target_md)
    return tvd - well.kb_elevation_m


# ---------------------------------------------------------------------------
# Stratigraphic Normalized Depth & Formation Identification
# ---------------------------------------------------------------------------

def formation_at_depth(tops: List[FormationTop], md: float) -> Optional[FormationTop]:
    """Return which formation is penetrated at this MD using top_md <= md < base_md."""
    if not tops:
        return None
    for top in sorted(tops, key=lambda t: t.top_md_m):
        if top.thickness_m > 0 and top.top_md_m <= md < top.base_md_m:
            return top
    return None


def formation_at_tvdss(tops: List[FormationTop], well: Well, tvdss_m: float) -> Optional[FormationTop]:
    """Return which formation is penetrated at this TVDSS using top_tvdss <= tvdss < base_tvdss."""
    if not tops:
        return None
    
    def get_top_tvdss(top: FormationTop) -> float:
        if top.top_tvdss_m is not None:
            return top.top_tvdss_m
        return top.top_tvd_m - well.kb_elevation_m

    def get_base_tvdss(top: FormationTop) -> float:
        if top.base_tvdss_m is not None:
            return top.base_tvdss_m
        return get_top_tvdss(top) + top.thickness_m

    sorted_tops = sorted(tops, key=get_top_tvdss)
    for top in sorted_tops:
        top_z = get_top_tvdss(top)
        base_z = get_base_tvdss(top)
        if base_z > top_z and top_z <= tvdss_m < base_z:
            return top
    return None



def stratigraphic_depth(
    trajectory: WellTrajectory,
    tops: List[FormationTop],
    md: float,
) -> Optional[float]:
    """
    d_strat(w, d) = TVD(w, d) - Top_TVD(Formation_k, w)

    Computes penetration distance *within* the current geological formation.
    This eliminates false depth comparisons between directional and vertical wells.
    """
    fm = formation_at_depth(tops, md)
    if fm is None:
        return None

    tvd_current = tvd_at_md(trajectory, md)
    tvd_formation_top = fm.top_tvd_m  # Already converted in data

    return round(tvd_current - tvd_formation_top, 2)


# ---------------------------------------------------------------------------
# Multi-Well Horizon Alignment
# ---------------------------------------------------------------------------

def align_horizons_across_wells(
    active_md: float,
    active_well: Well,
    active_traj: WellTrajectory,
    active_tops: List[FormationTop],
    offset_wells: List[Well],
    offset_trajs: Dict[str, WellTrajectory],
    offset_tops_map: Dict[str, List[FormationTop]],
) -> Dict[str, dict]:
    """
    For the active bit position, compute the equivalent formation depth in all
    offset wells. Returns a dict of well_id â†’ alignment data.

    This powers the "Stratigraphic Depth Track" visualization.
    """
    active_fm = formation_at_depth(active_tops, active_md)
    active_tvd = tvd_at_md(active_traj, active_md)
    active_d_strat = stratigraphic_depth(active_traj, active_tops, active_md)

    result = {
        active_well.well_id: {
            "well_name": active_well.well_name,
            "md_m": active_md,
            "tvd_m": round(active_tvd, 2),
            "tvdss_m": round(tvdss_at_md(active_traj, active_well, active_md), 2),
            "formation": active_fm.formation_name if active_fm else None,
            "d_strat_m": active_d_strat,
            "is_active": True,
        }
    }

    for offset in offset_wells:
        if offset.well_id == active_well.well_id:
            continue

        o_traj = offset_trajs.get(offset.well_id)
        o_tops = offset_tops_map.get(offset.well_id, [])

        if o_traj is None:
            continue

        # Find the equivalent MD in offset well where same formation is at same d_strat
        equiv_md = None
        equiv_tvd = None
        offset_fm = None

        if active_fm and active_d_strat is not None:
            # Find this formation's top in offset well
            for top in o_tops:
                if top.formation_name == active_fm.formation_name:
                    # Equivalent TVD = formation_top_TVD + d_strat
                    target_tvd = top.top_tvd_m + active_d_strat
                    # Find MD corresponding to this TVD in offset trajectory
                    equiv_md = _md_at_tvd(o_traj, target_tvd)
                    equiv_tvd = target_tvd
                    offset_fm = top.formation_name
                    break

        if equiv_md is None and o_traj.stations:
            # Fallback: use raw MD
            equiv_md = active_md
            equiv_tvd = tvd_at_md(o_traj, active_md)

        result[offset.well_id] = {
            "well_name": offset.well_name,
            "md_m": round(equiv_md, 2) if equiv_md else None,
            "tvd_m": round(equiv_tvd, 2) if equiv_tvd else None,
            "tvdss_m": round(tvdss_at_md(o_traj, offset, equiv_md or 0), 2) if equiv_md else None,
            "formation": offset_fm,
            "d_strat_m": active_d_strat,
            "is_active": False,
        }

    return result


def _md_at_tvd(trajectory: WellTrajectory, target_tvd: float) -> Optional[float]:
    """Inverse interpolation: find MD corresponding to a target TVD."""
    stations = trajectory.stations
    if not stations:
        return target_tvd

    for i in range(1, len(stations)):
        s_prev = stations[i - 1]
        s_curr = stations[i]
        if s_prev.tvd_m <= target_tvd <= s_curr.tvd_m:
            frac = (target_tvd - s_prev.tvd_m) / max(s_curr.tvd_m - s_prev.tvd_m, 0.001)
            return s_prev.md_m + frac * (s_curr.md_m - s_prev.md_m)

    # Extrapolate beyond last station
    if target_tvd > stations[-1].tvd_m:
        last = stations[-1]
        prev = stations[-2] if len(stations) > 1 else last
        tvd_rate = (last.tvd_m - prev.tvd_m) / max(last.md_m - prev.md_m, 0.001)
        if tvd_rate > 0:
            return last.md_m + (target_tvd - last.tvd_m) / tvd_rate

    return None

