"""
Repository layer for module 04/05's PostgreSQL write-through — the only
place in this package that writes raw SQL (same separation as module 01's
and module 02's db/ packages).

Unit conversions (TelemetryEnvelope -> telemetry_records): the physics
engine's own canonical units (models/telemetry.py) are SI/metric
(kN, bar, g/cc, L/min) per its own module docstring ("Module 5 Section 47
specification"); database/schema.sql's telemetry_records was grounded on
modules/02_nwis_backend/models/schemas.py's TelemetryRecord, which uses
field-standard oilfield units (klbs, psi, ppg) for its own real reasons
(matching module 02's synthetic testbed + real Volve data, already in
those units). Converting here is the correct place for it — this table is
the shared sink multiple producers write into, so the conversion belongs
once, at the write boundary, not duplicated in every producer.
"""

from __future__ import annotations

from typing import Any


# Conversion factors, each named for exactly what it converts (no bare
# magic numbers) and each independently verifiable:
KN_TO_KLBS = 0.2248089431          # 1 kN = 0.2248089431 kip (klbs)
BAR_TO_PSI = 14.5037738            # 1 bar = 14.5037738 psi
GCC_TO_PPG = 8.345404              # 1 g/cm^3 = 8.345404 lb/gal (ppg)
LPM_IS_LPM = 1.0                   # flow_in_lpm/flow_out_lpm already match (L/min both sides)


def envelope_to_telemetry_row(envelope: dict[str, Any]) -> dict[str, Any]:
    """Map one TelemetryEnvelope.model_dump() dict to telemetry_records'
    column shape, converting units where the two schemas differ."""
    channels = envelope.get("channels", {}) or {}
    depth = envelope.get("depth", {}) or {}

    return {
        "time": envelope["timestamp"],
        "well_id": envelope["well_id"],
        "depth_m": depth.get("md_m", 0.0),
        "rop_m_hr": channels.get("rop_m_hr", 0.0),
        "wob_klbs": channels.get("wob_kn", 0.0) * KN_TO_KLBS,
        "rpm": channels.get("rpm", 0.0),
        "torque_kn_m": channels.get("torque_kn_m", 0.0),  # schema's own column is kN.m despite psi-family siblings — matches TelemetryRecord verbatim (not re-derived)
        "standpipe_pressure_psi": channels.get("standpipe_pressure_bar", 0.0) * BAR_TO_PSI,
        "flow_in_lpm": channels.get("flow_in_lpm", 0.0),
        "flow_out_lpm": channels.get("flow_out_lpm", 0.0),
        "pit_volume_bbl": channels.get("pit_volume_m3", 0.0) * 6.28981,  # 1 m^3 = 6.28981 bbl
        "mud_weight_ppg": channels.get("mud_weight_gcc", 1.20) * GCC_TO_PPG,
        "d_exponent": channels.get("d_exponent", 1.0),
        "source_type": "SIMULATED",
    }


class TelemetryRepository:
    def __init__(self, conn):
        self._conn = conn

    def well_exists(self, well_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM wells WHERE well_id = %s", (well_id,)).fetchone()
        return row is not None

    def insert(self, row: dict[str, Any]) -> None:
        """INSERT ... ON CONFLICT DO NOTHING: (well_id, time) is the
        hypertable's primary key, and re-sending the exact same simulation
        tick (e.g. a retried request) must not error or duplicate — but
        unlike the master-data tables, a telemetry tick is never meant to
        be "corrected" in place, so DO NOTHING rather than DO UPDATE."""
        self._conn.execute(
            """
            INSERT INTO telemetry_records (
                time, well_id, depth_m, rop_m_hr, wob_klbs, rpm, torque_kn_m,
                standpipe_pressure_psi, flow_in_lpm, flow_out_lpm, pit_volume_bbl,
                mud_weight_ppg, d_exponent, source_type
            ) VALUES (
                %(time)s, %(well_id)s, %(depth_m)s, %(rop_m_hr)s, %(wob_klbs)s, %(rpm)s,
                %(torque_kn_m)s, %(standpipe_pressure_psi)s, %(flow_in_lpm)s, %(flow_out_lpm)s,
                %(pit_volume_bbl)s, %(mud_weight_ppg)s, %(d_exponent)s, %(source_type)s
            )
            ON CONFLICT (well_id, time) DO NOTHING
            """,
            row,
        )


class AlertRepository:
    _HISTORY_COLUMNS = """
        alert_id, well_id, hazard_type, severity, score, confidence,
        trigger_reason, evidence_chain, recommended_mitigation, status,
        triggered_at, updated_at
    """

    def __init__(self, conn):
        self._conn = conn

    def valid_hazard_codes(self) -> set[str]:
        rows = self._conn.execute("SELECT code FROM hazard_type").fetchall()
        return {r[0] for r in rows}

    def for_well(self, well_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Persisted alert history for one well, newest first -- uses
        idx_alerts_well (well_id, triggered_at DESC), the same index this
        table was given at creation specifically for this query shape.
        Returns dict rows (same row_factory idiom as module 02's
        repositories); the caller maps them to the same AlertAdvisory-ish
        shape the live /predictive/alerts endpoint already returns, so the
        frontend doesn't need two alert shapes."""
        from psycopg.rows import dict_row
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT {self._HISTORY_COLUMNS}
                FROM alerts
                WHERE well_id = %s
                ORDER BY triggered_at DESC
                LIMIT %s
                """,
                (well_id, limit),
            )
            return cur.fetchall()

    def upsert(self, alert: dict[str, Any]) -> None:
        """UPSERT keyed on alert_id (ActiveAlert's own stable id) — an
        alert's status/score legitimately changes over its lifecycle
        (ACTIVE -> ACKNOWLEDGED -> MITIGATED/CLEARED), so re-sending the
        same alert_id with a new status is the expected update path, not
        a duplicate."""
        self._conn.execute(
            """
            INSERT INTO alerts (
                alert_id, well_id, hazard_type, severity, score, confidence,
                trigger_reason, evidence_chain, recommended_mitigation, status,
                triggered_at, updated_at
            ) VALUES (
                %(alert_id)s, %(well_id)s, %(hazard_type)s, %(severity)s, %(score)s,
                %(confidence)s, %(trigger_reason)s, %(evidence_chain)s,
                %(recommended_mitigation)s, %(status)s, %(triggered_at)s, now()
            )
            ON CONFLICT (alert_id) DO UPDATE SET
                severity = excluded.severity,
                score = excluded.score,
                confidence = excluded.confidence,
                trigger_reason = excluded.trigger_reason,
                evidence_chain = excluded.evidence_chain,
                recommended_mitigation = excluded.recommended_mitigation,
                status = excluded.status,
                updated_at = now()
            """,
            alert,
        )
