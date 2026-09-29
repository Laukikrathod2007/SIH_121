"""
ML Data Engineering Pipeline -- Multi-Horizon Label Generator.

Implements Module 5 Data Pipeline Section 12:
- Generates hazard-specific event phase labels:
  NORMAL, PRE_EVENT, EVENT, RECOVERY.
- Generates multi-horizon binary targets:
  Time horizons: 5 min (300s), 10 min (600s), 20 min (1200s), 30 min (1800s).
  Depth horizons: 10m, 20m, 50m, 100m.
- Strictly causality-preserving (no temporal leakage during feature extraction).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from data_pipeline.models import MultiHorizonLabels, EventPhase


class HazardLabeler:
    """Assigns multi-horizon predictive hazard targets based on simulation ground truth."""

    def __init__(self):
        pass

    def label_sequence(
        self,
        records: List[Dict[str, Any]],
        event_type: Optional[str] = None,
        event_start_time_s: Optional[float] = None,
        event_end_time_s: Optional[float] = None,
        event_start_md_m: Optional[float] = None,
    ) -> List[MultiHorizonLabels]:
        """
        Labels an entire simulation sequence with multi-horizon predictive targets.
        """
        labels: List[MultiHorizonLabels] = []

        for r in records:
            t = float(r.get("simulation_time_s", 0.0))
            md = float(r.get("depth", {}).get("md_m", 0.0))

            lbl = MultiHorizonLabels(
                active_hazard=event_type,
            )

            if event_start_time_s is None or event_type is None:
                # Completely normal sequence
                lbl.event_phase = EventPhase.NORMAL
                labels.append(lbl)
                continue

            # Determine Event Phase
            if t < (event_start_time_s - 600.0):
                lbl.event_phase = EventPhase.NORMAL
            elif (event_start_time_s - 600.0) <= t < event_start_time_s:
                lbl.event_phase = EventPhase.PRE_EVENT
            elif event_start_time_s <= t <= (event_end_time_s or (event_start_time_s + 600.0)):
                lbl.event_phase = EventPhase.EVENT
                lbl.severity = 1.0
            else:
                lbl.event_phase = EventPhase.RECOVERY

            # Time horizon targets (Will event begin within X seconds?)
            time_to_event = event_start_time_s - t
            if 0.0 <= time_to_event <= 300.0:
                lbl.hazard_5m_ahead = True
            if 0.0 <= time_to_event <= 600.0:
                lbl.hazard_10m_ahead = True
            if 0.0 <= time_to_event <= 1200.0:
                lbl.hazard_20m_ahead = True
            if 0.0 <= time_to_event <= 1800.0:
                lbl.hazard_30m_ahead = True

            # Depth horizon targets (Will event occur within X meters ahead?)
            if event_start_md_m is not None:
                dist_to_event = event_start_md_m - md
                if 0.0 <= dist_to_event <= 10.0:
                    lbl.hazard_10m_depth_ahead = True
                if 0.0 <= dist_to_event <= 20.0:
                    lbl.hazard_20m_depth_ahead = True
                if 0.0 <= dist_to_event <= 50.0:
                    lbl.hazard_50m_depth_ahead = True
                if 0.0 <= dist_to_event <= 100.0:
                    lbl.hazard_100m_depth_ahead = True

            labels.append(lbl)

        return labels
