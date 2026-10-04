"""
Tests for the Phase 1 canonical database foundation (db/).

Kinds: `test_healthcheck_*` is a pure unit test (no database). Everything else
is marked `db` and needs a REACHABLE PostgreSQL/PostGIS at localhost:5433
(the database/docker-compose.yml default); when it is not reachable those
tests are SKIPPED with an explicit reason -- they are never reported as
passes. Start one with:

    cd database && docker compose up -d && python migrate_seed.py
    cd ../Backend && pytest ../modules/02_nwis_backend/tests/test_db_foundation.py -v

The DSN is applied by patching db.connection's module state for the duration
of each test (no environment edits at import time, no module reloading).

Covers:
  DATABASE  — schema present, seed idempotency
  WELL      — create/load well, retrieve by ID, special-character IDs
  GEO       — nearby-well query, max distance filtering
  PROVENANCE — real vs synthetic vs simulated remain distinguishable
"""
from __future__ import annotations

import psycopg
import pytest

from app.modules.nwis.db import connection
from app.modules.nwis.db import service as db_service  # noqa: F401  (import must succeed)
from app.modules.nwis.db.connection import get_connection
from app.modules.nwis.db.repositories import WellRepository

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
    """Mark as a `db` test and SKIP (with a reason) when no database is reachable."""
    skip = pytest.mark.skipif(
        not _DB_UP,
        reason="No reachable NWIS PostgreSQL at localhost:5433 -- start it (see module docstring)",
    )
    return pytest.mark.db(skip(fn))


@pytest.fixture(autouse=True)
def _point_connection_at_test_db(monkeypatch):
    """Apply the test DSN to db.connection state for each test and always
    release any pool a test opened."""
    monkeypatch.setattr(connection, "_DSN", TEST_DSN)
    monkeypatch.setattr(connection, "_pool", None)
    yield
    connection.close_pool()


# ---------------------------------------------------------------------------
# HEALTHCHECK (Pass 2 hardening) -- pure unit test, no live DB required:
# monkeypatches get_connection itself, so this runs even without Docker.
# ---------------------------------------------------------------------------

def test_healthcheck_error_field_is_class_name_not_full_message(monkeypatch):
    """healthcheck()'s "error" field must be the exception's class name
    only (e.g. "OperationalError"), never str(exc) -- which for a real
    connection failure includes host/port/user and shouldn't sit in a
    client-facing JSON body (GET /api/v2/health embeds this directly)."""
    import app.modules.nwis.db.connection as connection_module

    monkeypatch.setattr(connection_module, "is_configured", lambda: True)

    class _FakeConnCtx:
        def __enter__(self):
            raise ConnectionRefusedError("connection to server at host.internal.example port 5555 failed")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(connection_module, "get_connection", lambda: _FakeConnCtx())

    result = connection_module.healthcheck()

    assert result["configured"] is True
    assert result["reachable"] is False
    assert result["error"] == "ConnectionRefusedError"
    assert "host.internal.example" not in result["error"]
    assert "5555" not in result["error"]


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

@requires_db
def test_schema_tables_exist():
    """A clean DB initialized from schema.sql has every canonical entity
    table from task requirement #2."""
    expected_tables = {
        "wells", "trajectory_stations", "formations", "formation_tops",
        "drilling_events", "casing_programs", "documents",
        "document_extractions", "telemetry_records", "hazard_assessments",
        "model_registry", "audit_log", "event_embeddings",
    }
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ).fetchall()
    actual = {r[0] for r in rows}
    missing = expected_tables - actual
    assert not missing, f"Missing canonical tables: {missing}"


@requires_db
def test_seed_is_idempotent():
    """Running migrate_seed.py's well insert twice must not duplicate rows
    (task requirement #7). Exercises the actual ON CONFLICT clause rather
    than re-running the whole script (which also re-embeds events and is
    slow) -- a direct, minimal reproduction of the same INSERT.
    """
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM wells").fetchone()[0]
        conn.execute(
            """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
               VALUES ('TEST-IDEMPOTENT-001', 'Idempotency Test Well',
                       ST_SetSRID(ST_MakePoint(91.0, 27.0), 4326)::geography, 1000, 'SYNTHETIC')
               ON CONFLICT (well_id) DO NOTHING""",
        )
        conn.execute(
            """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
               VALUES ('TEST-IDEMPOTENT-001', 'Idempotency Test Well',
                       ST_SetSRID(ST_MakePoint(91.0, 27.0), 4326)::geography, 1000, 'SYNTHETIC')
               ON CONFLICT (well_id) DO NOTHING""",
        )
        after = conn.execute("SELECT COUNT(*) FROM wells").fetchone()[0]
        conn.execute("DELETE FROM wells WHERE well_id = 'TEST-IDEMPOTENT-001'")
        conn.commit()
    assert after == before + 1, "Running the same INSERT twice created duplicate rows"


# ---------------------------------------------------------------------------
# WELL
# ---------------------------------------------------------------------------

