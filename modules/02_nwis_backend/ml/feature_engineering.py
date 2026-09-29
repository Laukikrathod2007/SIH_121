"""
NWIS Module 02 — ML Feature Engineering

Builds a labeled training dataset for the hazard prediction models from the
synthetic testbed (data_store.py). Read this before touching train_hazard_models.py
or hazard_predictor.py — it explains what the model can and can't actually learn.

WHAT THE MODEL CAN LEARN FROM (available per any well, historical or active):
  - depth_m
  - formation pore_pressure_gradient_ppg at that depth (from formation_tops.json)
  - formation group (regional stratigraphic grouping — see engines/dors_engine.py's
    ASSAM_FORMATION_GROUPS, reused here for consistency)
  - trajectory inclination_deg at that depth (interpolated from survey stations)
  - well_type (Vertical / J-Type / S-Type)

WHAT IT DELIBERATELY DOES NOT LEARN FROM, AND WHY:
  - mud_weight_ppg / overbalance: DrillingEvent records in this synthetic testbed
    do NOT carry a mud weight at the time of the event — only the live telemetry
    stream (one well only) has mud_weight_ppg. Training rows would therefore all
    share the same constant assumed mud weight, and a model cannot learn a
    relationship from a constant. Overbalance is real domain knowledge, so it's
    kept as a physics-based ADDITIVE adjustment applied on top of the model's
    prediction at inference time (see hazard_predictor.py), not fed into the
    model itself — this is a deliberate hybrid design, not an oversight.
  - live telemetry features (torque/SPP/flow trends): only WELL-HGJ-012 has any
    telemetry in this dataset. Training a general cross-well model on a feature
    that's only populated for 1/12 wells would just be learning "is this
    WELL-HGJ-012," not a real telemetry relationship.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random

from models.schemas import Well, WellTrajectory, FormationTop, DrillingEvent, HazardType
from engines.dors_engine import ASSAM_FORMATION_GROUPS, _formation_group
from engines.stratigraphic_correlator import formation_at_depth, inclination_at_md

# Minimum positive examples required before we'll even attempt to train a model
# for a hazard type. Below this, any train/test split is statistically
# meaningless — see train_hazard_models.py for what happens instead (the
# existing physics heuristic stays authoritative for that hazard type).
MIN_POSITIVE_SAMPLES = 8

# How many negative (no-event) depths to sample per well per hazard type.
# Deliberately creates class imbalance in the ~10:1 range rather than an
# artificially balanced 50/50 — that would misrepresent how rare these events
# actually are. class_weight="balanced" in the classifier compensates instead.
NEGATIVES_PER_WELL = 15

# A historical event "claims" this many meters on either side of its recorded
# depth — a candidate negative sample too close to a real event is skipped
# rather than risk mislabeling a near-miss as a clean negative. Matches
# engines/risk_corridor_engine.py's DELTA_BUFFER for consistency.
EXCLUSION_BUFFER_M = 30.0

WELL_TYPE_ENCODING = {"Vertical": 0, "J-Type": 1, "S-Type": 2, "Horizontal": 3}
FORMATION_GROUP_ENCODING = {g: i for i, g in enumerate(sorted(ASSAM_FORMATION_GROUPS) + ["UNKNOWN"])}

FEATURE_NAMES = ["depth_m", "pore_pressure_ppg", "inclination_deg", "well_type_code", "formation_group_code"]


@dataclass
class TrainingRow:
    well_id: str
    depth_m: float
    label: int  # 1 = hazard occurred here, 0 = did not
    features: List[float]


def build_features(
    depth_m: float,
    formation_tops: List[FormationTop],
    trajectory: Optional[WellTrajectory],
    well_type: str,
) -> List[float]:
    """
    The single feature-extraction function used at BOTH training and inference
    time — if these two ever computed features differently, the model would
    silently degrade with no error. hazard_predictor.py imports this directly
    rather than re-implementing it.
    """
    fm = formation_at_depth(formation_tops, depth_m)
    pore_pressure = fm.pore_pressure_gradient_ppg if fm else 9.0  # regional default
    fm_group = _formation_group(fm.formation_name) if fm else "UNKNOWN"
    inclination = inclination_at_md(trajectory, depth_m) if trajectory else 0.0
    return [
        depth_m,
        pore_pressure,
        inclination,
        WELL_TYPE_ENCODING.get(well_type, 0),
        FORMATION_GROUP_ENCODING.get(fm_group, FORMATION_GROUP_ENCODING["UNKNOWN"]),
    ]


def build_training_dataset(
    hazard_type: HazardType,
    all_wells: List[Well],
    all_trajectories: dict[str, WellTrajectory],
    all_formation_tops: dict[str, List[FormationTop]],
    all_events: dict[str, List[DrillingEvent]],
    seed: int = 42,
) -> tuple[List[List[float]], List[int], List[str]]:
    """
    Returns (X, y, well_ids) for one hazard type across all wells.
    well_ids is returned alongside X/y so callers can do leave-one-WELL-out
    cross-validation (not just leave-one-ROW-out) — rows from the same well
    are correlated (same formations, same trajectory), so ordinary k-fold CV
    would leak information between train and test folds.
    """
    rng = random.Random(seed)
    X: List[List[float]] = []
    y: List[int] = []
    well_ids: List[str] = []

    for well in all_wells:
        traj = all_trajectories.get(well.well_id)
        tops = all_formation_tops.get(well.well_id, [])
        events = all_events.get(well.well_id, [])
        if traj is None or not traj.stations:
            continue

        md_min, md_max = traj.stations[0].md_m, traj.stations[-1].md_m
        hazard_events = [e for e in events if e.event_type == hazard_type]

        # Positive samples: the actual recorded depth of each event of this type
        for e in hazard_events:
            X.append(build_features(e.depth_start_md_m, tops, traj, well.well_type.value))
            y.append(1)
            well_ids.append(well.well_id)

        # Negative samples: random depths not within EXCLUSION_BUFFER_M of any
        # event of this type in this well
        exclusion_windows = [
            (e.depth_start_md_m - EXCLUSION_BUFFER_M, (e.depth_end_md_m or e.depth_start_md_m) + EXCLUSION_BUFFER_M)
            for e in hazard_events
        ]
        attempts = 0
        sampled = 0
        while sampled < NEGATIVES_PER_WELL and attempts < NEGATIVES_PER_WELL * 10:
            attempts += 1
            candidate = rng.uniform(md_min, md_max)
            if any(lo <= candidate <= hi for lo, hi in exclusion_windows):
                continue
            X.append(build_features(candidate, tops, traj, well.well_type.value))
            y.append(0)
            well_ids.append(well.well_id)
            sampled += 1

    return X, y, well_ids
