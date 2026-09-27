"""
Module 5 Predictive Risk Analytics -- Supervised Hazard Classification (XGBoost).

Implements Part C & D:
Multiclass supervised hazard prediction covering:
0: NORMAL
1: LOST_CIRCULATION
2: STUCK_PIPE
3: KICK
4: TORQUE_DRAG
5: WASHOUT

Preprocessors (StandardScaler, Imputer) are strictly fitted on training wells only.
Never fit preprocessing on validation or test sets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.preprocessing import StandardScaler
import xgboost as xgb


HAZARD_TARGET_MAP = {
    "NORMAL": 0,
    "LOST_CIRCULATION": 1,
    "STUCK_PIPE": 2,
    "KICK": 3,
    "TORQUE_DRAG": 4,
    "WASHOUT": 5,
}

TARGET_HAZARD_MAP = {v: k for k, v in HAZARD_TARGET_MAP.items()}


SUPERVISED_FEATURE_NAMES = [
    # Flow
    "delta_flow", "abs_flow_imbalance", "mean_delta_flow", "std_delta_flow",
    "flow_imbalance_slope", "flow_imbalance_duration_s",
    # Pit
    "pit_volume_m3", "pit_slope", "pit_accel", "pit_gain", "pit_loss",
    # Pressure
    "standpipe_pressure_bar", "spp_slope", "annular_pressure_bar", "ann_slope",
    "bhp_bar", "ecd_gcc", "pp_margin_bar", "fg_margin_bar",
    # Torque
    "torque_kn_m", "torque_mean", "torque_std", "torque_slope",
    "torque_oscillation", "torque_spike_count",
    # RPM
    "rpm", "bit_rpm", "rpm_difference", "rpm_std", "rpm_oscillation", "stick_slip_index",
    # WOB & Hookload
    "wob_kn", "wob_mean", "wob_slope", "hookload_kn", "hookload_slope", "overpull_kn",
    # ROP
    "rop_m_hr", "rop_mean", "rop_slope", "rop_change_pct", "rop_break_score",
    # MSE & d-exp
    "mse_mpa", "mse_zscore", "d_exponent", "d_exponent_deviation", "d_exponent_slope",
    # Hole cleaning
    "cuttings_concentration",
    # Geology
    "xi", "distance_to_top_m", "distance_to_base_m",
    # History
    "historical_lc_count", "historical_sp_count", "historical_kick_count",
    # Quality
    "telemetry_quality",
]


class XGBoostHazardClassifier:
    """Supervised gradient boosted tree classifier for drilling hazard prediction."""

    def __init__(
        self,
        n_estimators: int = 120,
        max_depth: int = 5,
        learning_rate: float = 0.08,
        random_state: int = 42,
    ):
        self.feature_names = list(SUPERVISED_FEATURE_NAMES)
        self.scaler = StandardScaler()
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            objective="multi:softprob",
            num_class=len(HAZARD_TARGET_MAP),
            eval_metric="mlogloss",
            tree_method="hist",
            subsample=0.85,
            colsample_bytree=0.85,
        )
        self._is_fitted = False
        self._feature_importances: Dict[str, float] = {}

    def _prepare_matrix(self, features_list: List[Dict[str, float]]) -> np.ndarray:
        matrix = []
        for f in features_list:
            row = []
            for name in self.feature_names:
                v = f.get(name, 0.0)
                row.append(float(v) if v is not None and not np.isnan(v) else 0.0)
            matrix.append(row)
        arr = np.array(matrix, dtype=np.float32)
        # Clean any remaining NaNs
        arr = np.nan_to_num(arr, nan=0.0)
        return arr

    def fit(
        self,
        train_features: List[Dict[str, float]],
        train_labels: List[str],
        val_features: Optional[List[Dict[str, float]]] = None,
        val_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fits scaler and XGBoost model strictly on training data.
        Never touches validation or test data during preprocessing fit!
        """
        if not train_features or not train_labels:
            raise ValueError("Training dataset cannot be empty")

        X_train_raw = self._prepare_matrix(train_features)
        y_train = np.array([HAZARD_TARGET_MAP.get(lbl, 0) for lbl in train_labels], dtype=np.int32)

        # FIT SCALER ON TRAINING DATA ONLY
        X_train = self.scaler.fit_transform(X_train_raw)

        eval_set = [(X_train, y_train)]
        if val_features and val_labels:
            X_val_raw = self._prepare_matrix(val_features)
            X_val = self.scaler.transform(X_val_raw)
            y_val = np.array([HAZARD_TARGET_MAP.get(lbl, 0) for lbl in val_labels], dtype=np.int32)
            eval_set.append((X_val, y_val))

        self.model.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            verbose=False,
        )

        self._is_fitted = True

        # Extract feature importances
        raw_imp = self.model.feature_importances_
        self._feature_importances = {
            name: round(float(imp), 4)
            for name, imp in sorted(zip(self.feature_names, raw_imp), key=lambda x: x[1], reverse=True)
        }

        return {
            "is_fitted": True,
            "train_samples": len(X_train),
            "top_features": list(self._feature_importances.items())[:10],
        }

    def predict_probabilities(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Infers probabilistic risk outputs across all 6 target classes.
        """
        if not self._is_fitted:
            # Baseline uniform fallback
            return {hazard: (1.0 if hazard == "NORMAL" else 0.0) for hazard in HAZARD_TARGET_MAP}

        X_raw = self._prepare_matrix([features])
        X = self.scaler.transform(X_raw)
        probs = self.model.predict_proba(X)[0]

        result = {}
        for target_idx, prob in enumerate(probs):
            hazard_name = TARGET_HAZARD_MAP.get(target_idx, f"CLASS_{target_idx}")
            result[hazard_name] = round(float(prob), 4)

        return result

    def get_feature_importances(self) -> Dict[str, float]:
        return self._feature_importances

    def save(self, filepath: Any) -> None:
        """Serializes fitted scaler and XGBoost classifier to disk using atomic write."""
        import joblib
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp_p = p.with_suffix(".tmp")
        data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "feature_importances": self._feature_importances,
            "is_fitted": self._is_fitted,
        }
        joblib.dump(data, tmp_p)
        tmp_p.replace(p)

    def load(self, filepath: Any) -> bool:
        """Loads serialized model and scaler from disk."""
        import joblib
        p = Path(filepath)
        if not p.exists():
            return False
        try:
            data = joblib.load(p)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.feature_names = data.get("feature_names", self.feature_names)
            self._feature_importances = data.get("feature_importances", {})
            self._is_fitted = data.get("is_fitted", True)
            return True
        except Exception:
            return False
