"""
NWIS Engine 02 — Stratigraphic Depth Correlator
Computes True Vertical Depth Subsea (TVDSS), stratigraphic normalized depth,
and aligns offset wells at equivalent geological horizons.

Formula:
  d_strat(w, d) = TVD(w, d) - Top_TVD(Formation_k, w)

Eliminates the "Trajectory Trap" — false MD comparisons between vertical
and directional wells drilling through the same geological formation.
"""

from __future__ import annotations
from typing import List, Optional, Dict
from models.schemas import Well, WellTrajectory, FormationTop, SurveyStation


# ---------------------------------------------------------------------------
# Minimum Curvature TVD Calculator
# ---------------------------------------------------------------------------

def tvd_at_md(trajectory: WellTrajectory, target_md: float) -> float:
    """
    Interpolate TVD at any MD using the minimum curvature method.
    Returns TVD in meters.
    """
    stations = trajectory.stations
    if not stations:
        return target_md  # assume vertical

    if target_md <= stations[0].md_m:
        # Extrapolate before first survey
        frac = target_md / max(stations[0].md_m, 0.001)
        return stations[0].tvd_m * frac

    for i in range(1, len(stations)):
        s_prev = stations[i - 1]
        s_curr = stations[i]
        if s_curr.md_m >= target_md:
            frac = (target_md - s_prev.md_m) / max(s_curr.md_m - s_prev.md_m, 0.001)
            return s_prev.tvd_m + frac * (s_curr.tvd_m - s_prev.tvd_m)

    return stations[-1].tvd_m


def inclination_at_md(trajectory: WellTrajectory, target_md: float) -> float:
    """
    Interpolate inclination (degrees) at a given MD — same interpolation
    pattern as tvd_at_md above, applied to inclination_deg instead. Shared by
    engines/dors_engine.py's trajectory-similarity scoring and ml/
    feature_engineering.py's model features, so both use the exact same
    interpolation (a discrepancy here would silently skew one or the other).
    """
    stations = trajectory.stations
    if not stations:
        return 0.0
    if target_md <= stations[0].md_m:
        return stations[0].inclination_deg
    for i in range(1, len(stations)):
        s_prev, s_curr = stations[i - 1], stations[i]
        if s_curr.md_m >= target_md:
            frac = (target_md - s_prev.md_m) / max(s_curr.md_m - s_prev.md_m, 0.001)
            return s_prev.inclination_deg + frac * (s_curr.inclination_deg - s_prev.inclination_deg)
    return stations[-1].inclination_deg


def azimuth_at_md(trajectory: WellTrajectory, target_md: float) -> float:
    """
    Interpolate azimuth (degrees, 0-360) at a given MD. Azimuth is circular
    (0 and 360 are the same heading), so this interpolates via unit vectors
    (cos/sin) rather than the raw angle — a naive linear interpolation
    between e.g. 350 deg and 10 deg would wrongly average to 180 deg (due
    south) instead of the correct ~0 deg (due north).
    """
    import math
    stations = trajectory.stations
    if not stations:
        return 0.0

    def _to_vec(deg: float) -> tuple[float, float]:
        rad = math.radians(deg)
        return math.cos(rad), math.sin(rad)

    def _vec_to_deg(x: float, y: float) -> float:
        return math.degrees(math.atan2(y, x)) % 360

    if target_md <= stations[0].md_m:
        return stations[0].azimuth_deg
    for i in range(1, len(stations)):
        s_prev, s_curr = stations[i - 1], stations[i]
        if s_curr.md_m >= target_md:
            frac = (target_md - s_prev.md_m) / max(s_curr.md_m - s_prev.md_m, 0.001)
            x1, y1 = _to_vec(s_prev.azimuth_deg)
            x2, y2 = _to_vec(s_curr.azimuth_deg)
            return _vec_to_deg(x1 + frac * (x2 - x1), y1 + frac * (y2 - y1))
    return stations[-1].azimuth_deg


def tvdss_at_md(trajectory: WellTrajectory, well: Well, target_md: float) -> float:
    """
    TVD Subsea = TVD - KB_Elevation.
    Negative values = above sea level.
    """
    tvd = tvd_at_md(trajectory, target_md)
    return tvd - well.kb_elevation_m


# ---------------------------------------------------------------------------
# Stratigraphic Normalized Depth
# ---------------------------------------------------------------------------

def formation_at_depth(tops: List[FormationTop], md: float) -> Optional[FormationTop]:
    """Return which formation is penetrated at this MD."""
    for top in sorted(tops, key=lambda t: t.top_md_m):
        if top.top_md_m <= md <= top.base_md_m:
            return top
    # Check if deeper than last known formation
    if tops:
        deepest = max(tops, key=lambda t: t.base_md_m)
        if md > deepest.base_md_m:
            return deepest
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
    offset wells. Returns a dict of well_id → alignment data.

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
