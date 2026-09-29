"""
NWIS Engine — Minimum Curvature Trajectory Math (SPE/API Standard)

Ported from a teammate's (Prasad's) parallel `well_intelligence` module
(`services/trajectory_engine.py`) after a code audit confirmed it as a
genuinely new, more rigorous capability we lacked: the official SPE/API
Minimum Curvature Method for computing 3D wellbore geometry from directional
survey stations (MD, Inclination, Azimuth), including numerically-stable
handling of near-zero dogleg angles and tangential extrapolation beyond the
last known survey station.

This file is deliberately self-contained (only stdlib `math`/`dataclasses`/
`typing`) — Prasad's original had no repo-internal imports either, so no
import fixes were needed here (contrast with the ahead-of-bit corridor port
in engines/risk_corridor_engine.py, which DID have a real missing-import bug
to fix).

Where this plugs in: engines/stratigraphic_correlator.py's `tvd_at_md()`
(and friends) now use `compute_dogleg_angle`/`compute_ratio_factor` from
this module for the sub-interval interpolation between two known survey
stations, and for tangential extrapolation beyond the last station — see
that file for the integration and rationale. The higher-level
`calculate_minimum_curvature_trajectory`/`interpolate_trajectory_at_md`
helpers below operate on this module's own lightweight dataclasses (not our
Pydantic `WellTrajectory`/`SurveyStation` models) and are kept here, ported
as-is, for any future caller that needs to build a full trajectory from raw
(MD, Inc, Azi) triples from scratch — our current data model already stores
TVD/NS/EW per survey station (computed upstream by
data/synthetic/generate_testbed.py using this exact same math), so nothing
in our pipeline currently calls these two directly; only the two low-level
math primitives are consumed today.

Mathematical Formulation:
  Dogleg Angle:
    cos(beta) = cos(I1)*cos(I2) + sin(I1)*sin(I2)*cos(A2 - A1)
    beta = arccos(clamp(cos(beta), -1.0, 1.0))

  Ratio Factor:
    RF = (2 / beta) * tan(beta / 2)  if beta >= 1e-6
    RF = 1.0 + (beta^2)/12          if beta < 1e-6 (Taylor expansion for zero dogleg)

  Displacement Increments:
    Delta_TVD   = (Delta_MD / 2) * [cos(I1) + cos(I2)] * RF
    Delta_North = (Delta_MD / 2) * [sin(I1)*cos(A1) + sin(I2)*cos(A2)] * RF
    Delta_East  = (Delta_MD / 2) * [sin(I1)*sin(A1) + sin(I2)*sin(A2)] * RF
    DLS         = (degrees(beta) / Delta_MD) * 30.0  (deg/30m)

References:
  - API Bulletin D12 (Directional Surveying Calculations)
  - Sawaryn, S.J. and Thorogood, J.L. (2005): "A Compendium of Directional
    Calculations Based on the Minimum Curvature Method", SPE Drilling & Completion.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class RawSurveyStation:
    """Input survey station."""
    md_m: float
    inclination_deg: float
    azimuth_deg: float


@dataclass
class ComputedSurveyStation:
    """Output survey station with spatial coordinates and dogleg severity."""
    md_m: float
    inclination_deg: float
    azimuth_deg: float
    tvd_m: float
    tvdss_m: float
    north_m: float
    east_m: float
    dogleg_deg: float
    dls_deg_30m: float
    method: str = "MINIMUM_CURVATURE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "md_m": round(self.md_m, 2),
            "inclination_deg": round(self.inclination_deg, 3),
            "azimuth_deg": round(self.azimuth_deg, 3),
            "tvd_m": round(self.tvd_m, 2),
            "tvdss_m": round(self.tvdss_m, 2),
            "north_m": round(self.north_m, 2),
            "east_m": round(self.east_m, 2),
            "dogleg_deg": round(self.dogleg_deg, 4),
            "dls_deg_30m": round(self.dls_deg_30m, 3),
            "method": self.method,
        }


@dataclass
class TrajectoryResult:
    """Complete computed 3D wellbore trajectory."""
    well_id: str
    wellhead_elevation_m: float
    stations: List[ComputedSurveyStation]
    total_md_m: float
    max_tvd_m: float
    final_north_m: float
    final_east_m: float
    tvd_method: str = "MINIMUM_CURVATURE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "well_id": self.well_id,
            "wellhead_elevation_m": self.wellhead_elevation_m,
            "stations_count": len(self.stations),
            "total_md_m": round(self.total_md_m, 2),
            "max_tvd_m": round(self.max_tvd_m, 2),
            "final_north_m": round(self.final_north_m, 2),
            "final_east_m": round(self.final_east_m, 2),
            "tvd_method": self.tvd_method,
            "stations": [s.to_dict() for s in self.stations],
        }


def compute_ratio_factor(beta_rad: float) -> float:
    """
    Computes Ratio Factor (RF) with Taylor series expansion for numerical stability as beta -> 0.
    RF = (2 / beta) * tan(beta / 2)
    When beta < 1e-6 rad: RF = 1.0 + (beta^2) / 12
    """
    if beta_rad < 1e-6:
        # Taylor expansion prevents 0/0 division singularity
        return 1.0 + (beta_rad ** 2) / 12.0
    return (2.0 / beta_rad) * math.tan(beta_rad / 2.0)


def compute_dogleg_angle(inc1_rad: float, inc2_rad: float, az1_rad: float, az2_rad: float) -> float:
    """
    Computes the dogleg angle (beta) in radians between two directional vectors.
    cos(beta) = cos(inc1)*cos(inc2) + sin(inc1)*sin(inc2)*cos(az2 - az1)
    Clamped to [-1.0, 1.0] to eliminate floating point domain errors in arccos.
    """
    cos_beta = (
        math.cos(inc1_rad) * math.cos(inc2_rad)
        + math.sin(inc1_rad) * math.sin(inc2_rad) * math.cos(az2_rad - az1_rad)
    )
    cos_beta = max(-1.0, min(1.0, cos_beta))
    return math.acos(cos_beta)


def calculate_minimum_curvature_trajectory(
    raw_stations: List[RawSurveyStation],
    wellhead_elevation_m: float = 0.0,
    well_id: str = "WELL",
) -> TrajectoryResult:
    """
    Computes cumulative (TVD, TVDSS, North, East, DLS) using Minimum Curvature Method.

    Fallback behavior:
      - If raw_stations is empty: Returns a 0m station with method 'VERTICAL_ASSUMPTION'.
      - Handles duplicate MD stations gracefully (skips identical MDs, logs warning if conflicting).
      - Automatically inserts surface station at MD=0 if first station is > 0.
    """
    if not raw_stations:
        # Strict vertical well fallback
        station_zero = ComputedSurveyStation(
            md_m=0.0,
            inclination_deg=0.0,
            azimuth_deg=0.0,
            tvd_m=0.0,
            tvdss_m=-wellhead_elevation_m,
            north_m=0.0,
            east_m=0.0,
            dogleg_deg=0.0,
            dls_deg_30m=0.0,
            method="VERTICAL_ASSUMPTION",
        )
        return TrajectoryResult(
            well_id=well_id,
            wellhead_elevation_m=wellhead_elevation_m,
            stations=[station_zero],
            total_md_m=0.0,
            max_tvd_m=0.0,
            final_north_m=0.0,
            final_east_m=0.0,
            tvd_method="VERTICAL_ASSUMPTION",
        )

    # Sort stations strictly by MD
    sorted_raw = sorted(raw_stations, key=lambda s: s.md_m)

    # Filter out duplicate MD stations (keep first)
    deduped_raw: List[RawSurveyStation] = []
    seen_mds = set()
    for s in sorted_raw:
        if s.md_m < 0.0:
            raise ValueError(f"Invalid negative Measured Depth in survey: {s.md_m}m")
        if round(s.md_m, 4) in seen_mds:
            continue
        seen_mds.add(round(s.md_m, 4))
        deduped_raw.append(s)

    # Ensure surface station (MD=0) exists
    if deduped_raw[0].md_m > 0.0:
        first_s = deduped_raw[0]
        # Assume vertical from surface to first survey if inclination at first survey is small
        surface_station = RawSurveyStation(
            md_m=0.0,
            inclination_deg=0.0,
            azimuth_deg=first_s.azimuth_deg,
        )
        deduped_raw.insert(0, surface_station)

    computed_stations: List[ComputedSurveyStation] = []

    # Initialize first station at surface
    first = deduped_raw[0]
    computed_stations.append(
        ComputedSurveyStation(
            md_m=first.md_m,
            inclination_deg=first.inclination_deg,
            azimuth_deg=first.azimuth_deg,
            tvd_m=first.md_m,  # At surface MD=0, TVD=0
            tvdss_m=first.md_m - wellhead_elevation_m,
            north_m=0.0,
            east_m=0.0,
            dogleg_deg=0.0,
            dls_deg_30m=0.0,
            method="MINIMUM_CURVATURE",
        )
    )

    # Integrate forward station by station
    for i in range(1, len(deduped_raw)):
        prev = computed_stations[i - 1]
        curr_raw = deduped_raw[i]

        delta_md = curr_raw.md_m - prev.md_m
        if delta_md <= 0:
            continue

        inc1_rad = math.radians(prev.inclination_deg)
        inc2_rad = math.radians(curr_raw.inclination_deg)
        az1_rad = math.radians(prev.azimuth_deg)
        az2_rad = math.radians(curr_raw.azimuth_deg)

        beta_rad = compute_dogleg_angle(inc1_rad, inc2_rad, az1_rad, az2_rad)
        beta_deg = math.degrees(beta_rad)

        rf = compute_ratio_factor(beta_rad)

        delta_tvd = (delta_md / 2.0) * (math.cos(inc1_rad) + math.cos(inc2_rad)) * rf
        delta_north = (delta_md / 2.0) * (
            math.sin(inc1_rad) * math.cos(az1_rad) + math.sin(inc2_rad) * math.cos(az2_rad)
        ) * rf
        delta_east = (delta_md / 2.0) * (
            math.sin(inc1_rad) * math.sin(az1_rad) + math.sin(inc2_rad) * math.sin(az2_rad)
        ) * rf

        dls = (beta_deg / delta_md) * 30.0 if delta_md > 0.0 else 0.0

        cum_tvd = prev.tvd_m + delta_tvd
        cum_north = prev.north_m + delta_north
        cum_east = prev.east_m + delta_east
        cum_tvdss = cum_tvd - wellhead_elevation_m

        computed_stations.append(
            ComputedSurveyStation(
                md_m=curr_raw.md_m,
                inclination_deg=curr_raw.inclination_deg,
                azimuth_deg=curr_raw.azimuth_deg,
                tvd_m=cum_tvd,
                tvdss_m=cum_tvdss,
                north_m=cum_north,
                east_m=cum_east,
                dogleg_deg=beta_deg,
                dls_deg_30m=dls,
                method="MINIMUM_CURVATURE",
            )
        )

    last = computed_stations[-1]
    return TrajectoryResult(
        well_id=well_id,
        wellhead_elevation_m=wellhead_elevation_m,
        stations=computed_stations,
        total_md_m=last.md_m,
        max_tvd_m=max(s.tvd_m for s in computed_stations),
        final_north_m=last.north_m,
        final_east_m=last.east_m,
        tvd_method="MINIMUM_CURVATURE",
    )


def interpolate_trajectory_at_md(
    trajectory: TrajectoryResult,
    target_md: float,
) -> ComputedSurveyStation:
    """
    Interpolates continuous 3D spatial position at any arbitrary MD along the trajectory.

    Behavior:
      - MD <= 0: Returns surface station (TVD=0, North=0, East=0).
      - If trajectory has VERTICAL_ASSUMPTION: TVD=MD, TVDSS=MD-elevation, North=0, East=0.
      - MD within surveyed range [MD_i-1, MD_i]: Performs exact sub-interval Minimum Curvature.
      - MD > last surveyed station: Tangential extrapolation along last inclination/azimuth vector.
    """
    if target_md <= 0.0:
        return ComputedSurveyStation(
            md_m=0.0,
            inclination_deg=0.0,
            azimuth_deg=0.0,
            tvd_m=0.0,
            tvdss_m=-trajectory.wellhead_elevation_m,
            north_m=0.0,
            east_m=0.0,
            dogleg_deg=0.0,
            dls_deg_30m=0.0,
            method=trajectory.tvd_method,
        )

    if trajectory.tvd_method == "VERTICAL_ASSUMPTION" or not trajectory.stations:
        return ComputedSurveyStation(
            md_m=target_md,
            inclination_deg=0.0,
            azimuth_deg=0.0,
            tvd_m=target_md,
            tvdss_m=target_md - trajectory.wellhead_elevation_m,
            north_m=0.0,
            east_m=0.0,
            dogleg_deg=0.0,
            dls_deg_30m=0.0,
            method="VERTICAL_ASSUMPTION",
        )

    stations = trajectory.stations

    for s in stations:
        if abs(s.md_m - target_md) < 1e-4:
            return s

    for i in range(1, len(stations)):
        s_prev = stations[i - 1]
        s_curr = stations[i]

        if s_prev.md_m <= target_md <= s_curr.md_m:
            delta_md_total = s_curr.md_m - s_prev.md_m
            delta_md_target = target_md - s_prev.md_m
            frac = delta_md_target / delta_md_total

            inc1_rad = math.radians(s_prev.inclination_deg)
            inc2_rad = math.radians(s_curr.inclination_deg)
            az1_rad = math.radians(s_prev.azimuth_deg)
            az2_rad = math.radians(s_curr.azimuth_deg)

            inc_target_rad = inc1_rad + frac * (inc2_rad - inc1_rad)
            d_az = az2_rad - az1_rad
            if d_az > math.pi:
                d_az -= 2.0 * math.pi
            elif d_az < -math.pi:
                d_az += 2.0 * math.pi
            az_target_rad = az1_rad + frac * d_az

            beta_sub_rad = compute_dogleg_angle(inc1_rad, inc_target_rad, az1_rad, az_target_rad)
            rf_sub = compute_ratio_factor(beta_sub_rad)

            delta_tvd = (delta_md_target / 2.0) * (math.cos(inc1_rad) + math.cos(inc_target_rad)) * rf_sub
            delta_north = (delta_md_target / 2.0) * (
                math.sin(inc1_rad) * math.cos(az1_rad) + math.sin(inc_target_rad) * math.cos(az_target_rad)
            ) * rf_sub
            delta_east = (delta_md_target / 2.0) * (
                math.sin(inc1_rad) * math.sin(az1_rad) + math.sin(inc_target_rad) * math.sin(az_target_rad)
            ) * rf_sub

            cum_tvd = s_prev.tvd_m + delta_tvd
            cum_north = s_prev.north_m + delta_north
            cum_east = s_prev.east_m + delta_east
            cum_tvdss = cum_tvd - trajectory.wellhead_elevation_m
            dls_sub = (math.degrees(beta_sub_rad) / delta_md_target) * 30.0 if delta_md_target > 0 else 0.0

            return ComputedSurveyStation(
                md_m=target_md,
                inclination_deg=math.degrees(inc_target_rad),
                azimuth_deg=(math.degrees(az_target_rad) + 360.0) % 360.0,
                tvd_m=cum_tvd,
                tvdss_m=cum_tvdss,
                north_m=cum_north,
                east_m=cum_east,
                dogleg_deg=math.degrees(beta_sub_rad),
                dls_deg_30m=dls_sub,
                method="MINIMUM_CURVATURE",
            )

    # MD exceeds deepest surveyed station -> Tangential projection along last vector
    last = stations[-1]
    delta_md_extrap = target_md - last.md_m
    inc_rad = math.radians(last.inclination_deg)
    az_rad = math.radians(last.azimuth_deg)

    tvd_extrap = last.tvd_m + delta_md_extrap * math.cos(inc_rad)
    north_extrap = last.north_m + delta_md_extrap * math.sin(inc_rad) * math.cos(az_rad)
    east_extrap = last.east_m + delta_md_extrap * math.sin(inc_rad) * math.sin(az_rad)

    return ComputedSurveyStation(
        md_m=target_md,
        inclination_deg=last.inclination_deg,
        azimuth_deg=last.azimuth_deg,
        tvd_m=tvd_extrap,
        tvdss_m=tvd_extrap - trajectory.wellhead_elevation_m,
        north_m=north_extrap,
        east_m=east_extrap,
        dogleg_deg=0.0,
        dls_deg_30m=0.0,
        method="TANGENTIAL_EXTRAPOLATION",
    )
