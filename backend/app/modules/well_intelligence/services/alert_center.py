"""
Alert Center — turns NWIS analysis results into persistent, evidence-backed alerts.

Producers: every call to NWISOrchestrator.analyze() that goes through
`AlertCenter.evaluate()` (the live replay stream and the on-demand
/alerts/evaluate endpoint). An alert is raised when either
  * the bit is within LEAD_WINDOW_M of a historical offset-well risk corridor, or
  * a hazard's composite risk (history + sensors + model) is HIGH/CRITICAL.

Each alert carries:
  * evidence   — the offset-well events behind it, with source document + page
  * recommendation — the engine's recommended action PLUS what the offset wells
                     actually did (their recorded mitigations), so the advice is
                     traceable, never invented
Alerts are de-duplicated per (well, hazard, corridor) and updated as the bit
advances; acknowledging an alert records who/when/note. State persists to
data/alerts.json so the alert history survives restarts.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings
from app.core.logging import logger
from app.modules.well_intelligence.models.schemas import NWISAnalysisResponse, RiskLevel
from app.modules.well_intelligence.services.data_store import NWISDataStore

LEAD_WINDOW_M = 60.0
ALERTS_PATH = settings.DATA_DIR / "alerts.json"
RANK = {"LOW": 0, "MODERATE": 1, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _severity(level: str, lead_m: Optional[float]) -> str:
    """Corridor proximity escalates severity: inside the zone is at least HIGH."""
    sev = level if level in RANK else "MEDIUM"
    if lead_m is not None and lead_m <= 0 and RANK[sev] < RANK["HIGH"]:
        sev = "HIGH"
    if sev == "LOW":
        sev = "MEDIUM"
    return sev


class AlertCenter:
    _instance: Optional["AlertCenter"] = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._lock = threading.Lock()
            inst._alerts: Dict[str, dict] = {}
            inst._load()
            cls._instance = inst
        return cls._instance

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if ALERTS_PATH.exists():
            try:
                for a in json.loads(ALERTS_PATH.read_text(encoding="utf-8")):
                    self._alerts[a["alert_id"]] = a
            except Exception as exc:
                logger.warning(f"Alert history unreadable, starting fresh: {exc}")

    def _save(self) -> None:
        ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        ALERTS_PATH.write_text(json.dumps(list(self._alerts.values()), indent=1, default=str), encoding="utf-8")

    # -- evidence -------------------------------------------------------------

    @staticmethod
    def _evidence(store: NWISDataStore, event_ids: List[str], hazard: str) -> List[dict]:
        by_id = {e.event_id: e for e in store.all_events}
        wells = store.wells_by_id
        out = []
        for eid in event_ids:
            e = by_id.get(eid)
            if e is None or e.event_type.value != hazard:
                continue
            w = wells.get(e.well_id)
            out.append({
                "event_id": e.event_id,
                "well_id": e.well_id,
                "well_name": w.well_name if w else e.well_id,
                "event_type": e.event_type.value,
                "severity": e.severity,
                "depth_m": e.depth_start_md_m,
                "formation": e.formation,
                "narrative": e.raw_narrative,
                "mitigation": e.mitigation_description,
                "outcome": e.outcome,
                "npt_hours": e.npt_hours,
                "source_document": e.source_document,
                "source_page": e.source_page,
            })
        return out

    @staticmethod
    def _recommendation(engine_action: str, evidence: List[dict]) -> dict:
        steps, seen = [], set()
        for ev in evidence:
            m = (ev.get("mitigation") or "").strip()
            if m and m.lower() not in seen:
                seen.add(m.lower())
                steps.append({"action": m, "from_well": ev["well_name"], "outcome": ev.get("outcome"),
                              "source_document": ev.get("source_document"), "source_page": ev.get("source_page")})
        return {"summary": engine_action, "offset_well_practice": steps[:5]}

    # -- producer -------------------------------------------------------------

    def evaluate(self, result: NWISAnalysisResponse, source: str = "analysis") -> List[dict]:
        """Create/update alerts from one analysis result. Returns alerts raised or updated."""
        store = NWISDataStore()
        touched = []
        now = datetime.utcnow().isoformat()
        with self._lock:
            for h in result.hazard_assessments:
                hazard = h.hazard_type.value
                corridor = h.active_corridor
                lead = h.lead_time_meters
                near_corridor = corridor is not None and lead is not None and lead <= LEAD_WINDOW_M
                high_risk = RANK.get(h.risk_level.value, 0) >= RANK["HIGH"]
                if not (near_corridor or high_risk):
                    continue

                key = f"{result.active_well_id}|{hazard}|{corridor.depth_start_m if corridor else 'none'}"
                # Corridor bounds shift slightly as the bit advances and the
                # offset ranking updates, so match an existing alert for the
                # same well + hazard by OVERLAPPING zone, not an exact key.
                existing = None
                for a in self._alerts.values():
                    if a["status"] != "ACTIVE" or a["well_id"] != result.active_well_id or a["hazard_type"] != hazard:
                        continue
                    z = a.get("zone")
                    if corridor is None and z is None:
                        existing = a
                        break
                    if corridor is not None and z is not None and z["from_m"] <= corridor.depth_end_m and corridor.depth_start_m <= z["to_m"]:
                        existing = a
                        break
                # Evidence = the events that actually form the corridor when one is
                # driving the alert; otherwise the assessment's own evidence list.
                evidence_ids = corridor.contributing_events if near_corridor else h.evidence_events
                evidence = self._evidence(store, evidence_ids, hazard)
                wells = sorted({ev["well_name"] for ev in evidence})
                zone = f"{corridor.depth_start_m:.0f}–{corridor.depth_end_m:.0f} m" if corridor else None

                if near_corridor and lead > 0:
                    title = f"Approaching historical {hazard.replace('_', ' ').lower()} zone"
                    message = f"{lead:.0f} m to the {zone} interval where {len(wells) or corridor.event_count} offset well(s) had {hazard.replace('_', ' ').lower()}."
                elif near_corridor:
                    title = f"Inside historical {hazard.replace('_', ' ').lower()} zone"
                    message = f"Bit is within the {zone} interval where offset wells recorded {hazard.replace('_', ' ').lower()}."
                else:
                    title = f"Elevated {hazard.replace('_', ' ').lower()} risk"
                    message = f"Combined risk score {h.composite_score:.2f} from offset history, sensor anomaly and model."

                payload = {
                    "well_id": result.active_well_id,
                    "hazard_type": hazard,
                    "severity": _severity(h.risk_level.value, lead if near_corridor else None),
                    "title": title,
                    "message": message,
                    "depth_m": round(result.current_depth_m, 1),
                    "formation_at_bit": result.formation_at_bit,
                    "zone": {"from_m": corridor.depth_start_m, "to_m": corridor.depth_end_m} if corridor else None,
                    "lead_distance_m": round(lead, 1) if lead is not None else None,
                    "risk_score": round(h.composite_score, 3),
                    "score_breakdown": {"offset_history": h.p_history, "live_sensors": h.a_sensor,
                                        "model": h.m_ml, "model_source": h.m_ml_source},
                    "offset_wells": wells,
                    "evidence": evidence,
                    "recommendation": self._recommendation(h.recommended_action, evidence),
                    "updated_at": now,
                    "source": source,
                }
                if existing:
                    existing.update(payload)
                    touched.append(existing)
                else:
                    alert = {"alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}", "key": key, "status": "ACTIVE",
                             "created_at": now, "acknowledged_by": None, "acknowledged_at": None, "ack_note": None,
                             **payload}
                    self._alerts[alert["alert_id"]] = alert
                    touched.append(alert)
                    logger.info(f"ALERT {alert['alert_id']} [{alert['severity']}] {title} @ {payload['depth_m']} m ({result.active_well_id})")
            if touched:
                self._save()
        return [dict(a) for a in touched]

    # -- consumers ------------------------------------------------------------

    def list(self, well_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        alerts = list(self._alerts.values())
        if well_id:
            alerts = [a for a in alerts if a["well_id"] == well_id]
        if status:
            alerts = [a for a in alerts if a["status"] == status.upper()]
        return sorted(alerts, key=lambda a: (a["status"] != "ACTIVE", -RANK.get(a["severity"], 0), a["updated_at"]), reverse=False)

    def acknowledge(self, alert_id: str, user: str, note: Optional[str]) -> Optional[dict]:
        with self._lock:
            a = self._alerts.get(alert_id)
            if a is None:
                return None
            a.update({"status": "ACKNOWLEDGED", "acknowledged_by": user, "ack_note": note,
                      "acknowledged_at": datetime.utcnow().isoformat()})
            self._save()
            return dict(a)

    def clear(self, well_id: Optional[str] = None) -> int:
        with self._lock:
            ids = [k for k, a in self._alerts.items() if well_id is None or a["well_id"] == well_id]
            for k in ids:
                del self._alerts[k]
            self._save()
            return len(ids)
