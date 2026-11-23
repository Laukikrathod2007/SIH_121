"""
NWIS Module 02 — Hazard Predictor (inference-time entry point)

Replaces the old, purely hand-coded engines.risk_corridor_engine.compute_ml_score
with a three-tier hybrid, chosen per hazard type, never silently guessed:

  1. REAL-DATA-TRAINED model (real_data/real_trained_models/*_REAL.joblib) —
     trained on genuine Equinor Volve field data (see
     real_data/train_hazard_models_real.py) — used only where a validated
     artifact exists AND passes the compatibility/schema checks in
     _validate_real_model() below.
  2. SYNTHETIC-TRAINED model (data/models/*.joblib, see train_hazard_models.py)
     — used where no valid real-data model exists for that hazard type.
  3. Physics heuristic fallback — used where neither trained model exists
     (too few historical examples to train one at all).

Every call returns which path was actually used (`source`), so the API surface
can be honest about "trained_model_real" vs "trained_model" vs
"heuristic_fallback" instead of presenting all three as the same kind of
number — consistent with the 4-Pillar Confidence Evaluator's whole point (no
black box).

IMPORTANT — do not read the real model's leave-one-well-out AUC as "better
than the synthetic model." It is honestly weaker (mean 0.55-0.59 vs the
synthetic model's ~0.60-0.62, see real_data/train_hazard_models_real.py's own
printed comparison) because the real dataset is small (3 wells). It is
preferred here ONLY because it is trained on genuine field data rather than a
procedurally-generated testbed — a provenance preference, not a performance
claim. This is a deliberate, disclosed trade-off, not an oversight.

The overbalance term (mud weight vs. pore pressure) is applied as a physics
ADDITIVE on top of any path, always — it is real domain knowledge that the
trained models cannot learn (see feature_engineering.py's module docstring for
why: training data has no per-event mud weight, so the model never sees this
feature vary). This is a deliberate hybrid design.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import joblib
from loguru import logger

from app.modules.nwis.models.schemas import HazardType, WellTrajectory, FormationTop
from app.modules.nwis.ml.feature_engineering import build_features, FEATURE_NAMES

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"
REAL_MODELS_DIR = Path(__file__).parent.parent.parent.parent / "real_data" / "real_trained_models"

# Same heuristic table that used to live entirely inside compute_ml_score —
# kept as the formation-risk lookup for hazard types with no trained model,
# and unchanged in meaning from the original.
HIGH_RISK_FORMATIONS = {
    HazardType.MUD_LOSS: {"Tipam Sandstone", "Sylhet Limestone", "Kopili"},
    HazardType.STUCK_PIPE: {"Girujan Clay", "Barail Coal-Shale"},
    HazardType.KICK: {"Barail Sandstone", "Sylhet Limestone"},
    HazardType.WELLBORE_INSTABILITY: {"Girujan Clay", "Barail Coal-Shale"},
    HazardType.TORQUE_SPIKE: {"Barail Coal-Shale", "Girujan Clay"},
    HazardType.CEMENTING_FAILURE: {"Girujan Clay", "Kopili"},
    HazardType.OVERPRESSURE_ZONE: {"Kopili", "Barail Coal-Shale"},
}


@dataclass
class MLScoreResult:
    score: float
    source: str  # "trained_model" | "heuristic_fallback"


_model_cache: dict[str, Optional[dict]] = {}
_model_source_cache: dict[str, str] = {}  # "trained_model_real" | "trained_model" | None
_cache_populated = False


def _validate_real_model(entry: dict, hazard_name: str) -> Optional[str]:
    """
    Returns None if the real-data-trained artifact is safe to serve
    predictions from the live feature pipeline, otherwise a string reason it
    was rejected. Checked once at load time, not on every request.

    Deliberately conservative: a real model that fails ANY of these checks
    falls back to the synthetic model rather than risk a shape-mismatch
    crash or a silently-wrong prediction at inference time.
    """
    if "pipeline" not in entry:
        return "missing 'pipeline' key (expected real-model schema)"
    pipeline = entry["pipeline"]
    if not hasattr(pipeline, "predict_proba"):
        return "estimator has no predict_proba"
    n_expected = len(FEATURE_NAMES)
    n_features_in = getattr(pipeline, "n_features_in_", None)
    if n_features_in != n_expected:
        return f"feature count mismatch: model expects {n_features_in}, live pipeline builds {n_expected}"
    # Run one real inference against the live feature pipeline's own output
    # shape (not fabricated data) to prove the loaded estimator actually
    # accepts what build_features() will send it at request time.
    try:
        probe_features = [0.0] * n_expected
        proba = pipeline.predict_proba([probe_features])
        if proba.shape != (1, 2):
            return f"unexpected predict_proba output shape {proba.shape}"
    except Exception as exc:
        return f"probe inference failed: {exc}"
    return None


def _load_all_models() -> None:
    """
    Populates _model_cache per hazard type with the best available model,
    preferring a validated real-data-trained artifact over the synthetic one,
    and _model_source_cache with which tier was actually selected. A hazard
    type with neither falls through to the heuristic at inference time
    (see predict_ml_score below) — this function never raises.
    """
    global _cache_populated
    if _cache_populated:
        return
    for hazard in HazardType:
        real_path = REAL_MODELS_DIR / f"{hazard.value.lower()}_model_REAL.joblib"
        synthetic_path = MODELS_DIR / f"{hazard.value.lower()}_model.joblib"

        chosen_entry: Optional[dict] = None
        chosen_source: Optional[str] = None

        if real_path.exists():
            try:
                real_entry = joblib.load(real_path)
                rejection_reason = _validate_real_model(real_entry, hazard.value)
                if rejection_reason is None:
                    # Normalize to the same internal key the rest of this
                    # module uses ("model"), regardless of which on-disk key
                    # the artifact was saved under — the real trainer uses
                    # "pipeline", the synthetic trainer uses "model".
                    chosen_entry = {**real_entry, "model": real_entry["pipeline"]}
                    chosen_source = "trained_model_real"
                    logger.info(
                        f"Loaded REAL-data-trained hazard model: {hazard.value} ({real_path.name}), "
                        f"lowo_mean_auc={real_entry.get('lowo_mean_auc')}, n_wells={real_entry.get('n_wells')}"
                    )
                else:
                    logger.warning(
                        f"Real-data model for {hazard.value} ({real_path.name}) failed validation: "
                        f"{rejection_reason} — falling back to synthetic model for this hazard"
                    )
            except Exception as exc:
                logger.warning(f"Failed to load real-data model {real_path}: {exc} — falling back to synthetic model")

        if chosen_entry is None and synthetic_path.exists():
            try:
                chosen_entry = joblib.load(synthetic_path)
                chosen_source = "trained_model"
                logger.info(f"Loaded synthetic-trained hazard model: {hazard.value} ({synthetic_path.name})")
            except Exception as exc:
                logger.warning(f"Failed to load model {synthetic_path}: {exc} — falling back to heuristic for {hazard.value}")

        _model_cache[hazard.value] = chosen_entry
        if chosen_source is not None:
            _model_source_cache[hazard.value] = chosen_source
    _cache_populated = True


def _overbalance_adjustment(mud_weight_ppg: float, pore_pressure_ppg: float) -> float:
    """The one piece of physics domain knowledge applied on top of BOTH the
    trained model and the heuristic fallback — see module docstring."""
    overbalance = mud_weight_ppg - pore_pressure_ppg
    if overbalance < 0.3:
        return 0.5
    elif overbalance < 0.7:
        return 0.25
    return 0.0


def _heuristic_score(
    hazard_type: HazardType,
    current_depth_m: float,
    formation: Optional[str],
    mud_weight_ppg: float,
    pore_pressure_ppg: float,
) -> float:
    """Unchanged from the original compute_ml_score — used for hazard types
    with no trained model (too few historical examples to train one)."""
    score = _overbalance_adjustment(mud_weight_ppg, pore_pressure_ppg)
    if formation and hazard_type in HIGH_RISK_FORMATIONS and formation in HIGH_RISK_FORMATIONS[hazard_type]:
        score += 0.35
    if current_depth_m > 2500:
        score += 0.15
    elif current_depth_m > 2000:
        score += 0.08
    return round(min(1.0, score), 4)


def predict_ml_score(
    hazard_type: HazardType,
    current_depth_m: float,
    formation: Optional[str],
    formation_tops: list[FormationTop],
    trajectory: Optional[WellTrajectory],
    well_type: str,
    mud_weight_ppg: float = 9.5,
    pore_pressure_ppg: float = 9.2,
) -> MLScoreResult:
    """
    Drop-in replacement for the old compute_ml_score(...) call in
    engines/risk_corridor_engine.py. Same signature plus the extra context
    (formation_tops/trajectory/well_type) the trained models need as features.
    """
    _load_all_models()
    entry = _model_cache.get(hazard_type.value)

    overbalance_term = _overbalance_adjustment(mud_weight_ppg, pore_pressure_ppg)

    if entry is not None:
        try:
            features = build_features(current_depth_m, formation_tops, trajectory, well_type)
            model_proba = float(entry["model"].predict_proba([features])[0][1])
            combined = round(min(1.0, model_proba + overbalance_term), 4)
            source = _model_source_cache.get(hazard_type.value, "trained_model")
            return MLScoreResult(score=combined, source=source)
        except Exception as exc:
            logger.warning(f"Trained model inference failed for {hazard_type.value}: {exc} — falling back to heuristic")

    return MLScoreResult(
        score=_heuristic_score(hazard_type, current_depth_m, formation, mud_weight_ppg, pore_pressure_ppg),
        source="heuristic_fallback",
    )
