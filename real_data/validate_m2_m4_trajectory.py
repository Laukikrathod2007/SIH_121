"""
Real-data validation of modules/02_nwis_backend's stratigraphic correlator
(tvd_at_md/inclination_at_md/azimuth_at_md) and DORS trajectory scoring
(score_trajectory), against real parsed Equinor Volve directional surveys
(real_data/real_trajectories.json -- see parse_real_trajectories.py).

Two things are checked, both against REAL data, not synthetic:
1. Interpolation accuracy: pick MDs that fall BETWEEN two real survey
   stations (not on one), interpolate TVD/inclination/azimuth, and compare
   against a station actually close to that MD -- if the interpolation is
   sound, it should track smoothly between the two real bracketing values.
2. Whether score_trajectory correctly identifies these two real wells (F-1,
   which builds to ~21 deg and holds; F-12, which builds much further to
   ~53 deg) as trajectory-DISSIMILAR despite being the same well_type and
   field -- this is the exact "two wells with different real shapes" case
   the Hausdorff-profile approach was built to get right where a single
   avg-inclination scalar would not.
"""
import sys
import json
sys.path.insert(0, ".")

from models.schemas import WellTrajectory
from engines.stratigraphic_correlator import tvd_at_md, inclination_at_md, azimuth_at_md
from engines.dors_engine import score_trajectory

data = json.load(open("../../real_data/real_trajectories.json", encoding="utf-8"))
trajectories = {t["well_id"]: WellTrajectory(**t) for t in data}

f1 = trajectories["WELL-15_9-F-1"]
f12 = trajectories["WELL-15_9-F-12"]

print("=== 1. Interpolation accuracy against real survey stations ===")
for traj, name in [(f1, "F-1"), (f12, "F-12")]:
    stations = traj.stations
    mid_idx = len(stations) // 2
    s_before, s_after = stations[mid_idx], stations[mid_idx + 1]
    test_md = (s_before.md_m + s_after.md_m) / 2
    interp_tvd = tvd_at_md(traj, test_md)
    interp_inc = inclination_at_md(traj, test_md)
    interp_azi = azimuth_at_md(traj, test_md)
    print(f"{name}: interpolating at MD={test_md:.1f}m (between real stations "
          f"MD={s_before.md_m}/TVD={s_before.tvd_m} and MD={s_after.md_m}/TVD={s_after.tvd_m})")
    print(f"       -> interpolated TVD={interp_tvd:.2f}m (real bracket: {s_before.tvd_m}-{s_after.tvd_m}m) "
          f"{'OK: within bracket' if min(s_before.tvd_m, s_after.tvd_m) <= interp_tvd <= max(s_before.tvd_m, s_after.tvd_m) else 'FAIL: outside bracket'}")
    print(f"       -> interpolated inclination={interp_inc:.2f} deg, azimuth={interp_azi:.2f} deg")

print()
print("=== 2. score_trajectory on two REAL, genuinely different-shaped wells ===")
print(f"F-1  profile: builds to ~{max(s.inclination_deg for s in f1.stations):.1f} deg and holds (J-type)")
print(f"F-12 profile: builds to ~{max(s.inclination_deg for s in f12.stations):.1f} deg (J-type)")
score = score_trajectory(offset_traj=f12, active_traj=f1, active_well_type="J-Type")
print(f"score_trajectory(offset=F-12, active=F-1) = {score}")
print(f"(1.0 = identical trajectory shape, 0.0 = maximally dissimilar; "
      f"these are real wells with genuinely different build profiles in the same field)")

# Self-comparison sanity check: a well compared against itself must score 1.0
self_score = score_trajectory(offset_traj=f1, active_traj=f1, active_well_type="J-Type")
print(f"\nSanity check -- score_trajectory(F-1, F-1) = {self_score} (must be 1.0)")
