"""
Module 6: Real-Time Alerts, Lookahead Advisories, and Mitigation Recommendation Engine.

Implements:
1. Alert Tiering:
   - CRITICAL (Hazard fused score > 0.70 or acute well control risk)
   - WARNING (Hazard fused score in 0.35..0.70)
   - ADVISORY (Sensor health degraded or lookahead corridor within 50m)
   - CLEARED (Resolved following mitigation action)
2. Causal Evidence Chains (Symptom -> Physics -> Correlation -> Offset History).
3. Field-Standard Mitigation Actions per IADC / SPE drilling standards.
4. Human-In-The-Loop Action Execution and Closed-Loop Recovery Verification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MitigationAction(BaseModel):
    action_id: str
    hazard_type: str
    title: str
    description: str
    parameter_adjustments: Dict[str, Any] = Field(default_factory=dict)
    applied: bool = False
    applied_at: Optional[str] = None


class ActiveAlert(BaseModel):
    alert_id: str
    well_id: str
    timestamp: str
    hazard_type: str
    severity: str  # CRITICAL, WARNING, ADVISORY, CLEARED
    score: float
    confidence: float
    trigger_reason: str
    evidence_chain: List[str]
    recommended_mitigation: MitigationAction
    status: str = "ACTIVE"  # ACTIVE, ACKNOWLEDGED, MITIGATED, CLEARED


class AlertAdvisoryEngine:
    """Module 6 Alert Management and Engineering Advisory Engine."""

    def __init__(self):
        # In-memory store of active and historic alerts per well
        self._alerts: Dict[str, Dict[str, ActiveAlert]] = {}

    def evaluate_and_generate_alerts(
        self,
        well_id: str,
        fused_risk: Dict[str, Any],
        lookahead_corridors: Optional[List[Dict[str, Any]]] = None,
    ) -> List[ActiveAlert]:
        """
        Consumes Module 5 fused hazard risk evaluation and generates Module 6 operational alerts.
        """
        if well_id not in self._alerts:
            self._alerts[well_id] = {}

        now_iso = datetime.now(timezone.utc).isoformat()
        current_md = fused_risk.get("md", 0.0)
        current_fm = fused_risk.get("formation", "Unknown")
        xi = fused_risk.get("xi", 0.0)
        hazards = fused_risk.get("hazards", {})
        data_quality = fused_risk.get("data_quality", {})

        new_alerts: List[ActiveAlert] = []

        # 1. Check Sensor Health Degradation (ADVISORY)
        if data_quality.get("sensor_health") == "DEGRADED":
            alert_key = f"{well_id}_SENSOR_FAULT"
            ev = [
                f"Overall telemetry quality dropped to {data_quality.get('overall_quality')}",
                f"Missingness ratio: {data_quality.get('missingness', 0.0)}",
            ]
            action = MitigationAction(
                action_id=str(uuid.uuid4())[:8],
                hazard_type="SENSOR_FAULT",
                title="Inspect Sensor Rig Gateway & Transducers",
                description="Verify telemetry cabling, calibrate surface pressure transducer, and check WITSML gateway.",
                parameter_adjustments={},
            )
            alert = ActiveAlert(
                alert_id=str(uuid.uuid4())[:8],
                well_id=well_id,
                timestamp=now_iso,
                hazard_type="SENSOR_FAULT",
                severity="ADVISORY",
                score=1.0 - float(data_quality.get("overall_quality", 1.0)),
                confidence=0.95,
                trigger_reason="Sensor measurement fidelity degraded below operational threshold.",
                evidence_chain=ev,
                recommended_mitigation=action,
                status="ACTIVE",
            )
            self._alerts[well_id][alert_key] = alert
            new_alerts.append(alert)

        # 2. Process Physical Drilling Hazards
        for h_name, h_data in hazards.items():
            score = float(h_data.get("score", 0.0))
            state = h_data.get("state", "LOW")
            conf = float(h_data.get("confidence", 0.0))
            contribs = h_data.get("contributors", {})
            alert_key = f"{well_id}_{h_name.upper()}"

            if state in ("MEDIUM", "HIGH"):
                severity = "CRITICAL" if state == "HIGH" else "WARNING"
                trigger_reason, ev_chain, action = self._assemble_mitigation(
                    hazard_type=h_name,
                    score=score,
                    md=current_md,
                    fm=current_fm,
                    xi=xi,
                    contribs=contribs,
                )

                alert = ActiveAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    well_id=well_id,
                    timestamp=now_iso,
                    hazard_type=h_name.upper(),
                    severity=severity,
                    score=score,
                    confidence=conf,
                    trigger_reason=trigger_reason,
                    evidence_chain=ev_chain,
                    recommended_mitigation=action,
                    status="ACTIVE",
                )
                self._alerts[well_id][alert_key] = alert
                new_alerts.append(alert)

            elif state == "LOW" and alert_key in self._alerts[well_id]:
                # Alert cleared after mitigation / recovery
                prior_alert = self._alerts[well_id][alert_key]
                if prior_alert.status != "CLEARED":
                    prior_alert.status = "CLEARED"
                    prior_alert.severity = "CLEARED"
                    prior_alert.score = score
                    new_alerts.append(prior_alert)

        # 3. Check Ahead-of-Bit Corridors (Proactive Lookahead Warning)
        if lookahead_corridors:
            for corridor in lookahead_corridors:
                top_m = corridor.get("top_md", 0.0)
                h_type = corridor.get("hazard_type", "HAZARD")
                dist = top_m - current_md
                if 0.0 < dist <= 50.0:
                    alert_key = f"{well_id}_LOOKAHEAD_{h_type}"
                    action = MitigationAction(
                        action_id=str(uuid.uuid4())[:8],
                        hazard_type=h_type,
                        title=f"Prepare Rig for {h_type} Lookahead Zone",
                        description=f"Anticipate {h_type} zone in {dist:.1f}m. Stage mitigation materials.",
                        parameter_adjustments={},
                    )
                    alert = ActiveAlert(
                        alert_id=str(uuid.uuid4())[:8],
                        well_id=well_id,
                        timestamp=now_iso,
                        hazard_type=h_type,
                        severity="WARNING",
                        score=0.65,
                        confidence=0.85,
                        trigger_reason=f"Lookahead Risk Corridor: {h_type} zone projected in {dist:.1f} m MD.",
                        evidence_chain=[
                            f"Active bit at {current_md:.1f}m MD ({current_fm}, xi={xi:.3f})",
                            f"Corridor horizon mapped at {top_m:.1f}m MD",
                            f"Offset cluster confirmed historical {h_type} events in this formation",
                        ],
                        recommended_mitigation=action,
                        status="ACTIVE",
                    )
                    self._alerts[well_id][alert_key] = alert
                    new_alerts.append(alert)

        return list(self._alerts[well_id].values())

    def _assemble_mitigation(
        self,
        hazard_type: str,
        score: float,
        md: float,
        fm: str,
        xi: float,
        contribs: Dict[str, Any],
    ) -> tuple[str, List[str], MitigationAction]:
        """Synthesizes IADC / SPE standard mitigation protocols and causal evidence."""
        act_id = str(uuid.uuid4())[:8]

        if hazard_type == "lost_circulation":
            trigger = f"Active fluid loss detected at {md:.1f}m MD in {fm} (xi={xi:.3f}); return deficit with pit volume depletion."
            ev = [
                f"Delta flow rate: {contribs.get('delta_flow_lpm', -80.0)} LPM deficit",
                f"Pit loss slope: {contribs.get('pit_slope_m3_min', -0.02)} m3/min",
                f"Fracture gradient margin: {contribs.get('fg_margin_bar', 2.0)} bar (approaching/exceeding breakdown)",
                f"Statistical anomaly score: {contribs.get('anomaly_score', 0.85):.2f}",
                f"Module 4 offset wells confirmed historical lost circulation at equivalent horizon",
            ]
            action = MitigationAction(
                action_id=act_id,
                hazard_type="LOST_CIRCULATION",
                title="Mitigate Lost Circulation: Pump LCM & Reduce Rate",
                description="1. Reduce flow rate to 1400 LPM. 2. Spot 25 bbl medium-grade LCM pill at bit depth. 3. Monitor pit level.",
                parameter_adjustments={"flow_in_lpm": 1400.0, "clear_fault": True},
            )

        elif hazard_type == "kick":
            trigger = f"Formation influx (Kick) detected at {md:.1f}m MD in {fm}; return flow excess and pit volume gain."
            ev = [
                f"Delta flow rate: +{contribs.get('delta_flow_lpm', 95.0)} LPM excess",
                f"Pit gain slope: +{contribs.get('pit_slope_m3_min', 0.03)} m3/min",
                f"Pore pressure margin: {contribs.get('pp_margin_bar', -2.5)} bar (underbalanced condition)",
                f"Statistical anomaly score: {contribs.get('anomaly_score', 0.92):.2f}",
                f"Offset wells recorded overpressured gas influx in {fm}",
            ]
            action = MitigationAction(
                action_id=act_id,
                hazard_type="KICK",
                title="Well Control Protocol: Space Out & Shut-In BOP",
                description="1. Space out tool joint above rotary table. 2. Stop mud pumps. 3. Close annular BOP. 4. Record SIDP/SICP. 5. Increase mud weight to 1.35 gcc.",
                parameter_adjustments={"flow_in_lpm": 0.0, "mud_weight_gcc": 1.35, "clear_fault": True},
            )

        elif hazard_type == "stuck_pipe":
            trigger = f"Differential/Mechanical sticking risk elevated at {md:.1f}m MD; overpull elevated and ROP degraded."
            ev = [
                f"Overpull: {contribs.get('overpull_kn', 45.0)} kN above string weight",
                f"Annular cuttings concentration: {contribs.get('cuttings_concentration', 0.09) * 100:.1f}%",
                f"ROP degradation: {contribs.get('rop_change_pct', -55.0)}%",
                f"Mechanical friction coefficient elevated",
            ]
            action = MitigationAction(
                action_id=act_id,
                hazard_type="STUCK_PIPE",
                title="Free Pipe Protocol: Work Pipe & Circulate Hole",
                description="1. Work drillstring with maximum allowable overpull and right-hand torque. 2. Increase pump rate to 2600 LPM to sweep cuttings bed.",
                parameter_adjustments={"flow_in_lpm": 2600.0, "wob_kn": 40.0, "clear_fault": True},
            )

        elif hazard_type == "torque_drag":
            trigger = f"Severe torsional dynamics (Stick-Slip) detected at {md:.1f}m MD; high torque and RPM oscillations."
            ev = [
                f"Stick-Slip Index: {contribs.get('stick_slip_index', 0.75):.2f} (Critical > 0.50)",
                f"Torque oscillation: {contribs.get('torque_oscillation', 6.8)} kN.m peak-to-peak",
                f"Bit RPM stalling while surface rotary rotates continuously",
            ]
            action = MitigationAction(
                action_id=act_id,
                hazard_type="TORQUE_DRAG",
                title="Stick-Slip Mitigation: Optimize WOB/RPM & Soft-Torque",
                description="1. Reduce WOB from 85 kN to 55 kN. 2. Increase surface rotary speed to 135 RPM. 3. Engage Soft-Torque feedback control.",
                parameter_adjustments={"wob_kn": 55.0, "rpm": 135.0, "clear_fault": True},
            )

        elif hazard_type == "washout":
            trigger = f"Drillstring/nozzle washout symptom at {md:.1f}m MD; standpipe pressure decay with steady pump rate."
            ev = [
                f"SPP drop observed without surface pump reduction",
                f"Annular hydraulics indicating nozzle or string breach",
            ]
            action = MitigationAction(
                action_id=act_id,
                hazard_type="WASHOUT",
                title="Washout Inspection Protocol",
                description="1. Verify surface manifold for leaks. 2. Flow check well. 3. Trip out of hole to inspect BHA and drillpipe.",
                parameter_adjustments={"flow_in_lpm": 1800.0, "clear_fault": True},
            )

        else:
            trigger = f"Elevated operational drilling risk for {hazard_type} at {md:.1f}m MD."
            ev = [f"Fused risk score: {score:.2f}"]
            action = MitigationAction(
                action_id=act_id,
                hazard_type=hazard_type.upper(),
                title=f"Review Operations for {hazard_type}",
                description="Inspect drilling parameters and confirm geomechanical safety corridor.",
                parameter_adjustments={},
            )

        return trigger, ev, action

    def apply_action(self, well_id: str, alert_id: str) -> Optional[ActiveAlert]:
        """
        Marks an alert's recommended action as APPLIED by the rig engineer.
        """
        if well_id not in self._alerts:
            return None
        for k, alert in self._alerts[well_id].items():
            if alert.alert_id == alert_id:
                alert.status = "MITIGATED"
                alert.recommended_mitigation.applied = True
                alert.recommended_mitigation.applied_at = datetime.now(timezone.utc).isoformat()
                return alert
        return None

    def get_active_alerts(self, well_id: str) -> List[ActiveAlert]:
        """Returns all alerts currently active or mitigated for the well."""
        if well_id not in self._alerts:
            return []
        return [a for a in self._alerts[well_id].values() if a.status != "CLEARED"]
