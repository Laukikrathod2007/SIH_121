"""
Broader real-data validation of module 02's stratigraphic correlator and
DORS trajectory scoring, using 22 real WITSML-parsed Volve wells (vs. the 2
hand-picked PDF-derived wells in Step 17) -- real_data/real_trajectories_witsml.json.
"""
import sys
import json
import random
from pathlib import Path  # noqa: E402

# Canonical `app.modules.nwis` package lives under Backend/ (no longer
# dependent on the current working directory).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Backend"))

from app.modules.nwis.models.schemas import WellTrajectory
from app.modules.nwis.engines.stratigraphic_correlator import tvd_at_md
from app.modules.nwis.engines.dors_engine import score_trajectory

data = json.load(open("../../real_data/real_trajectories_witsml.json", encoding="utf-8"))
trajectories = {t["well_id"]: WellTrajectory(**t) for t in data}
print(f"Loaded {len(trajectories)} real WITSML-parsed wells.\n")

print("=== 1. Bulk interpolation-accuracy check (100 random real bracket midpoints) ===")
random.seed(42)
checked = 0
failures = 0
wells_list = [t for t in trajectories.values() if len(t.stations) >= 5]
for _ in range(100):
    traj = random.choice(wells_list)
    idx = random.randint(0, len(traj.stations) - 2)
    s0, s1 = traj.stations[idx], traj.stations[idx + 1]
    if s1.md_m <= s0.md_m:
        continue
    test_md = (s0.md_m + s1.md_m) / 2
    interp_tvd = tvd_at_md(traj, test_md)
    lo, hi = min(s0.tvd_m, s1.tvd_m), max(s0.tvd_m, s1.tvd_m)
    checked += 1
    if not (lo - 0.01 <= interp_tvd <= hi + 0.01):
        failures += 1
        print(f"  FAIL: {traj.well_id} MD={test_md:.1f} interp_tvd={interp_tvd:.2f} outside real bracket [{lo:.2f}, {hi:.2f}]")
print(f"Checked {checked} real interpolation points: {checked - failures}/{checked} within real bracket ({failures} failures)")

print()
print("=== 2. Pairwise score_trajectory across real well combinations ===")
pairs = [
    ("WELL-15_9-F-12", "WELL-15_9-F-14"),
    ("WELL-15_9-F-12", "WELL-15_9-F-15"),
    ("WELL-15_9-F-4", "WELL-15_9-F-5"),
    ("WELL-15_9-F-10", "WELL-NO 15_9-F-11"),
    ("WELL-15_9-F-15A", "WELL-15_9-F-15B"),
    ("WELL-15_9-F-9", "WELL-15_9-F-9 A"),
]
for w1_id, w2_id in pairs:
    if w1_id not in trajectories or w2_id not in trajectories:
        print(f"  (skip {w1_id} vs {w2_id} -- not in real set)")
        continue
    w1, w2 = trajectories[w1_id], trajectories[w2_id]
    max_incl_1 = max(s.inclination_deg for s in w1.stations)
    max_incl_2 = max(s.inclination_deg for s in w2.stations)
    score = score_trajectory(offset_traj=w2, active_traj=w1, active_well_type="J-Type")
    print(f"  {w1_id} (max incl {max_incl_1:.1f}) vs {w2_id} (max incl {max_incl_2:.1f}): score={score}")

print()
print("=== 3. Full ranking: score every real well against WELL-15_9-F-12 as 'active' ===")
active = trajectories["WELL-15_9-F-12"]
scores = []
for wid, traj in trajectories.items():
    if wid == "WELL-15_9-F-12":
        continue
    s = score_trajectory(offset_traj=traj, active_traj=active, active_well_type="J-Type")
    scores.append((wid, s))
scores.sort(key=lambda x: -x[1])
for wid, s in scores:
    print(f"  {s:.4f}  {wid}")
