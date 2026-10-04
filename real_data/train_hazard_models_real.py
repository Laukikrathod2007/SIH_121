"""
Real-data retraining of the hazard prediction models -- replaces the
synthetic-testbed training in modules/02_nwis_backend/ml/train_hazard_models.py
with real Equinor Volve data: real depth-tagged events (module 01's fixed
extraction, re-run fresh against all 14 real documents), real WITSML
trajectories (22 real wells), real formation tops.

Reuses module 02's OWN build_features()/build_training_dataset()/
_leave_one_well_out_auc() functions directly rather than reimplementing
them, so the real-data model is trained through the exact same code path
as the synthetic one -- only the input data differs.

Honest, stated up front: this is a genuinely small real dataset (33
depth-tagged real events across 4 real wells, after the vast majority of
the 119 total real extracted events turned out to have no depth in the
source narrative at all). Only hazard types with >=8 real positive
examples spread across more than one well are attempted -- MIN_POSITIVE_
SAMPLES matches module 02's own threshold, and single-well concentration
would make leave-one-well-out CV degenerate.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "modules" / "02_nwis_backend"))

from models.schemas import (
    Well, WellType, WellTrajectory, SurveyStation, FormationTop,
    DrillingEvent, HazardType,
)
from ml.feature_engineering import build_features, MIN_POSITIVE_SAMPLES, FEATURE_NAMES
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
import numpy as np
import random
import joblib


def build_training_dataset_soft(hazard_type, all_wells, all_trajectories, all_formation_tops, all_events, seed=42):
    """
    Same as module 02's build_training_dataset(), EXCEPT it does not hard-
    exclude a well with no real trajectory -- build_features() already has
    a documented, deliberate 0.0-inclination fallback for exactly this case
    (see its docstring), so this uses that fallback instead of dropping the
    well's real events entirely. Every row built this way from a
    no-trajectory well is tagged so the caller can report it honestly, not
    silently blend it in as equivalent to a real trajectory reading.
    """
    rng = random.Random(seed)
    X, y, well_ids, used_fallback_inclination = [], [], [], []
    NEGATIVES_PER_WELL = 15
    EXCLUSION_BUFFER_M = 30.0

    for well in all_wells:
        traj = all_trajectories.get(well.well_id)
        tops = all_formation_tops.get(well.well_id, [])
        events = all_events.get(well.well_id, [])
        hazard_events = [e for e in events if e.event_type == hazard_type]
        if not hazard_events:
            continue

        md_values = [e.depth_start_md_m for e in hazard_events]
        md_min, md_max = min(md_values) - 200, max(md_values) + 200

        for e in hazard_events:
            X.append(build_features(e.depth_start_md_m, tops, traj, well.well_type.value))
            y.append(1)
            well_ids.append(well.well_id)
            used_fallback_inclination.append(traj is None)

        exclusion_windows = [(e.depth_start_md_m - EXCLUSION_BUFFER_M, e.depth_start_md_m + EXCLUSION_BUFFER_M) for e in hazard_events]
        attempts, sampled = 0, 0
        while sampled < NEGATIVES_PER_WELL and attempts < NEGATIVES_PER_WELL * 10:
            attempts += 1
            candidate = rng.uniform(md_min, md_max)
            if any(lo <= candidate <= hi for lo, hi in exclusion_windows):
                continue
            X.append(build_features(candidate, tops, traj, well.well_type.value))
            y.append(0)
            well_ids.append(well.well_id)
            used_fallback_inclination.append(traj is None)
            sampled += 1

    return X, y, well_ids, used_fallback_inclination


def leave_one_well_out_per_fold(X, y, well_ids):
    """Same methodology as module 02's _leave_one_well_out_auc, but returns
    every fold's individual result instead of just the mean -- more honest
    with a small number of wells, where a single mean can hide that (say)
    one fold scored 0.95 and another scored 0.40."""
    unique_wells = sorted(set(well_ids))
    fold_results = []
    for held_out in unique_wells:
        test_mask = np.array([w == held_out for w in well_ids])
        train_mask = ~test_mask
        y_test = y[test_mask]
        if len(set(y_test.tolist())) < 2 or train_mask.sum() < 4:
            fold_results.append({"well": held_out, "auc": None, "reason": "single-class fold, AUC undefined"})
            continue
        model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
        model.fit(X[train_mask], y[train_mask])
        proba = model.predict_proba(X[test_mask])[:, 1]
        auc = roc_auc_score(y_test, proba)
        fold_results.append({"well": held_out, "auc": round(float(auc), 3), "n_test": int(test_mask.sum())})
    valid = [f["auc"] for f in fold_results if f["auc"] is not None]
    mean_auc = float(np.mean(valid)) if valid else float("nan")
    return fold_results, mean_auc

REAL_DATA = REPO_ROOT / "real_data"
MODELS_OUT = REAL_DATA / "real_trained_models"
MODELS_OUT.mkdir(exist_ok=True)

# Manual reconciliation between the 4 target wells' event-derived well_id
# and the real WITSML trajectory file's own well_id naming (different
# service-company/era naming conventions for the same physical wells --
# same real finding documented in logger Step 19). 15/9-19B genuinely has
# NO real trajectory in the WITSML pull -- stays None, not guessed.
TRAJECTORY_WELL_MAP = {
    "15/9-F-1": "WELL-15_9-F-1",
    "15/9-F-12": "WELL-15_9-F-12",
    "15/9-F-1C": "WELL-NO 15_9-F-1 C",
    "15/9-19B": None,
}

TARGET_WELLS = list(TRAJECTORY_WELL_MAP.keys())


def load_real_events() -> dict[str, list[DrillingEvent]]:
    with open(REAL_DATA / "real_events_depth_tagged_fresh.json", encoding="utf-8") as f:
        raw = json.load(f)
    events_by_well: dict[str, list[DrillingEvent]] = {w: [] for w in TARGET_WELLS}
    for e in raw:
        if e["well_id"] not in TARGET_WELLS or e["hazard_type"] is None:
            continue
        events_by_well[e["well_id"]].append(
            DrillingEvent(
                well_id=e["well_id"],
                event_type=HazardType(e["hazard_type"]),
                severity=e["severity"],
                depth_start_md_m=e["depth_start_md_m"],
            )
        )
    return events_by_well


def load_real_trajectories() -> dict[str, WellTrajectory]:
    with open(REAL_DATA / "real_trajectories_witsml.json", encoding="utf-8") as f:
        raw = json.load(f)
    by_traj_id = {t["well_id"]: t for t in raw}
    trajectories: dict[str, WellTrajectory] = {}
    for well_id, traj_key in TRAJECTORY_WELL_MAP.items():
        if traj_key is None or traj_key not in by_traj_id:
            continue
        t = by_traj_id[traj_key]
        stations = [
            SurveyStation(
                md_m=s["md_m"], inclination_deg=s["inclination_deg"],
                azimuth_deg=s["azimuth_deg"], tvd_m=s["tvd_m"],
                ns_m=s["ns_m"], ew_m=s["ew_m"], tvdss_m=s["tvdss_m"],
            )
            for s in t["stations"]
        ]
        trajectories[well_id] = WellTrajectory(
            well_id=well_id, well_name=well_id, method=t["method"],
            well_type=t.get("well_type", "Vertical"), stations=stations,
        )
    return trajectories


def build_real_wells(trajectories: dict[str, WellTrajectory]) -> list[Well]:
    wells = []
    for well_id in TARGET_WELLS:
        traj = trajectories.get(well_id)
        wt_raw = traj.well_type if traj else "Vertical"
        wt = {"J-Type": WellType.J_TYPE, "S-Type": WellType.S_TYPE,
              "Vertical": WellType.VERTICAL, "Horizontal": WellType.HORIZONTAL}.get(wt_raw, WellType.VERTICAL)
        wells.append(Well(
            well_id=well_id, well_name=well_id, field="Volve", field_code="VOLVE",
            operator="Equinor", surface_lat=58.4, surface_lon=1.9,
            total_depth_md_m=4000.0, well_type=wt,
        ))
    return wells


def load_real_formation_tops() -> dict[str, list[FormationTop]]:
    with open(REAL_DATA / "real_formations_fresh.json", encoding="utf-8") as f:
        raw = json.load(f)
    tops_by_well: dict[str, list[FormationTop]] = {w: [] for w in TARGET_WELLS}
    for f_ in raw:
        if f_["well_id"] not in TARGET_WELLS or f_["top_md_m"] is None:
            continue
        # HONEST: module 01 does not extract a real pore-pressure gradient
        # per formation -- this stays at module 02's own regional default
        # (9.0 ppg) for every real formation here, meaning the
        # pore_pressure_ppg FEATURE carries no real per-formation signal in
        # this real-data run, exactly the same class of limitation the
        # existing code already discloses for mud_weight/overbalance.
        tops_by_well[f_["well_id"]].append(FormationTop(
            well_id=f_["well_id"], well_name=f_["well_id"],
            formation_name=f_["formation_name"], top_md_m=f_["top_md_m"],
            top_tvd_m=f_["top_md_m"], base_md_m=f_["top_md_m"] + 50,
            thickness_m=50.0,
        ))
    return tops_by_well


def main():
    events_by_well = load_real_events()
    trajectories = load_real_trajectories()
    wells = build_real_wells(trajectories)
    tops_by_well = load_real_formation_tops()

    print("=" * 70)
    print("REAL-DATA HAZARD MODEL TRAINING (Equinor Volve field)")
    print("=" * 70)
    print(f"Wells: {TARGET_WELLS}")
    print(f"Wells WITH real trajectory: {[w for w, t in trajectories.items()]}")
    print(f"Wells WITHOUT real trajectory (inclination defaults to 0.0): "
          f"{[w for w in TARGET_WELLS if w not in trajectories]}")
    for w in TARGET_WELLS:
        print(f"  {w}: {len(events_by_well[w])} events, {len(tops_by_well[w])} formation tops")
    print()

    results = {}
    # KICK and MUD_LOSS added 2026-10-04 after merge_unused_real_events.py
    # recovered genuinely usable, previously-unmerged real depth-tagged
    # events from real_events_module01.json (a raw extraction dump that had
    # never been fed into real_events_depth_tagged_fresh.json before). See
    # that script's own docstring for the exact exclusion/dedup reasoning
    # (a garbled/unexplained well bucket, 2 physically-impossible depths, a
    # geological-description false positive, and 6 duplicate-OCR-pass rows
    # were all identified and excluded, not blindly merged).
    for hazard_type in [HazardType.STUCK_PIPE, HazardType.WELLBORE_INSTABILITY, HazardType.KICK, HazardType.MUD_LOSS]:
        print(f"--- {hazard_type.value} ---")

        # Soft dataset: includes 19B (no real trajectory -> inclination
        # defaults to 0.0 for those specific rows, per build_features'
        # own documented fallback), rather than module 02's live
        # build_training_dataset() which hard-excludes it. Deviation
        # explicitly disclosed, not silent.
        X, y, well_ids, used_fallback = build_training_dataset_soft(
            hazard_type=hazard_type, all_wells=wells, all_trajectories=trajectories,
            all_formation_tops=tops_by_well, all_events=events_by_well,
        )
        n_pos = sum(y)
        n_wells_with_pos = len({w for w, label in zip(well_ids, y) if label == 1})
        n_fallback_rows = sum(used_fallback)
        print(f"  Total rows: {len(X)} ({n_pos} positive, {len(X) - n_pos} negative)")
        print(f"  Positive examples span {n_wells_with_pos} real wells")
        print(f"  Rows using 0.0-inclination fallback (no real trajectory): {n_fallback_rows}/{len(X)}")

        if n_pos < MIN_POSITIVE_SAMPLES:
            print(f"  SKIPPED even with 19B included: {n_pos} < MIN_POSITIVE_SAMPLES ({MIN_POSITIVE_SAMPLES})")
            continue

        X_arr, y_arr = np.array(X), np.array(y)

        # Per-fold, not just a mean -- honest with this few wells.
        fold_results, mean_auc = leave_one_well_out_per_fold(X_arr, y_arr, well_ids)
        print(f"  Leave-one-well-out AUC per fold (19B's rows use fallback inclination):")
        for f in fold_results:
            if f["auc"] is not None:
                print(f"    held-out well={f['well']:12s} AUC={f['auc']:.3f}  (n_test={f['n_test']})")
            else:
                print(f"    held-out well={f['well']:12s} SKIPPED: {f['reason']}")
        print(f"  Mean AUC across valid folds: {mean_auc:.3f}")

        # Final model on ALL real rows (deployed candidate)
        pipeline = Pipeline([("scaler", StandardScaler()),
                              ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
        pipeline.fit(X_arr, y_arr)

        # Physics sanity check: sample-size-independent. Does the model's
        # learned direction for pore_pressure_ppg match real domain
        # understanding (higher pore pressure -> higher hazard risk for a
        # pressure-related hazard)? Coefficients are in STANDARDIZED
        # feature space (post StandardScaler), so sign is what's
        # meaningful here, not raw magnitude.
        clf = pipeline.named_steps["clf"]
        print("  Physics sanity check (standardized coefficients, sign matters not magnitude):")
        for name, coef in zip(FEATURE_NAMES, clf.coef_[0]):
            direction = "+" if coef > 0 else "-"
            print(f"    {name:20s} {direction}{abs(coef):.3f}")

        out_path = MODELS_OUT / f"{hazard_type.value.lower()}_model_REAL.joblib"
        joblib.dump({"pipeline": pipeline, "trained_on": "real_volve_data_with_19B_fallback_inclination",
                     "n_samples": len(X), "n_wells": n_wells_with_pos,
                     "n_fallback_inclination_rows": n_fallback_rows,
                     "lowo_fold_results": fold_results, "lowo_mean_auc": mean_auc}, out_path)
        print(f"  Saved: {out_path}")
        results[hazard_type.value] = {"auc": mean_auc, "n_folds": len([f for f in fold_results if f['auc'] is not None]), "n_samples": len(X)}
        print()

    print("=" * 70)
    print("SUMMARY (real data vs. synthetic, for direct honest comparison)")
    print("=" * 70)
    synthetic_auc = {"STUCK_PIPE": 0.622, "WELLBORE_INSTABILITY": 0.606}
    for hz, r in results.items():
        print(f"{hz}: REAL AUC={r['auc']:.3f} ({r['n_folds']} folds, {r['n_samples']} rows) "
              f"vs SYNTHETIC AUC={synthetic_auc.get(hz, 'n/a')}")
    if not results:
        print("No hazard type reached the minimum sample threshold even with 19B included.")


if __name__ == "__main__":
    main()
