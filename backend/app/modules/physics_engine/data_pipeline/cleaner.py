"""
ML Data Engineering Pipeline -- Cleaning, Standardization & Outliers.

Implements Module 5 Data Pipeline Sections 5, 7, 8, 9, 56-57:
- Canonical unit standardization and bidirectional conversions.
- Missing data imputation with short-gap interpolation, forward-fill, and indicator tracking:
  is_imputed, imputation_method.
- Layered outlier handling preserving raw spikes:
  raw_value, clean_value, outlier_flag.
"""

from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple


class UnitStandardizer:
    """Canonical unit converter for oilfield <-> SI standardization."""

    @staticmethod
    def ft_to_m(val: float) -> float:
        return val * 0.3048

    @staticmethod
    def m_to_ft(val: float) -> float:
        return val / 0.3048

    @staticmethod
    def psi_to_bar(val: float) -> float:
        return val * 0.0689476

    @staticmethod
    def bar_to_psi(val: float) -> float:
        return val / 0.0689476

    @staticmethod
    def gpm_to_lpm(val: float) -> float:
        return val * 3.78541

    @staticmethod
    def lpm_to_gpm(val: float) -> float:
        return val / 3.78541

    @staticmethod
    def ppg_to_gcc(val: float) -> float:
        return val * 0.119826

    @staticmethod
    def gcc_to_ppg(val: float) -> float:
        return val / 0.119826

    @staticmethod
    def klbf_to_kn(val: float) -> float:
        return val * 4.44822

    @staticmethod
    def kn_to_klbf(val: float) -> float:
        return val / 4.44822


class TelemetryCleaner:
    """Cleans telemetry time series, imputes short gaps, and identifies outliers."""

    def __init__(self, max_interp_gap: int = 3, max_ffill_gap: int = 10, outlier_z_thresh: float = 3.5):
        self.max_interp_gap = max_interp_gap
        self.max_ffill_gap = max_ffill_gap
        self.outlier_z_thresh = outlier_z_thresh

    def impute_missing(
        self,
        time_series: List[Dict[str, Any]],
        channel: str,
    ) -> List[Tuple[float, bool, str]]:
        """
        Imputes missing values for a given channel in a chronological record list.
        
        Returns list of (clean_val, is_imputed, imputation_method).
        """
        values: List[Optional[float]] = []
        for r in time_series:
            val = r.get("channels", {}).get(channel)
            values.append(float(val) if val is not None else None)

        n = len(values)
        results: List[Tuple[float, bool, str]] = []

        for i in range(n):
            if values[i] is not None:
                results.append((values[i], False, "none"))
                continue

            # Gap detected at index i: find length of missing gap
            gap_start = i
            while i < n and values[i] is None:
                i += 1
            gap_end = i
            gap_len = gap_end - gap_start

            # Left and right boundary values
            left_val = results[gap_start - 1][0] if gap_start > 0 else None
            right_val = values[gap_end] if gap_end < n else None

            for k in range(gap_start, gap_end):
                if gap_len <= self.max_interp_gap and left_val is not None and right_val is not None:
                    # Linear interpolation
                    frac = (k - gap_start + 1) / (gap_len + 1)
                    interp_val = left_val + frac * (right_val - left_val)
                    results.append((round(interp_val, 3), True, "linear_interp"))
                elif gap_len <= self.max_ffill_gap and left_val is not None:
                    # Forward fill
                    results.append((left_val, True, "forward_fill"))
                else:
                    # Too wide to impute safely -- preserve as zero/missing indicator
                    results.append((0.0, True, "unfilled_gap"))

        return results

    def detect_outliers_layered(
        self,
        values: List[float],
        window_size: int = 15,
    ) -> List[Tuple[float, float, bool]]:
        """
        Layered outlier detection:
        Returns list of (raw_value, clean_value, outlier_flag).
        
        Preserves raw values so diagnostic hazard spikes are not erased.
        """
        n = len(values)
        results: List[Tuple[float, float, bool]] = []

        for i in range(n):
            val = values[i]
            # Rolling window around i
            w_start = max(0, i - window_size // 2)
            w_end = min(n, i + window_size // 2 + 1)
            window = [values[j] for j in range(w_start, w_end) if j != i]

            if len(window) < 4:
                results.append((val, val, False))
                continue

            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std = math.sqrt(variance)

            if std > 1e-4:
                z_score = abs(val - mean) / std
            else:
                z_score = 999.0 if abs(val - mean) > 1e-3 else 0.0

            if z_score > self.outlier_z_thresh:
                # Flag outlier, but retain window median as clean_value
                sorted_w = sorted(window)
                median = sorted_w[len(sorted_w) // 2]
                results.append((val, median, True))
            else:
                results.append((val, val, False))

        return results
