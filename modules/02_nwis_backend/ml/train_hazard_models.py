"""
NWIS Module 02 — Hazard Prediction Model Training

Trains one binary LogisticRegression classifier per hazard type that has
enough historical examples to make training statistically meaningful
(see feature_engineering.MIN_POSITIVE_SAMPLES). Hazard types below that
threshold are left on the physics-heuristic fallback in
engines/risk_corridor_engine.py — deliberately, not silently.

HONEST FRAMING FOR WHOEVER READS THIS: this synthetic testbed has 39 total
events across 4 hazard types (14 stuck pipe, 12 wellbore instability, 10 kick,
3 mud loss — torque spike and cementing failure have zero examples). That is
a genuinely small dataset for machine learning. This training pipeline is
real — real features, real cross-validation, real serialized models used at
real inference time — but the resulting models' predictive validity is
inherently limited by how little labeled data exists. The point of building
this now is to have a working, retrainable pipeline ready for when real
historical Oil India event data becomes available (see PROBLEM_STATEMENT.md's
"Relevant Data Availability" section) — not to claim clinical-grade accuracy
from 10-14 examples.

Usage:
    python -m ml.train_hazard_models
    (or: python run_server.py --train-ml)
"""

from __future__ import annotations
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).parent.parent
if __name__ == "__main__":
    # Only when run directly as a script: make the canonical `app` package
    # (Backend/app/modules/nwis -> this module) importable. When this file is
    # imported as app.modules.nwis.ml.train_hazard_models, `app` is already
    # importable and nothing here touches sys.path.
    sys.path.insert(0, str(MODULE_ROOT.parents[1] / "Backend"))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
import joblib
from loguru import logger

from app.modules.nwis.data_store import NWISDataStore
from app.modules.nwis.models.schemas import HazardType
from app.modules.nwis.ml.feature_engineering import build_training_dataset, MIN_POSITIVE_SAMPLES, FEATURE_NAMES

MODELS_DIR = MODULE_ROOT / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _leave_one_well_out_auc(X: np.ndarray, y: np.ndarray, well_ids: list[str]) -> tuple[float, int]:
    """
    Honest cross-validated ROC-AUC using leave-one-WELL-out (not leave-one-row
    or ordinary k-fold): every row from one well is held out as the test set
    for one fold, since rows from the same well share the same formations and
    trajectory and would otherwise leak information between train/test.
    Returns (mean_auc, n_folds_evaluated) — folds where the held-out well has
    only one class present are skipped (AUC is undefined for a single class).
    """
    unique_wells = sorted(set(well_ids))
    aucs = []
    for held_out in unique_wells:
        test_mask = np.array([w == held_out for w in well_ids])
        train_mask = ~test_mask
        y_test = y[test_mask]
        if len(set(y_test.tolist())) < 2 or train_mask.sum() < 4:
            continue  # can't score AUC on a single-class fold; skip it honestly rather than fudge it
        model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
        model.fit(X[train_mask], y[train_mask])
        try:
            proba = model.predict_proba(X[test_mask])[:, 1]
            aucs.append(roc_auc_score(y_test, proba))
        except ValueError:
            continue
    return (float(np.mean(aucs)) if aucs else float("nan"), len(aucs))


def train_all_models() -> dict:
    """Trains and saves one model per eligible hazard type. Returns a report
    dict summarizing what was trained, what was skipped, and why."""
    store = NWISDataStore()
    store.load()

    report = {"trained": {}, "skipped": {}}

    for hazard in HazardType:
        X_list, y_list, well_ids = build_training_dataset(
            hazard_type=hazard,
            all_wells=store.all_wells,
            all_trajectories=store.all_trajectories,
            all_formation_tops=store.formation_tops_by_well,
            all_events=store.events_by_well,
        )
        n_positive = sum(y_list)
        if n_positive < MIN_POSITIVE_SAMPLES:
            reason = f"only {n_positive} historical example(s), need >= {MIN_POSITIVE_SAMPLES}"
            report["skipped"][hazard.value] = reason
            logger.warning(f"[{hazard.value}] SKIPPED — {reason}. Staying on physics-heuristic fallback.")
            continue

        X = np.array(X_list)
        y = np.array(y_list)

        mean_auc, n_folds = _leave_one_well_out_auc(X, y, well_ids)

        # Final model trained on ALL available data (the CV above is purely
        # for honest reporting of expected real-world performance, not the
        # model that gets served)
        final_model = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(class_weight="balanced", max_iter=1000))])
        final_model.fit(X, y)

        model_path = MODELS_DIR / f"{hazard.value.lower()}_model.joblib"
        joblib.dump({"model": final_model, "feature_names": FEATURE_NAMES, "n_positive": n_positive, "n_total": len(y)}, model_path)

        report["trained"][hazard.value] = {
            "n_positive": n_positive,
            "n_total": len(y),
            "leave_one_well_out_auc": round(mean_auc, 3) if mean_auc == mean_auc else None,  # NaN check
            "cv_folds_evaluated": n_folds,
            "saved_to": str(model_path),
        }
        auc_str = f"{mean_auc:.3f}" if mean_auc == mean_auc else "undefined (too few folds)"
        logger.success(
            f"[{hazard.value}] Trained on {n_positive} positive / {len(y)} total samples. "
            f"Leave-one-well-out AUC: {auc_str} ({n_folds} well-folds evaluated)."
        )

    return report


def main() -> dict:
    """Trains all models and prints a human-readable report. Shared by both
    `python -m ml.train_hazard_models` and `python run_server.py --train-ml`
    so the two entry points can't drift into printing different summaries."""
    print("\n" + "=" * 70)
    print("  NWIS Module 02 — Hazard Prediction Model Training")
    print("  Synthetic testbed: 39 events across 4 hazard types (small-N — see")
    print("  module docstring for what this honestly can and can't achieve)")
    print("=" * 70 + "\n")

    report = train_all_models()

    print("\n" + "-" * 70)
    print("  SUMMARY")
    print("-" * 70)
    for hazard, info in report["trained"].items():
        auc = info["leave_one_well_out_auc"]
        auc_str = f"{auc:.3f}" if auc is not None else "undefined"
        print(f"  [TRAINED]  {hazard:22s} AUC={auc_str}  ({info['n_positive']}/{info['n_total']} pos/total, {info['cv_folds_evaluated']} folds)")
    for hazard, reason in report["skipped"].items():
        print(f"  [SKIPPED]  {hazard:22s} {reason}")
    print("-" * 70)
    print(f"  Models saved to: {MODELS_DIR}")
    print("=" * 70 + "\n")
    return report


if __name__ == "__main__":
    main()