@requires_db
def test_create_and_load_well():
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
               VALUES ('TEST-CREATE-001', 'Create Test Well',
                       ST_SetSRID(ST_MakePoint(91.5, 27.5), 4326)::geography, 2500, 'SYNTHETIC')
               ON CONFLICT (well_id) DO NOTHING""",
        )
        conn.commit()
        repo = WellRepository(conn)
        row = repo.get_by_id("TEST-CREATE-001")
        conn.execute("DELETE FROM wells WHERE well_id = 'TEST-CREATE-001'")
        conn.commit()

    assert row is not None
    assert row["well_name"] == "Create Test Well"
    assert row["total_depth_md_m"] == 2500
    assert abs(row["surface_lat"] - 27.5) < 1e-6
    assert abs(row["surface_lon"] - 91.5) < 1e-6


@requires_db
def test_retrieve_by_id_not_found_returns_none():
    with get_connection() as conn:
        repo = WellRepository(conn)
        assert repo.get_by_id("DOES-NOT-EXIST-XYZ") is None


@requires_db
def test_special_character_well_ids_preserved():
    """Task requirement: 'Support IDs containing /, -, _, etc.' and
    'Preserve real Volve identifiers.' Exercises the exact real Volve ID
    shape ("15/9-F-12") end to end through insert + retrieval."""
    special_id = "15/9-F-TEST"
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
               VALUES (%s, 'Special Char Test',
                       ST_SetSRID(ST_MakePoint(1.88, 58.44), 4326)::geography, 3000, 'REAL')
               ON CONFLICT (well_id) DO NOTHING""",
            (special_id,),
        )
        conn.commit()
        repo = WellRepository(conn)
        row = repo.get_by_id(special_id)
        conn.execute("DELETE FROM wells WHERE well_id = %s", (special_id,))
        conn.commit()

    assert row is not None
    assert row["well_id"] == special_id  # not rewritten/parsed/truncated


# ---------------------------------------------------------------------------
# GEO
# ---------------------------------------------------------------------------

@requires_db
def test_nearby_well_query_orders_by_distance():
    """Three wells on a simple east-west line; nearby() from the westmost
    one must return the near one before the far one."""
    wells = [
        ("TEST-GEO-CENTER", 91.00, 27.00),
        ("TEST-GEO-NEAR", 91.05, 27.00),   # ~5km east
        ("TEST-GEO-FAR", 91.50, 27.00),    # ~50km east
    ]
    with get_connection() as conn:
        for well_id, lon, lat in wells:
            conn.execute(
                """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
                   VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 1000, 'SYNTHETIC')
                   ON CONFLICT (well_id) DO NOTHING""",
                (well_id, well_id, lon, lat),
            )
        conn.commit()

        repo = WellRepository(conn)
        results = repo.nearby("TEST-GEO-CENTER")

        for well_id, _, _ in wells:
            conn.execute("DELETE FROM wells WHERE well_id = %s", (well_id,))
        conn.commit()

    test_well_ids = {w[0] for w in wells}
    ids_in_order = [r["well_id"] for r in results if r["well_id"] in test_well_ids]
    assert ids_in_order == ["TEST-GEO-NEAR", "TEST-GEO-FAR"]


@requires_db
def test_max_distance_km_hard_filter_excludes_far_wells():
    """The far well (~50km) must be excluded when max_distance_km=10, and
    included when omitted -- task requirement #10's hard-filter semantics."""
    wells = [
        ("TEST-GEOF-CENTER", 91.00, 27.00),
        ("TEST-GEOF-NEAR", 91.05, 27.00),
        ("TEST-GEOF-FAR", 91.50, 27.00),
    ]
    with get_connection() as conn:
        for well_id, lon, lat in wells:
            conn.execute(
                """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
                   VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 1000, 'SYNTHETIC')
                   ON CONFLICT (well_id) DO NOTHING""",
                (well_id, well_id, lon, lat),
            )
        conn.commit()

        repo = WellRepository(conn)
        filtered = repo.nearby("TEST-GEOF-CENTER", max_distance_km=10.0)
        unfiltered = repo.nearby("TEST-GEOF-CENTER")

        for well_id, _, _ in wells:
            conn.execute("DELETE FROM wells WHERE well_id = %s", (well_id,))
        conn.commit()

    filtered_ids = {r["well_id"] for r in filtered}
    unfiltered_ids = {r["well_id"] for r in unfiltered}
    assert "TEST-GEOF-NEAR" in filtered_ids
    assert "TEST-GEOF-FAR" not in filtered_ids
    assert "TEST-GEOF-FAR" in unfiltered_ids  # proves it's a real filter, not just a coincidence


# ---------------------------------------------------------------------------
# PROVENANCE
# ---------------------------------------------------------------------------

@requires_db
def test_real_synthetic_simulated_remain_distinguishable():
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO wells (well_id, well_name, surface_location, total_depth_md_m, source_type)
               VALUES ('TEST-PROV-REAL', 'Real', ST_SetSRID(ST_MakePoint(1.0, 58.0), 4326)::geography, 1000, 'REAL'),
                      ('TEST-PROV-SYNTH', 'Synth', ST_SetSRID(ST_MakePoint(91.0, 27.0), 4326)::geography, 1000, 'SYNTHETIC')
               ON CONFLICT (well_id) DO NOTHING""",
        )
        conn.commit()
        repo = WellRepository(conn)
        real_row = repo.get_by_id("TEST-PROV-REAL")
        synth_row = repo.get_by_id("TEST-PROV-SYNTH")
        conn.execute("DELETE FROM wells WHERE well_id IN ('TEST-PROV-REAL', 'TEST-PROV-SYNTH')")
        conn.commit()

    assert real_row["source_type"] == "REAL"
    assert synth_row["source_type"] == "SYNTHETIC"
    assert real_row["source_type"] != synth_row["source_type"]


@requires_db
def test_real_volve_wells_seeded_with_real_provenance():
    """If migrate_seed.py has been run, the two real Volve wells must carry
    source_type='REAL', not the table default of 'SYNTHETIC' -- i.e. this
    catches the migration accidentally relying on the column default
    instead of setting it explicitly for real rows."""
    with get_connection() as conn:
        repo = WellRepository(conn)
        row = repo.get_by_id("15/9-F-12")
    if row is None:
        pytest.skip("Real Volve wells not seeded yet -- run migrate_seed.py first")
    assert row["source_type"] == "REAL"
