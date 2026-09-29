"""
NWIS Module 02 — Hazard Predictor (inference-time entry point)

Replaces the old, purely hand-coded engines.risk_corridor_engine.compute_ml_score
with a hybrid: a real trained model (see train_hazard_models.py) where enough
historical data exists to train one, and the original physics heuristic where
it doesn't — chosen per hazard type, never silently guessed.

Every call returns which path was actually used (`source`), so the API surface
can be honest about "trained model" vs "heuristic fallback" instead of
presenting both as the same kind of number — consistent with the 4-Pillar
Confidence Evaluator's whole point (no black box).

The overbalance term (mud weight vs. pore pressure) is applied as a physics
ADDITIVE on top of either path, always — it is real domain knowledge that the
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

from models.schemas import HazardType, WellTrajectory, FormationTop
from ml.feature_engineering import build_features

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"

# Same heuristic table that used to live entirely inside compute_ml_score —
# kept as the formation-risk lookup for hazard types with no trained model,
# and unchanged in meaning from the original.
HIGH_RISK_FORMATIONS = {
    HazardType.MUD_LOSS: {"Tipam Sandstone", "Sylhet Limestone", "Kopili"},
    HazardType.STUCK_PIPE: {"Girujan Clay", "Barail Coal-Shale"},
    HazardType.KICK: {"Barail Sandstone", "Sylhet Limestone"},
    HazardType.WELLBORE_INSTABILITY: {"Girujan Clay", "Barail Coal-Shale"},
    # Added in the PS 26121 gap-closure pass (logger Step 20/21). Kopili and
    # Barail Coal-Shale are already-established formation names in this
    # codebase (domain_rules.py) and are shale-dominant, undercompacted-prone
    # intervals in the Assam-Arakan basin -- the same general geological
    # reasoning (shale sequences retain pore fluid under compaction) as why
    # they already appear above for STUCK_PIPE/WELLBORE_INSTABILITY, not a
    # new or separately-sourced claim.
    HazardType.OVERPRESSURE_ZONE: {"Kopili", "Barail Coal-Shale"},
}


@dataclass
class MLScoreResult:
    score: float
    source: str  # "trained_model" | "heuristic_fallback"


_model_cache: dict[str, Optional[dict]] = {}
_cache_populated = False


def _load_all_models() -> None:
    global _cache_populated
    if _cache_populated:
        return
    for hazard in HazardType:
        path = MODELS_DIR / f"{hazard.value.lower()}_model.joblib"
        if path.exists():
            try:
                _model_cache[hazard.value] = joblib.load(path)
                logger.info(f"Loaded trained hazard model: {hazard.value} ({path.name})")
            except Exception as exc:
                logger.warning(f"Failed to load model {path}: {exc} — falling back to heuristic for {hazard.value}")
                _model_cache[hazard.value] = None
        else:
            _model_cache[hazard.value] = None
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
            return MLScoreResult(score=combined, source="trained_model")
        except Exception as exc:
            logger.warning(f"Trained model inference failed for {hazard_type.value}: {exc} — falling back to heuristic")

    return MLScoreResult(
        score=_heuristic_score(hazard_type, current_depth_m, formation, mud_weight_ppg, pore_pressure_ppg),
        source="heuristic_fallback",
    )
