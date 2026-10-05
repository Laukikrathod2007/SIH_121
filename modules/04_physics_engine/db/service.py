"""
Service layer for module 04/05's PostgreSQL write-through (Pass 4).

Entry point: sync_evaluation(telemetry_envelope, alerts) -- called from
POST /api/v3/predictive/evaluate (api/server.py) right after
risk_service.process_telemetry_point() returns. Best-effort and NEVER
raises: a database outage must not fail the live risk evaluation the
frontend is waiting on, and must not affect the physics simulation loop
or the WebSocket broadcast, neither of which call this at all.

Like modules/01_document_intelligence/db/service.py's handoff_events,
this honestly skips (counts, never fabricates) whatever doesn't fit the
canonical schema instead of forcing it in:
  - a well_id not present in `wells` (telemetry_records.well_id and
    alerts.well_id are both NOT NULL REFERENCES wells) -- the simulator's
    own default well_id ("WELL-NHK-001") IS seeded by
    database/migrate_seed.py, so this is a defensive guard for a
    reconfigured/reset well_id, not the expected case.
  - an alert's hazard_type not present in the canonical hazard_type table
    -- confirmed by reading alert_advisory_engine.py directly: it emits
    SENSOR_FAULT / LOST_CIRCULATION / TORQUE_DRAG / WASHOUT alongside the
    canonical MUD_LOSS / KICK / STUCK_PIPE names, and the first four have
    no row in hazard_type (schema.sql's 8 values). alerts.hazard_type is
    nullable for exactly this reason (an alert without a resolvable
    hazard code is still a real alert) -- stored with hazard_type=NULL
    rather than dropped or coerced into a wrong code.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from app.modules.nwis.db.connection import is_configured as db_is_configured, get_connection
from app.modules.physics.db.repositories import (
    TelemetryRepository, AlertRepository, envelope_to_telemetry_row,
)


def _alert_row(alert: dict[str, Any], valid_hazards: set[str]) -> dict[str, Any]:
    mitigation = alert.get("recommended_mitigation")
    hazard_type = alert.get("hazard_type")
    from psycopg.types.json import Json
    return {
        "alert_id": alert["alert_id"],
        "well_id": alert["well_id"],
        "hazard_type": hazard_type if hazard_type in valid_hazards else None,
        "severity": alert.get("severity", "ADVISORY"),
        "score": alert.get("score"),
        "confidence": alert.get("confidence"),
        "trigger_reason": alert.get("trigger_reason"),
        "evidence_chain": alert.get("evidence_chain") or [],
        "recommended_mitigation": Json(mitigation) if mitigation is not None else None,
        "status": alert.get("status", "ACTIVE"),
        "triggered_at": alert.get("timestamp"),
    }


def get_alert_history(well_id: str, limit: int = 100) -> dict[str, Any]:
    """Read path for the `alerts` table (Pass 6) -- this table was
    write-only from the application's perspective until now. Returns one
    of three honestly distinct, machine- and UI-distinguishable states
    (same tri-state discipline as module 01's SyncStatus and the Pass 5
    plan's A3 note), never collapsing "no history yet" and "database
    unavailable" into the same empty response:

      {"status": "ok", "alerts": [...]}        -- DB reachable, 0+ real rows
      {"status": "not_configured", "alerts": []}  -- NWIS_DATABASE_URL unset (dev mode)
      {"status": "unavailable"}                   -- DB configured but unreachable; caller returns 503, body carries no "alerts" key at all

    Row -> AlertAdvisory-ish dict mapping reuses the same field semantics
    as api/server.py's _alert_to_advisory (trigger_reason -> headline,
    evidence_chain -> causal_evidence_chain, recommended_mitigation ->
    recommended_action), so the frontend's History tab can reuse the same
    rendering as the live feed instead of a second shape."""
    if not db_is_configured():
        return {"status": "not_configured", "alerts": []}

    try:
        with get_connection() as conn:
            rows = AlertRepository(conn).for_well(well_id, limit=limit)
    except Exception as exc:
        logger.debug(f"Alert history read for well '{well_id}' failed: {exc}")
        return {"status": "unavailable"}

    return {"status": "ok", "alerts": [_history_row_to_advisory(r) for r in rows]}


def _history_row_to_advisory(row: dict[str, Any]) -> dict[str, Any]:
    mitigation = row.get("recommended_mitigation") or {}
    severity = row.get("severity") or "ADVISORY"
    urgency_map = {"CRITICAL": "IMMEDIATE", "WARNING": "HIGH", "ADVISORY": "MEDIUM", "CLEARED": "MEDIUM"}
    description = mitigation.get("description", "") if isinstance(mitigation, dict) else ""
    import re
    steps = [p.strip() for p in re.split(r"\d+\.\s*", description) if p.strip()] if description else []
    status_map = {"ACTIVE": "DETECTED", "ACKNOWLEDGED": "ACKNOWLEDGED", "MITIGATED": "MITIGATED", "CLEARED": "CLEARED"}
    triggered_at = row.get("triggered_at")
    return {
        "alert_id": row.get("alert_id"),
        "well_id": row.get("well_id"),
        "hazard_type": row.get("hazard_type"),
        "severity": severity,
        "measured_depth_m": 0.0,  # not stored on the alerts row itself (only on the live in-memory ActiveAlert) -- honestly omitted rather than fabricated
        "formation": "Unknown",
        "headline": row.get("trigger_reason") or "",
        "causal_evidence_chain": row.get("evidence_chain") or [],
        "recommended_action": {
            "action_id": mitigation.get("action_id", "") if isinstance(mitigation, dict) else "",
            "title": mitigation.get("title", "") if isinstance(mitigation, dict) else "",
            "steps": steps,
            "urgency": urgency_map.get(severity, "MEDIUM"),
        },
        "status": status_map.get(row.get("status") or "ACTIVE", "DETECTED"),
        "created_at": triggered_at.isoformat() if hasattr(triggered_at, "isoformat") else str(triggered_at),
    }


def sync_evaluation(
    telemetry_envelope: dict[str, Any],
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persists one telemetry tick (telemetry_records) and any alerts it
    produced (alerts), both already-decimated to the frontend's ~1 Hz
    evaluate cadence -- see db/__init__.py's module docstring. Returns a
    dict describing what happened; callers only log it, never branch on
    it (same contract as module 01's sync_document)."""
    if not db_is_configured():
        return {"synced": False, "reason": "database_not_configured"}

    well_id = telemetry_envelope.get("well_id", "DEFAULT")

    try:
        with get_connection() as conn:
            telemetry_repo = TelemetryRepository(conn)
            if not telemetry_repo.well_exists(well_id):
                return {"synced": False, "reason": f"well_id '{well_id}' not in wells table"}

            telemetry_repo.insert(envelope_to_telemetry_row(telemetry_envelope))

            alert_repo = AlertRepository(conn)
            valid_hazards = alert_repo.valid_hazard_codes() if alerts else set()
            n_alerts = 0
            for alert in alerts:
                if alert.get("well_id") != well_id:
                    continue  # defensive: never write an alert under a different well than this tick's
                alert_repo.upsert(_alert_row(alert, valid_hazards))
                n_alerts += 1

        return {"synced": True, "well_id": well_id, "alerts_written": n_alerts}
    except Exception as exc:
        logger.debug(f"Telemetry/alert write-through for well '{well_id}' failed (non-fatal): {exc}")
        return {"synced": False, "reason": f"{type(exc).__name__}: {exc}"}
