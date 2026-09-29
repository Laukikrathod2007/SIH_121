"""
ML Data Engineering Pipeline -- Feature Engineering Engine.

Implements Module 5 Sections 60-73:
Extracts engineered features across all domains:
- Flow features (delta flow, rolling statistics, slopes, duration)
- Pit features (slope, acceleration, gain/loss indicators)
- Pressure features (SPP, annular, margins, ECD, slopes)
- Torque features (mean, std, slope, spikes, oscillations)
- RPM features (bit vs surface difference, variance, oscillation)
- WOB & Hookload features (overpull, slopes)
- ROP features (break score, rolling trends)
- MSE features (z-score, baseline deviations)
- d-exponent features (trend, deviation)
- Hole cleaning features (cuttings concentration, transport margin)
- Module 4 geological and historical context
"""

from __future__ import annotations

import math
from typing import Dict, Any, List, Optional


class FeatureEngine:
    """Extracts multivariate physics, statistical, and geological features from telemetry window."""

    def __init__(self, short_window: int = 10, long_window: int = 30):
        self.short_window = short_window
        self.long_window = long_window

    def extract_features(
        self,
        history: List[Dict[str, Any]],
        historical_offset_events: Optional[Dict[str, int]] = None,
    ) -> Dict[str, float]:
        """
        Extracts complete feature vector from the trailing telemetry history window.
        Assumes history is sorted chronologically with current timestep at history[-1].
        """
        if not history:
            return {}

        current = history[-1]
        ch_curr = current.get("channels", {})
        dt = 1.0  # nominal 1s grid

        # Helper to extract trailing list of channel values
        def get_series(name: str, window: int) -> List[float]:
            win = history[-window:]
            return [float(r.get("channels", {}).get(name, 0.0)) for r in win]

        # 1. Flow Features
        flow_in_series = get_series("flow_in_lpm", self.short_window)
        flow_out_series = get_series("flow_out_lpm", self.short_window)
        delta_series = [o - i for o, i in zip(flow_out_series, flow_in_series)]

        delta_flow = delta_series[-1] if delta_series else 0.0
        abs_flow_imbalance = abs(delta_flow)
        mean_delta_flow = sum(delta_series) / max(1, len(delta_series))
        var_delta_flow = sum((x - mean_delta_flow) ** 2 for x in delta_series) / max(1, len(delta_series))
        std_delta_flow = math.sqrt(var_delta_flow)

        flow_out_slope = (flow_out_series[-1] - flow_out_series[0]) / max(1.0, len(flow_out_series) * dt) if len(flow_out_series) > 1 else 0.0
        flow_in_slope = (flow_in_series[-1] - flow_in_series[0]) / max(1.0, len(flow_in_series) * dt) if len(flow_in_series) > 1 else 0.0
        flow_imbalance_slope = flow_out_slope - flow_in_slope

        # Duration flow imbalance has persisted beyond 50 LPM
        imbalance_count = sum(1 for x in delta_series if abs(x) > 50.0)

        # 2. Pit Features
        pit_series = get_series("pit_volume_m3", self.short_window)
        pit_slope = (pit_series[-1] - pit_series[0]) / max(1.0, len(pit_series) * dt) if len(pit_series) > 1 else 0.0
        # Acceleration (change of slope)
        if len(pit_series) >= 6:
            mid = len(pit_series) // 2
            slope_first = (pit_series[mid] - pit_series[0]) / max(1.0, mid * dt)
            slope_second = (pit_series[-1] - pit_series[mid]) / max(1.0, (len(pit_series) - mid) * dt)
            pit_accel = slope_second - slope_first
        else:
            pit_accel = 0.0

        pit_gain = max(0.0, pit_series[-1] - pit_series[0]) if pit_series else 0.0
        pit_loss = max(0.0, pit_series[0] - pit_series[-1]) if pit_series else 0.0

        # 3. Pressure Features
        spp_series = get_series("standpipe_pressure_bar", self.short_window)
        spp_slope = (spp_series[-1] - spp_series[0]) / max(1.0, len(spp_series) * dt) if len(spp_series) > 1 else 0.0

        ann_series = get_series("annular_pressure_bar", self.short_window)
        ann_slope = (ann_series[-1] - ann_series[0]) / max(1.0, len(ann_series) * dt) if len(ann_series) > 1 else 0.0

        pp_margin_bar = float(ch_curr.get("pp_margin_bar", 0.0))
        fg_margin_bar = float(ch_curr.get("fg_margin_bar", 0.0))
        ecd_gcc = float(ch_curr.get("ecd_gcc", 1.20))
        bhp_bar = float(ch_curr.get("bhp_bar", 0.0))

        # 4. Torque Features
        t_series = get_series("torque_kn_m", self.short_window)
        t_mean = sum(t_series) / max(1, len(t_series))
        t_var = sum((x - t_mean) ** 2 for x in t_series) / max(1, len(t_series))
        t_std = math.sqrt(t_var)
        t_slope = (t_series[-1] - t_series[0]) / max(1.0, len(t_series) * dt) if len(t_series) > 1 else 0.0
        t_oscillation = (max(t_series) - min(t_series)) if t_series else 0.0
        t_spikes = sum(1 for x in t_series if (x - t_mean) > 2.0 * max(0.2, t_std))

        # 5. RPM Features
        rpm_series = get_series("rpm", self.short_window)
        bit_rpm_series = get_series("bit_rpm", self.short_window)
        rpm_mean = sum(rpm_series) / max(1, len(rpm_series))
        rpm_var = sum((x - rpm_mean) ** 2 for x in rpm_series) / max(1, len(rpm_series))
        rpm_std = math.sqrt(rpm_var)
        rpm_diff = ch_curr.get("rpm", 0.0) - ch_curr.get("bit_rpm", 0.0)
        rpm_oscillation = (max(bit_rpm_series) - min(bit_rpm_series)) if bit_rpm_series else 0.0
        stick_slip_index = float(ch_curr.get("stick_slip_index", 0.0))

        # 6. WOB & Hookload Features
        wob_series = get_series("wob_kn", self.short_window)
        wob_mean = sum(wob_series) / max(1, len(wob_series))
        wob_slope = (wob_series[-1] - wob_series[0]) / max(1.0, len(wob_series) * dt) if len(wob_series) > 1 else 0.0
        hl_series = get_series("hookload_kn", self.short_window)
        hl_slope = (hl_series[-1] - hl_series[0]) / max(1.0, len(hl_series) * dt) if len(hl_series) > 1 else 0.0
        overpull_kn = float(ch_curr.get("overpull_kn", 0.0))

        # 7. ROP Features
        rop_series = get_series("rop_m_hr", self.short_window)
        rop_mean = sum(rop_series) / max(1, len(rop_series))
        rop_slope = (rop_series[-1] - rop_series[0]) / max(1.0, len(rop_series) * dt) if len(rop_series) > 1 else 0.0
        rop_change_pct = ((rop_series[-1] - rop_mean) / max(1.0, rop_mean)) * 100.0 if rop_mean > 0.0 else 0.0
        # Drilling break: sudden positive jump in ROP (> 50% increase)
        rop_break_score = 1.0 if rop_change_pct > 50.0 else (0.5 if rop_change_pct > 25.0 else 0.0)

        # 8. MSE Features
        mse_series = get_series("mse_mpa", self.long_window)
        mse_mean = sum(mse_series) / max(1, len(mse_series))
        mse_var = sum((x - mse_mean) ** 2 for x in mse_series) / max(1, len(mse_series))
        mse_std = math.sqrt(mse_var)
        mse_zscore = (ch_curr.get("mse_mpa", 0.0) - mse_mean) / max(1.0, mse_std) if mse_std > 0.1 else 0.0

        # 9. d-exponent Features
        d_series = get_series("d_exponent", self.long_window)
        d_mean = sum(d_series) / max(1, len(d_series))
        d_deviation = ch_curr.get("d_exponent", 1.0) - d_mean
        d_slope = (d_series[-1] - d_series[0]) / max(1.0, len(d_series) * dt) if len(d_series) > 1 else 0.0

        # 10. Hole Cleaning Features
        cuttings_conc = float(ch_curr.get("cuttings_concentration", 0.0))

        # 11. Geological & Historical Features from Module 4
        geo = current.get("geology", {})
        formation_info = current.get("formation", {})
        formation_xi = formation_info.get("xi", 0.0) if isinstance(formation_info, dict) else 0.0
        xi = float(geo.get("xi", formation_xi))
        dist_top = float(geo.get("distance_to_top_m", 0.0))
        dist_base = float(geo.get("distance_to_base_m", 0.0))

        # Historical offset counts
        hist = historical_offset_events or {}
        hist_lc_count = float(hist.get("LOST_CIRCULATION", 0))
        hist_sp_count = float(hist.get("STUCK_PIPE", 0))
        hist_kick_count = float(hist.get("KICK", 0))

        # 12. Quality Features
        quality_info = current.get("quality", {})
        q_overall = float(quality_info.get("overall", 1.0)) if isinstance(quality_info, dict) else 1.0

        return {
            # Flow
            "delta_flow": round(delta_flow, 2),
            "abs_flow_imbalance": round(abs_flow_imbalance, 2),
            "mean_delta_flow": round(mean_delta_flow, 2),
            "std_delta_flow": round(std_delta_flow, 2),
            "flow_imbalance_slope": round(flow_imbalance_slope, 3),
            "flow_imbalance_duration_s": float(imbalance_count * dt),
            # Pit
            "pit_volume_m3": round(ch_curr.get("pit_volume_m3", 0.0), 2),
            "pit_slope": round(pit_slope, 4),
            "pit_accel": round(pit_accel, 4),
            "pit_gain": round(pit_gain, 3),
            "pit_loss": round(pit_loss, 3),
            # Pressure
            "standpipe_pressure_bar": round(ch_curr.get("standpipe_pressure_bar", 0.0), 1),
            "spp_slope": round(spp_slope, 3),
            "annular_pressure_bar": round(ch_curr.get("annular_pressure_bar", 0.0), 1),
            "ann_slope": round(ann_slope, 3),
            "bhp_bar": round(bhp_bar, 1),
            "ecd_gcc": round(ecd_gcc, 3),
            "pp_margin_bar": round(pp_margin_bar, 2),
            "fg_margin_bar": round(fg_margin_bar, 2),
            # Torque
            "torque_kn_m": round(ch_curr.get("torque_kn_m", 0.0), 2),
            "torque_mean": round(t_mean, 2),
            "torque_std": round(t_std, 3),
            "torque_slope": round(t_slope, 4),
            "torque_oscillation": round(t_oscillation, 2),
            "torque_spike_count": float(t_spikes),
            # RPM & Stick-slip
            "rpm": round(ch_curr.get("rpm", 0.0), 1),
            "bit_rpm": round(ch_curr.get("bit_rpm", 0.0), 1),
            "rpm_difference": round(rpm_diff, 1),
            "rpm_std": round(rpm_std, 2),
            "rpm_oscillation": round(rpm_oscillation, 1),
            "stick_slip_index": round(stick_slip_index, 3),
            # WOB & Hookload
            "wob_kn": round(ch_curr.get("wob_kn", 0.0), 1),
            "wob_mean": round(wob_mean, 1),
            "wob_slope": round(wob_slope, 3),
            "hookload_kn": round(ch_curr.get("hookload_kn", 0.0), 1),
            "hookload_slope": round(hl_slope, 3),
            "overpull_kn": round(overpull_kn, 2),
            # ROP
            "rop_m_hr": round(ch_curr.get("rop_m_hr", 0.0), 2),
            "rop_mean": round(rop_mean, 2),
            "rop_slope": round(rop_slope, 4),
            "rop_change_pct": round(rop_change_pct, 1),
            "rop_break_score": round(rop_break_score, 2),
            # MSE & d-exp
            "mse_mpa": round(ch_curr.get("mse_mpa", 0.0), 1),
            "mse_zscore": round(mse_zscore, 2),
            "d_exponent": round(ch_curr.get("d_exponent", 1.0), 3),
            "d_exponent_deviation": round(d_deviation, 3),
            "d_exponent_slope": round(d_slope, 4),
            # Hole Cleaning
            "cuttings_concentration": round(cuttings_conc, 4),
            # Geology & Offsets
            "xi": round(xi, 4),
            "distance_to_top_m": round(dist_top, 2),
            "distance_to_base_m": round(dist_base, 2),
            "historical_lc_count": hist_lc_count,
            "historical_sp_count": hist_sp_count,
            "historical_kick_count": hist_kick_count,
            # Quality
            "telemetry_quality": round(q_overall, 3),
        }
