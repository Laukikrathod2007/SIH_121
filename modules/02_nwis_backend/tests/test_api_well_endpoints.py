"""
API-level tests for the database-backed vertical slice
(GET /api/v2/wells/{id}, GET /api/v2/map/wells) across the THREE database
modes the backend must treat truthfully:

  unconfigured          -> normal in-memory development mode (data_source="memory")
  configured+reachable  -> PostgreSQL serves it (data_source="postgres")   [db test]
  configured+unreachable-> controlled 503; NEVER silently serve memory data as if it
                           were the database's answer

Kinds: `contract` tests run in-process through FastAPI's TestClient (no socket).
The reachable-DB test is also marked `db` and is SKIPPED (with a reason) when
no PostgreSQL is reachable at localhost:5433 -- never reported as a pass.
The unreachable-DB tests need no database at all (they point at a closed port).

The DB mode is selected by patching db.connection's DSN for the test; the API
key by patching the shared auth module. No module reloading, no sys.modules
manipulation.
"""
from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.modules.nwis import server as nwis_server
from app.modules.nwis.db import connection

pytestmark = pytest.mark.contract

DB_URL_REACHABLE = "postgresql://nwis:nwis_dev_password@localhost:5433/nwis"
# Nothing listens on 59999: connection refused -> a REAL "configured but
# unreachable" condition (pool open times out), without needing Docker.
DB_URL_UNREACHABLE = "postgresql://nwis:nwis_dev_password@localhost:59999/nwis"


def _db_reachable(url: str) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


@pytest.fixture()
def make_client(monkeypatch):
    """make_client(dsn) -> TestClient with auth disabled and db.connection
    configured for `dsn` (None = unconfigured). Pools are always closed."""
    monkeypatch.setattr(auth, "API_KEY", "")
    nwis_server.store.load()  # idempotent

    def _make(dsn):
        monkeypatch.setattr(connection, "_DSN", dsn)
        monkeypatch.setattr(connection, "_pool", None)
        return TestClient(nwis_server.app)

    yield _make
    connection.close_pool()


# ---------------------------------------------------------------------------
# unconfigured: in-memory development mode
# ---------------------------------------------------------------------------

def test_memory_mode_well_by_id(make_client):
    client = make_client(None)
    wells = client.get("/api/v2/wells").json()["wells"]
    assert wells
    first_id = wells[0]["well_id"]
    body = client.get(f"/api/v2/wells/{first_id}").json()
    assert body["well"]["well_id"] == first_id
    assert body["data_source"] == "memory"


def test_memory_mode_well_not_found(make_client):
    assert make_client(None).get("/api/v2/wells/DOES-NOT-EXIST-XYZ").status_code == 404


def test_memory_mode_slash_containing_real_volve_id(make_client):
    resp = make_client(None).get("/api/v2/wells/15%2F9-F-12")
    assert resp.status_code == 200
    assert resp.json()["well"]["well_id"] == "15/9-F-12"


def test_memory_mode_map_wells_unfiltered_returns_all(make_client):
    body = make_client(None).get("/api/v2/map/wells").json()
    assert body["radius_filter_applied"] is False
    assert all(w["distance_km"] is None for w in body["wells"])


def test_memory_mode_map_wells_hard_radius_filter(make_client):
    """radius_km on map/wells is a HARD geographic filter (unlike offset_rank's
    scoring-decay radius_km)."""
    client = make_client(None)
    all_wells = client.get("/api/v2/map/wells").json()["wells"]
    center = all_wells[0]["well_id"]
    unfiltered = client.get("/api/v2/map/wells", params={"center_well_id": center}).json()
    tight = client.get("/api/v2/map/wells", params={"center_well_id": center, "radius_km": 0.001}).json()
    assert tight["radius_filter_applied"] is True
    assert tight["total"] <= unfiltered["total"]
    assert any(w["well_id"] == center for w in tight["wells"])  # center survives its own filter


# ---------------------------------------------------------------------------
# configured but UNREACHABLE: controlled failure, never silent memory data
# ---------------------------------------------------------------------------

