"""
Module 5 Predictive Risk Analytics -- Statistical Anomaly Detection.

Implements Part B:
Unsupervised statistical anomaly detector using Isolation Forest trained
strictly on normal-operation drilling behavior.

Answers the question:
"Does this drilling state look abnormal?"
(Does NOT output hazard probability directly).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest


ANOMALY_FEATURE_NAMES = [
    "delta_flow",
    "abs_flow_imbalance",
    "pit_slope",
    "standpipe_pressure_bar",
    "spp_slope",
    "torque_kn_m",
    "torque_std",
    "torque_slope",
    "rpm",
    "rpm_std",
    "stick_slip_index",
    "wob_kn",
    "overpull_kn",
    "rop_m_hr",
    "rop_change_pct",
    "mse_mpa",
    "d_exponent",
    "cuttings_concentration",
]


class DrillingAnomalyDetector:
    """Isolation Forest anomaly detection on multivariate drilling telemetry features."""

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.feature_names = list(ANOMALY_FEATURE_NAMES)
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
        )
        self._is_fitted = False
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None

    def _extract_vector(self, features: Dict[str, float]) -> np.ndarray:
        vec = []
        for name in self.feature_names:
            val = features.get(name, 0.0)
            vec.append(float(val) if val is not None and not np.isnan(val) else 0.0)
        return np.array(vec, dtype=np.float32)

    def fit(self, normal_features_list: List[Dict[str, float]]) -> Dict[str, Any]:
        """Fits Isolation Forest on purely NORMAL drilling records."""
        if not normal_features_list:
            raise ValueError("Cannot fit anomaly detector with empty training data")

        matrix = np.array([self._extract_vector(f) for f in normal_features_list], dtype=np.float32)
        # Store mean & std for missing data normalization
        self._feature_means = np.nanmean(matrix, axis=0)
        self._feature_stds = np.nanstd(matrix, axis=0) + 1e-4

        # Replace any residual NaNs with mean
        inds = np.where(np.isnan(matrix))
        matrix[inds] = np.take(self._feature_means, inds[1])

        self.model.fit(matrix)
        self._is_fitted = True

        return {
            "is_fitted": True,
            "training_samples": len(normal_features_list),
            "feature_dim": len(self.feature_names),
        }

    def score(self, features: Dict[str, float]) -> Tuple[float, bool]:
        """
        Calculates continuous anomaly score [0.0 .. 1.0] and anomaly flag.
        Score near 1.0 = highly abnormal multidimensional state.
        Score near 0.0 = nominal normal drilling state.
        """
        if not self._is_fitted:
            # Fallback baseline heuristics if not yet fitted
            delta_flow = abs(features.get("delta_flow", 0.0))
            overpull = features.get("overpull_kn", 0.0)
            baseline_score = min(1.0, (delta_flow / 200.0) * 0.5 + (overpull / 60.0) * 0.5)
            return round(baseline_score, 3), baseline_score > 0.65

        vec = self._extract_vector(features).reshape(1, -1)
        # Handle missing values using fitted training means
        inds = np.where(np.isnan(vec))
        if self._feature_means is not None and len(inds[0]) > 0:
            vec[inds] = np.take(self._feature_means, inds[1])

        # IsolationForest decision_function outputs negative values for anomalies,
        # positive for normal inliers (range typically [-0.5 .. 0.5])
        raw_score = self.model.decision_function(vec)[0]
        # Invert and normalize to [0.0 .. 1.0]
        norm_score = max(0.0, min(1.0, 0.5 - raw_score * 2.0))
        is_anomaly = bool(norm_score > 0.65)

        return round(float(norm_score), 3), is_anomaly

    def evaluate_robustness(
        self,
        test_features_list: List[Dict[str, float]],
        labels: List[int],  # 0 = normal, 1 = anomalous
        noise_level: float = 0.05,
    ) -> Dict[str, float]:
        """
        Evaluates precision, recall, false alert rate, and noise robustness.
        """
        if not self._is_fitted:
            return {"status": "unfitted"}

        predictions = []
        for f in test_features_list:
            # Add synthetic noise perturbation to test robustness
            noisy_f = dict(f)
            for k in self.feature_names:
                noisy_f[k] = noisy_f.get(k, 0.0) * (1.0 + np.random.normal(0.0, noise_level))
            _, is_anom = self.score(noisy_f)
            predictions.append(1 if is_anom else 0)

        tp = sum(1 for p, y in zip(predictions, labels) if p == 1 and y == 1)
        fp = sum(1 for p, y in zip(predictions, labels) if p == 1 and y == 0)
        tn = sum(1 for p, y in zip(predictions, labels) if p == 0 and y == 0)
        fn = sum(1 for p, y in zip(predictions, labels) if p == 0 and y == 1)

        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = (2 * precision * recall) / max(1e-4, precision + recall)
        # False alerts per simulated hour (assuming 1s ticks: 3600 samples/hr)
        fa_rate_per_hour = (fp / max(1, len(labels))) * 3600.0

        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "false_alerts_per_hour": round(fa_rate_per_hour, 1),
            "noise_robustness_pct": round(precision * 100.0, 1),
        }

    def save(self, filepath: Any) -> None:
        """Serializes fitted anomaly detector to disk using atomic write."""
        import joblib
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp_p = p.with_suffix(".tmp")
        data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "feature_means": self._feature_means,
            "feature_stds": self._feature_stds,
            "contamination": self.contamination,
            "is_fitted": self._is_fitted,
        }
        joblib.dump(data, tmp_p)
        tmp_p.replace(p)

    def load(self, filepath: Any) -> bool:
        """Loads serialized anomaly detector from disk."""
        import joblib
        p = Path(filepath)
        if not p.exists():
            return False
        try:
            data = joblib.load(p)
            self.model = data["model"]
            self.feature_names = data.get("feature_names", self.feature_names)
            self._feature_means = data.get("feature_means")
            self._feature_stds = data.get("feature_stds")
            self.contamination = data.get("contamination", self.contamination)
            self._is_fitted = data.get("is_fitted", True)
            return True
        except Exception:
            return False
