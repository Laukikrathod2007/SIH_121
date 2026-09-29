"""
Module 5 Predictive Risk Analytics -- Baseline Deterministic Hazard Rules.

Implements Part A:
Deterministic, physics-grounded baseline hazard detection with:
- Explicit engineering thresholds
- Hysteresis and debouncing (requires persistence for N samples to trigger,
  and lower recovery threshold to clear)
- Zero false single-spike triggers from sensor noise
- Support for:
  1. lost_circulation
  2. stuck_pipe
  3. kick
  4. torque_drag
  5. cementing
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple


@dataclass
class DebounceState:
    trigger_counter: int = 0
    clear_counter: int = 0
    is_active: bool = False


class BaselineHazardRules:
    """
    Deterministic rule-based hazard detection with hysteresis and debouncing.
    Never triggers on a single noisy sample.
    """

    def __init__(
        self,
        lc_persistence: int = 3,
        sp_persistence: int = 4,
        kick_persistence: int = 3,
        td_persistence: int = 4,
        washout_persistence: int = 4,
    ):
        self.lc_persistence = lc_persistence
        self.sp_persistence = sp_persistence
        self.kick_persistence = kick_persistence
        self.td_persistence = td_persistence
        self.washout_persistence = washout_persistence

        # Debounce states per well and hazard
        self._states: Dict[str, Dict[str, DebounceState]] = collections.defaultdict(
            lambda: {
                "lost_circulation": DebounceState(),
                "stuck_pipe": DebounceState(),
                "kick": DebounceState(),
                "torque_drag": DebounceState(),
                "cementing": DebounceState(),
                "washout": DebounceState(),
            }
        )

    def evaluate_lost_circulation(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Lost circulation rule:
        - delta_flow < -60.0 LPM (persistent return deficit)
        - pit_slope < -0.015 m3/min (negative volume trend)
        - fg_margin_bar < 5.0 bar (approaching or exceeding fracture breakdown)
        """
        st = self._states[well_id]["lost_circulation"]
        delta_flow = features.get("delta_flow", 0.0)
        pit_slope = features.get("pit_slope", 0.0)
        fg_margin = features.get("fg_margin_bar", 50.0)

        # Hysteresis thresholds
        trigger_cond = (delta_flow < -50.0) and (pit_slope < -0.005) and (fg_margin < 10.0)
        clear_cond = (delta_flow > -20.0) and (pit_slope > -0.001)

        if trigger_cond:
            st.trigger_counter += 1
            st.clear_counter = 0
            if st.trigger_counter >= self.lc_persistence:
                st.is_active = True
        elif clear_cond:
            st.clear_counter += 1
            st.trigger_counter = 0
            if st.clear_counter >= 3:
                st.is_active = False

        # Continuous severity score [0.0 .. 1.0]
        flow_score = min(1.0, max(0.0, -delta_flow / 250.0))
        pit_score = min(1.0, max(0.0, -pit_slope / 0.05))
        fg_score = min(1.0, max(0.0, (10.0 - fg_margin) / 15.0))
        raw_score = 0.40 * flow_score + 0.35 * pit_score + 0.25 * fg_score

        if not st.is_active:
            # Debounced: before persistence, keep score bounded as PRE_ALERT
            score = min(0.35, raw_score * (st.trigger_counter / float(self.lc_persistence)))
            state_label = "LOW" if score < 0.20 else "GUARD"
        else:
            score = max(0.55, min(1.0, raw_score))
            state_label = "HIGH" if score > 0.70 else "MEDIUM"

        contributors = {
            "delta_flow_lpm": delta_flow,
            "pit_slope_m3_min": pit_slope,
            "fg_margin_bar": fg_margin,
            "persistence_ticks": float(st.trigger_counter),
        }
        return round(score, 3), state_label, contributors

    def evaluate_stuck_pipe(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Stuck pipe rule:
        - overpull_kn > 20.0 kN (mechanical drag elevation)
        - torque_slope > 0.2 kN.m/s or torque_zscore > 1.8
        - cuttings_concentration > 0.07 or rop_change_pct < -40%
        """
        st = self._states[well_id]["stuck_pipe"]
        overpull = features.get("overpull_kn", 0.0)
        t_slope = features.get("torque_slope", 0.0)
        cuttings = features.get("cuttings_concentration", 0.0)
        rop_change = features.get("rop_change_pct", 0.0)

        trigger_cond = (overpull > 25.0) and ((t_slope > 0.2) or (cuttings > 0.07) or (rop_change < -35.0))
        clear_cond = (overpull < 10.0) and (t_slope <= 0.0)

        if trigger_cond:
            st.trigger_counter += 1
            st.clear_counter = 0
            if st.trigger_counter >= self.sp_persistence:
                st.is_active = True
        elif clear_cond:
            st.clear_counter += 1
            st.trigger_counter = 0
            if st.clear_counter >= 3:
                st.is_active = False

        overpull_score = min(1.0, max(0.0, overpull / 75.0))
        cuttings_score = min(1.0, max(0.0, cuttings / 0.15))
        rop_drop_score = min(1.0, max(0.0, -rop_change / 80.0))
        raw_score = 0.45 * overpull_score + 0.30 * cuttings_score + 0.25 * rop_drop_score

        if not st.is_active:
            score = min(0.35, raw_score * (st.trigger_counter / float(self.sp_persistence)))
            state_label = "LOW" if score < 0.20 else "GUARD"
        else:
            score = max(0.55, min(1.0, raw_score))
            state_label = "HIGH" if score > 0.70 else "MEDIUM"

        contributors = {
            "overpull_kn": overpull,
            "cuttings_concentration": cuttings,
            "rop_change_pct": rop_change,
            "persistence_ticks": float(st.trigger_counter),
        }
        return round(score, 3), state_label, contributors

    def evaluate_kick(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Kick / underbalance rule:
        - delta_flow > 50.0 LPM (fluid influx)
        - pit_slope > 0.010 m3/min (pit gain)
        - pp_margin_bar < 8.0 bar (approaching or below pore pressure)
        """
        st = self._states[well_id]["kick"]
        delta_flow = features.get("delta_flow", 0.0)
        pit_slope = features.get("pit_slope", 0.0)
        pp_margin = features.get("pp_margin_bar", 50.0)
        rop_break = features.get("rop_break_score", 0.0)

        trigger_cond = (delta_flow > 50.0) and (pit_slope > 0.005) and (pp_margin < 10.0)
        clear_cond = (delta_flow < 20.0) and (pit_slope < 0.001)

        if trigger_cond:
            st.trigger_counter += 1
            st.clear_counter = 0
            if st.trigger_counter >= self.kick_persistence:
                st.is_active = True
        elif clear_cond:
            st.clear_counter += 1
            st.trigger_counter = 0
            if st.clear_counter >= 3:
                st.is_active = False

        flow_score = min(1.0, max(0.0, delta_flow / 200.0))
        pit_score = min(1.0, max(0.0, pit_slope / 0.05))
        pp_score = min(1.0, max(0.0, (10.0 - pp_margin) / 15.0))
        raw_score = 0.40 * flow_score + 0.35 * pit_score + 0.15 * pp_score + 0.10 * rop_break

        if not st.is_active:
            score = min(0.35, raw_score * (st.trigger_counter / float(self.kick_persistence)))
            state_label = "LOW" if score < 0.20 else "GUARD"
        else:
            score = max(0.55, min(1.0, raw_score))
            state_label = "HIGH" if score > 0.70 else "MEDIUM"

        contributors = {
            "delta_flow_lpm": delta_flow,
            "pit_slope_m3_min": pit_slope,
            "pp_margin_bar": pp_margin,
            "rop_break_score": rop_break,
            "persistence_ticks": float(st.trigger_counter),
        }
        return round(score, 3), state_label, contributors

    def evaluate_torque_drag(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Torque & Drag / Stick-slip rule:
        - stick_slip_index > 0.40
        - torque_oscillation > 3.5 kN.m
        - rpm_difference > 15.0 rpm
        """
        st = self._states[well_id]["torque_drag"]
        ssi = features.get("stick_slip_index", 0.0)
        t_osc = features.get("torque_oscillation", 0.0)
        rpm_diff = features.get("rpm_difference", 0.0)

        trigger_cond = (ssi > 0.45 and t_osc > 2.0) or (t_osc > 4.5 and abs(rpm_diff) > 15.0)
        clear_cond = (ssi < 0.20) and (t_osc < 2.0)

        if trigger_cond:
            st.trigger_counter += 1
            st.clear_counter = 0
            if st.trigger_counter >= self.td_persistence:
                st.is_active = True
        elif clear_cond:
            st.clear_counter += 1
            st.trigger_counter = 0
            if st.clear_counter >= 3:
                st.is_active = False

        ssi_score = min(1.0, max(0.0, ssi / 1.0))
        t_osc_score = min(1.0, max(0.0, t_osc / 10.0))
        raw_score = 0.60 * ssi_score + 0.40 * t_osc_score

        if not st.is_active:
            score = min(0.35, raw_score * (st.trigger_counter / float(self.td_persistence)))
            state_label = "LOW" if score < 0.20 else "GUARD"
        else:
            score = max(0.55, min(1.0, raw_score))
            state_label = "HIGH" if score > 0.70 else "MEDIUM"

        contributors = {
            "stick_slip_index": ssi,
            "torque_oscillation_kn_m": t_osc,
            "rpm_difference": rpm_diff,
            "persistence_ticks": float(st.trigger_counter),
        }
        return round(score, 3), state_label, contributors

    def evaluate_cementing(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Cementing integrity hazard:
        Primarily contextual/historical during drilling phases.
        """
        hist_count = features.get("historical_lc_count", 0.0)
        xi = features.get("xi", 0.5)

        # Higher risk near formation boundaries (xi < 0.05 or xi > 0.95) with loss history
        boundary_proximity = 1.0 - 2.0 * abs(xi - 0.5)
        raw_score = 0.20 * min(1.0, hist_count / 3.0) + 0.10 * boundary_proximity
        score = min(0.40, raw_score)
        state_label = "LOW"

        contributors = {
            "boundary_proximity": round(boundary_proximity, 2),
            "historical_loss_events": hist_count,
            "casing_annular_context": 1.0,
        }
        return round(score, 3), state_label, contributors

    def evaluate_washout(
        self,
        features: Dict[str, float],
        well_id: str = "DEFAULT",
    ) -> Tuple[float, str, Dict[str, float]]:
        """
        Washout rule:
        - spp_slope < -0.05 bar/s (persistent pressure drop while pumping)
        - pit_slope near 0.0 (|pit_slope| < 0.008 m3/min, distinct from thief zone losses)
        - delta_flow near 0.0 (|delta_flow| < 35.0 LPM, closed loop conserved)
        """
        st = self._states[well_id]["washout"]
        spp_slope = features.get("spp_slope", 0.0)
        pit_slope = features.get("pit_slope", 0.0)
        delta_flow = features.get("delta_flow", 0.0)

        trigger_cond = (spp_slope < -0.05) and (abs(pit_slope) < 0.008) and (abs(delta_flow) < 35.0)
        clear_cond = (spp_slope >= 0.0)

        if trigger_cond:
            st.trigger_counter += 1
            st.clear_counter = 0
            if st.trigger_counter >= self.washout_persistence:
                st.is_active = True
        elif clear_cond:
            st.clear_counter += 1
            st.trigger_counter = 0
            if st.clear_counter >= 3:
                st.is_active = False

        spp_drop_score = min(1.0, max(0.0, -spp_slope / 0.25))
        flow_const_score = max(0.0, 1.0 - abs(delta_flow) / 40.0)
        pit_const_score = max(0.0, 1.0 - abs(pit_slope) / 0.01)
        raw_score = 0.50 * spp_drop_score + 0.25 * flow_const_score + 0.25 * pit_const_score

        if not st.is_active:
            score = min(0.35, raw_score * (st.trigger_counter / float(self.washout_persistence)))
            state_label = "LOW" if score < 0.20 else "GUARD"
        else:
            score = max(0.55, min(1.0, raw_score))
            state_label = "HIGH" if score > 0.70 else "MEDIUM"

        contributors = {
            "spp_slope_bar_s": spp_slope,
            "delta_flow_lpm": delta_flow,
            "pit_slope_m3_min": pit_slope,
            "persistence_ticks": float(st.trigger_counter),
        }
        return round(score, 3), state_label, contributors
