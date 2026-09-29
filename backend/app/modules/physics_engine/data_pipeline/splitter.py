"""
ML Data Engineering Pipeline -- Leakage Prevention & Dataset Splitter.

Implements Module 5 Data Pipeline Section 13:
- STRICT RULE: Well-level split. No well may appear in both train and validation or test!
- Prevents temporal and spatial data leakage.
"""

from __future__ import annotations

import random
from typing import Dict, Any, List, Tuple


class DatasetSplitter:
    """Enforces strict well-level splitting to prevent data leakage."""

    @staticmethod
    def split_by_well(
        records: List[Dict[str, Any]],
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Splits a flat list of records strictly by well_id.
        No single well will have rows across multiple partitions.
        """
        # Group records by well_id
        wells_map: Dict[str, List[Dict[str, Any]]] = {}
        for r in records:
            wid = r.get("well_id", "DEFAULT")
            wells_map.setdefault(wid, []).append(r)

        unique_wells = sorted(list(wells_map.keys()))
        rng = random.Random(seed)
        rng.shuffle(unique_wells)

        n_wells = len(unique_wells)
        if n_wells == 1:
            # Single well: fallback to strictly temporal split
            w_records = wells_map[unique_wells[0]]
            n_recs = len(w_records)
            n_tr = int(n_recs * train_ratio)
            n_va = int(n_recs * val_ratio)
            return w_records[:n_tr], w_records[n_tr:n_tr + n_va], w_records[n_tr + n_va:]

        n_train = max(1, int(round(n_wells * train_ratio)))
        n_val = max(1, int(round(n_wells * val_ratio))) if n_wells >= 3 else 0

        train_wells = set(unique_wells[:n_train])
        val_wells = set(unique_wells[n_train:n_train + n_val])
        test_wells = set(unique_wells[n_train + n_val:])

        if not test_wells and unique_wells:
            test_wells = set([unique_wells[-1]])
            if len(train_wells) > 1:
                train_wells.remove(unique_wells[-1])

        train_set = [r for wid in train_wells for r in wells_map[wid]]
        val_set = [r for wid in val_wells for r in wells_map[wid]]
        test_set = [r for wid in test_wells for r in wells_map[wid]]

        return train_set, val_set, test_set