def test_db_unreachable_well_lookup_is_503_not_silent_memory(make_client):
    client = make_client(DB_URL_UNREACHABLE)
    first_id = client.get("/api/v2/wells").json()["wells"][0]["well_id"]  # list route has no DB branch
    resp = client.get(f"/api/v2/wells/{first_id}")
    assert resp.status_code == 503
    assert "data_source" not in resp.json()  # not the old memory response reshaped


def test_db_unreachable_map_wells_is_503(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/map/wells")
    assert resp.status_code == 503
    assert "data_source" not in resp.json()


def test_db_unreachable_error_body_does_not_leak_connection_details(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/map/wells")
    text = resp.text
    for secret in ("59999", "nwis_dev_password", "localhost", "psycopg"):
        assert secret not in text


# ---------------------------------------------------------------------------
# configured and reachable: PostgreSQL serves it
# ---------------------------------------------------------------------------

@pytest.mark.db
@pytest.mark.skipif(
    not _db_reachable(DB_URL_REACHABLE),
    reason="No reachable NWIS PostgreSQL at localhost:5433 (start database/docker-compose.yml and run migrate_seed.py)",
)
def test_db_reachable_well_served_by_postgres_with_provenance(make_client):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/wells/15%2F9-F-12")
    if resp.status_code == 404:
        pytest.skip("Real Volve wells are not seeded -- run database/migrate_seed.py")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_source"] == "postgres"
    assert body["well"]["well_id"] == "15/9-F-12"
    assert body["well"]["source_type"] == "REAL"


# ---------------------------------------------------------------------------
# Pass 4: trajectory / formations / casing — same DB-first-with-memory-
# fallback contract as get_well/get_map_wells above, extended to the three
# other read paths migrated in this pass.
# ---------------------------------------------------------------------------

def test_memory_mode_trajectory(make_client):
    client = make_client(None)
    first_id = client.get("/api/v2/wells").json()["wells"][0]["well_id"]
    resp = client.get(f"/api/v2/trajectory/{first_id}")
    assert resp.status_code == 200
    assert resp.json()["data_source"] == "memory"


def test_memory_mode_formations(make_client):
    client = make_client(None)
    resp = client.get("/api/v2/formations")
    assert resp.status_code == 200
    assert resp.json()["data_source"] == "memory"


def test_memory_mode_casing(make_client):
    client = make_client(None)
    resp = client.get("/api/v2/casing")
    assert resp.status_code == 200
    assert resp.json()["data_source"] == "memory"


def test_db_unreachable_trajectory_is_503(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/trajectory/15%2F9-F-12")
    assert resp.status_code == 503
    assert "data_source" not in resp.json()


def test_db_unreachable_formations_is_503(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/formations")
    assert resp.status_code == 503


def test_db_unreachable_casing_is_503(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/casing")
    assert resp.status_code == 503


@pytest.mark.db
@pytest.mark.skipif(
    not _db_reachable(DB_URL_REACHABLE),
    reason="No reachable NWIS PostgreSQL at localhost:5433 (start database/docker-compose.yml and run migrate_seed.py)",
)
def test_db_reachable_trajectory_served_by_postgres(make_client):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/trajectory/15%2F9-F-12")
    if resp.status_code == 404:
        pytest.skip("Real Volve well trajectory not seeded -- run database/migrate_seed.py")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_source"] == "postgres"
    assert body["well_id"] == "15/9-F-12"
    assert len(body["stations"]) > 0


@pytest.mark.db
@pytest.mark.skipif(
    not _db_reachable(DB_URL_REACHABLE),
    reason="No reachable NWIS PostgreSQL at localhost:5433 (start database/docker-compose.yml and run migrate_seed.py)",
)
def test_db_reachable_formations_served_by_postgres(make_client):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/formations/15%2F9-F-12")
    if resp.status_code == 404:
        pytest.skip("Real Volve well formation tops not seeded -- run database/migrate_seed.py")
    assert resp.status_code == 200
    assert resp.json()["data_source"] == "postgres"


@pytest.mark.db
@pytest.mark.skipif(
    not _db_reachable(DB_URL_REACHABLE),
    reason="No reachable NWIS PostgreSQL at localhost:5433 (start database/docker-compose.yml and run migrate_seed.py)",
)
def test_db_reachable_casing_served_by_postgres(make_client):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/casing")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_source"] == "postgres"
    assert body["total"] >= 1  # real Volve casing records seeded by migrate_seed.py
