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
import math
from typing import List, Optional, Dict
from app.modules.well_intelligence.models.schemas import Well, WellTrajectory, FormationTop, SurveyStation
from app.modules.well_intelligence.services.trajectory_engine import compute_dogleg_angle, compute_ratio_factor


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
    Interpolate TVD at any MD using the minimum curvature method.
    Returns TVD in meters.

    Each survey station's own tvd_m is already minimum-curvature-accurate
    (data/synthetic/generate_testbed.py's generate_trajectory_stations
    builds it that way). What used to be missing was the interpolation
    BETWEEN two known stations and the extrapolation BEYOND the last one —
    previously both did a naive linear/flat treatment of tvd_m, which threw
    away that accuracy for any query MD that doesn't land exactly on a 30m
    survey station. This now uses the SPE/API Minimum Curvature Method (see
    engines/trajectory_engine.py, ported from a teammate's more rigorous
    trajectory engine) for both:
      - Interior interval: minimum-curvature sub-interval calculation from
        the bracketing station (s_prev) to the target MD, using the
        angle-interpolated inclination/azimuth at target_md (via
        inclination_at_md/azimuth_at_md below) as the second survey point.
      - Beyond the last station: tangential extrapolation along the last
        known inclination/azimuth vector, instead of clamping flat (a
        deviated well still building/holding angle does NOT stop gaining
        TVD just because surveys ran out).
    Signature/contract unchanged — same inputs, same float TVD return — so
    every existing caller (tvdss_at_md, stratigraphic_depth,
    align_horizons_across_wells, and anything reached from
    /api/v2/stratigraphic_depth_track) keeps working unmodified.
    """
    if not trajectory or not trajectory.stations:
        return target_md  # assume vertical

    if target_md <= stations[0].md_m:
        # Extrapolate before first survey (near-surface, inclination ~0 in
        # practice, so this proportional-vertical approximation is left as
        # a low-risk fallback — not the gap this upgrade targets).
        frac = target_md / max(stations[0].md_m, 0.001)
        return stations[0].tvd_m * frac

    for i in range(1, len(stations)):
        s_prev = stations[i - 1]
        s_curr = stations[i]
        if s_curr.md_m >= target_md:
            return _min_curvature_tvd_from_station(trajectory, s_prev, target_md)

    # Beyond the last surveyed station: tangential extrapolation along the
    # last known inclination vector (was: `return stations[-1].tvd_m`, a
    # flat clamp that silently assumed the well goes vertical past TD).
    last = stations[-1]
    delta_md = target_md - last.md_m
    return last.tvd_m + delta_md * math.cos(math.radians(last.inclination_deg))


def _min_curvature_tvd_from_station(
    trajectory: WellTrajectory,
    s_prev: SurveyStation,
    target_md: float,
) -> float:
    """
    Minimum-curvature TVD delta from a known survey station (s_prev) to an
    arbitrary target_md that falls before the NEXT survey station, anchored
    on s_prev's already-known (and already minimum-curvature-accurate)
    tvd_m rather than recomputing the whole trajectory from surface. The
    "second survey point" for the dogleg calculation is the
    angle-interpolated inclination/azimuth at target_md (inclination_at_md/
    azimuth_at_md already do correct linear/circular interpolation of the
    raw angles — reused here rather than duplicated).
    """
    delta_md = target_md - s_prev.md_m
    if delta_md <= 0:
        return s_prev.tvd_m

    inc_target = inclination_at_md(trajectory, target_md)
    az_target = azimuth_at_md(trajectory, target_md)

    inc1_rad = math.radians(s_prev.inclination_deg)
    inc2_rad = math.radians(inc_target)
    az1_rad = math.radians(s_prev.azimuth_deg)
    az2_rad = math.radians(az_target)

    beta_rad = compute_dogleg_angle(inc1_rad, inc2_rad, az1_rad, az2_rad)
    rf = compute_ratio_factor(beta_rad)

    delta_tvd = (delta_md / 2.0) * (math.cos(inc1_rad) + math.cos(inc2_rad)) * rf
    return s_prev.tvd_m + delta_tvd


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


# Public alias — this function is used internally (align_horizons_across_wells
# above calls the leading-underscore name directly), but the ahead-of-bit
# corridor projection added in engines/risk_corridor_engine.py needs it as a
# cross-module import, so it's exposed here under a non-private name rather
# than having another module reach into a "private" function.
md_at_tvd = _md_at_tvd
