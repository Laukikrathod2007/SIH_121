"""
Tests for Pass 4's telemetry/alert PostgreSQL write-through
(app.modules.physics.db.service), exercised at the same point in the real
code path as POST /api/v3/predictive/evaluate: one TelemetryEnvelope dict
+ the ActiveAlert dicts it produced.

Kinds: unit-conversion math is a pure unit test. The insert/upsert
round-trip tests need a REACHABLE PostgreSQL at localhost:5433 with the
canonical schema + migrate_seed.py's well catalog loaded (WELL-NHK-001,
the physics engine's own default simulated well, must exist) -- skipped
with an explicit reason when unreachable, same pattern as module 02's and
module 01's db tests.
"""
from __future__ import annotations

import psycopg
import pytest

from app.modules.physics.db import service as physics_db_service
from app.modules.physics.db.repositories import envelope_to_telemetry_row
from app.modules.nwis.db import connection
from app.modules.nwis.db.connection import get_connection

TEST_DSN = "postgresql://nwis:nwis_dev_password@localhost:5433/nwis"


def _db_reachable() -> bool:
    try:
        with psycopg.connect(TEST_DSN, connect_timeout=2) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


_DB_UP = _db_reachable()


def requires_db(fn):
    skip = pytest.mark.skipif(
        not _DB_UP,
        reason="No reachable NWIS PostgreSQL at localhost:5433 -- start it (see database/README.md)",
    )
    return pytest.mark.db(skip(fn))


@pytest.fixture(autouse=True)
def _point_connection_at_test_db(monkeypatch):
    monkeypatch.setattr(connection, "_DSN", TEST_DSN)
    monkeypatch.setattr(connection, "_pool", None)
    yield
    connection.close_pool()


def _fake_envelope(well_id: str = "WELL-NHK-001", sequence: int = 1, **channel_overrides) -> dict:
    channels = {
        "rop_m_hr": 4.0, "rpm": 110.0, "wob_kn": 83.0, "torque_kn_m": 4.3,
        "standpipe_pressure_bar": 268.0, "flow_in_lpm": 2213.0, "flow_out_lpm": 2202.0,
        "pit_volume_m3": 45.0, "mud_weight_gcc": 1.28, "d_exponent": 0.8,
    }
    channels.update(channel_overrides)
    return {
        "well_id": well_id, "wellbore_id": "DEFAULT", "sequence": sequence,
        "timestamp": "2026-10-04T00:00:00+00:00", "simulation_time_s": 1.0,
        "depth": {"md_m": 2500.0, "tvd_m": 2445.0, "tvdss_m": 2425.0},
        "formation": {"name": "Barail Sandstone", "xi": 0.5, "top_tvdss_m": 1400.0, "base_tvdss_m": 2940.0},
        "channels": channels,
        "quality": {"overall": 1.0},
    }


def _fake_alert(**overrides) -> dict:
    base = {
        "alert_id": "TESTFIXTURE-ALERT-1", "well_id": "WELL-NHK-001",
        "timestamp": "2026-10-04T00:00:00+00:00", "hazard_type": "KICK",
        "severity": "CRITICAL", "score": 0.74, "confidence": 0.9,
        "trigger_reason": "test trigger", "evidence_chain": ["test evidence"],
        "recommended_mitigation": {
            "action_id": "test-action", "hazard_type": "KICK", "title": "Test mitigation",
            "description": "1. Do a thing", "parameter_adjustments": {}, "applied": False, "applied_at": None,
        },
        "status": "ACTIVE",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Unit conversion — pure, no database
# ---------------------------------------------------------------------------

def test_envelope_to_telemetry_row_converts_units():
    row = envelope_to_telemetry_row(_fake_envelope())
    assert row["well_id"] == "WELL-NHK-001"
    assert row["depth_m"] == 2500.0
    # 83 kN * 0.2248089431 ~= 18.66 klbs
    assert abs(row["wob_klbs"] - 18.659) < 0.01
    # 268 bar * 14.5037738 ~= 3887 psi
    assert abs(row["standpipe_pressure_psi"] - 3887.0) < 1.0
    # 1.28 g/cc * 8.345404 ~= 10.68 ppg
    assert abs(row["mud_weight_ppg"] - 10.68) < 0.01
    assert row["source_type"] == "SIMULATED"


# ---------------------------------------------------------------------------
# sync_evaluation — requires a live database
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cleanup_fixture_rows():
    yield
    if not _DB_UP:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM alerts WHERE alert_id LIKE 'TESTFIXTURE-ALERT%'")
        conn.execute("DELETE FROM telemetry_records WHERE well_id = 'WELL-NHK-001' AND time = '2026-10-04T00:00:00+00:00'")


@requires_db
def test_sync_evaluation_writes_telemetry_and_valid_hazard_alert():
    out = physics_db_service.sync_evaluation(_fake_envelope(), [_fake_alert()])
    assert out["synced"] is True
    assert out["alerts_written"] == 1

    with get_connection() as conn:
        telemetry_row = conn.execute(
            "SELECT well_id, depth_m FROM telemetry_records WHERE well_id = %s AND time = %s",
            ("WELL-NHK-001", "2026-10-04T00:00:00+00:00"),
        ).fetchone()
        alert_row = conn.execute(
            "SELECT hazard_type, severity FROM alerts WHERE alert_id = %s", ("TESTFIXTURE-ALERT-1",)
        ).fetchone()
    assert telemetry_row == ("WELL-NHK-001", 2500.0)
    assert alert_row == ("KICK", "CRITICAL")


@requires_db
def test_sync_evaluation_nulls_unmapped_hazard_type_without_rejecting_alert():
    """alert_advisory_engine.py emits hazard types with no row in the
    canonical hazard_type table (SENSOR_FAULT, LOST_CIRCULATION,
    TORQUE_DRAG, WASHOUT) -- the alert itself is still a real alert and
    must still be written, with hazard_type stored as NULL rather than
    the insert being rejected by the FK or a wrong code being invented."""
    alert = _fake_alert(alert_id="TESTFIXTURE-ALERT-2", hazard_type="TORQUE_DRAG")
    out = physics_db_service.sync_evaluation(_fake_envelope(sequence=2), [alert])
    assert out["synced"] is True
    assert out["alerts_written"] == 1

    with get_connection() as conn:
        row = conn.execute(
            "SELECT hazard_type, trigger_reason FROM alerts WHERE alert_id = %s", ("TESTFIXTURE-ALERT-2",)
        ).fetchone()
    assert row[0] is None
    assert row[1] == "test trigger"


@requires_db
def test_sync_evaluation_upserts_alert_status_idempotently():
    alert = _fake_alert(alert_id="TESTFIXTURE-ALERT-3", status="ACTIVE")
    physics_db_service.sync_evaluation(_fake_envelope(sequence=3), [alert])

    cleared = _fake_alert(alert_id="TESTFIXTURE-ALERT-3", status="CLEARED", severity="CLEARED")
    physics_db_service.sync_evaluation(_fake_envelope(sequence=4), [cleared])

    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alert_id = %s", ("TESTFIXTURE-ALERT-3",)
        ).fetchone()[0]
        status = conn.execute(
            "SELECT status FROM alerts WHERE alert_id = %s", ("TESTFIXTURE-ALERT-3",)
        ).fetchone()[0]
    assert count == 1, "re-sending the same alert_id must UPSERT, never duplicate"
    assert status == "CLEARED"

    with get_connection() as conn:
        conn.execute("DELETE FROM alerts WHERE alert_id = 'TESTFIXTURE-ALERT-3'")


@requires_db
def test_sync_evaluation_skips_unknown_well_id_without_raising():
    out = physics_db_service.sync_evaluation(_fake_envelope(well_id="NOT-A-REAL-WELL"), [])
    assert out["synced"] is False
    assert "not in wells table" in out["reason"]
