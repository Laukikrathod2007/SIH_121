"""
API-level tests for Pass 5's DB-backed historical-events/DORS/corridors/
analyze routes — the 8 routes left on the in-memory NWISDataStore by
Pass 4 (`GET /api/v2/events`, `/events/search`, `/events/{well_id}`,
`/offset_rank/{well_id}`, `/corridors/{well_id}`, `/ahead_of_bit/{well_id}`,
`/analyze/{well_id}`, `/stratigraphic_depth_track/{well_id}`), now served
by `db.service.DbStoreSnapshot` when NWIS_DATABASE_URL is configured.

Same three-database-mode contract `test_api_well_endpoints.py` already
established for `get_well`/`get_trajectory`/`get_formations`/`get_casing`:

  unconfigured          -> in-memory (data_source="memory")
  configured+reachable  -> PostgreSQL (data_source="postgres")   [db test]
  configured+unreachable-> 503, never silent memory fallback

Also includes a DORS ranking-PARITY regression test: the DB-backed path
must produce the exact same ranking order and composite scores as the
memory-backed path for identical inputs. This exists because Pass 5 found
and fixed a real bug this way (DbStoreSnapshot's trajectory reconstruction
silently defaulted well_type to VERTICAL, corrupting every non-vertical
well's DORS trajectory score by 0.075-0.5) — a route-level "does it return
200" test would never have caught that; only a direct score comparison did.
This test exists so that class of bug can't silently regress.
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
DB_URL_UNREACHABLE = "postgresql://nwis:nwis_dev_password@localhost:59999/nwis"


def _db_reachable(url: str) -> bool:
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


_DB_UP = _db_reachable(DB_URL_REACHABLE)


def requires_db(fn):
    skip = pytest.mark.skipif(not _DB_UP, reason="No reachable NWIS PostgreSQL at localhost:5433")
    return pytest.mark.db(skip(fn))


@pytest.fixture()
def make_client(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    nwis_server.store.load()  # idempotent

    def _make(dsn):
        monkeypatch.setattr(connection, "_DSN", dsn)
        monkeypatch.setattr(connection, "_pool", None)
        return TestClient(nwis_server.app)

    yield _make
    connection.close_pool()


ROUTES_SIMPLE = [
    ("/api/v2/events", {}),
    ("/api/v2/events/search", {"query": "mud loss"}),
    ("/api/v2/events/15%2F9-F-12", {}),
    ("/api/v2/offset_rank/15%2F9-F-12", {"depth": 2500}),
    ("/api/v2/corridors/15%2F9-F-12", {"depth": 2500}),
    ("/api/v2/ahead_of_bit/15%2F9-F-12", {"depth": 2500}),
    ("/api/v2/analyze/15%2F9-F-12", {"depth": 2500}),
    ("/api/v2/stratigraphic_depth_track/15%2F9-F-12", {"depth": 2500}),
]


# ---------------------------------------------------------------------------
# unconfigured: in-memory development mode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,params", ROUTES_SIMPLE)
def test_memory_mode_data_source(make_client, path, params):
    client = make_client(None)
    resp = client.get(path, params=params)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data_source"] == "memory"


# ---------------------------------------------------------------------------
# configured but UNREACHABLE: controlled 503, never silent memory data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,params", ROUTES_SIMPLE)
def test_db_unreachable_is_503_not_silent_memory(make_client, path, params):
    client = make_client(DB_URL_UNREACHABLE)
    resp = client.get(path, params=params)
    assert resp.status_code == 503, resp.text
    assert "data_source" not in resp.json()  # not the old memory response reshaped


def test_db_unreachable_error_body_does_not_leak_connection_details(make_client):
    resp = make_client(DB_URL_UNREACHABLE).get("/api/v2/events")
    text = resp.text
    for secret in ("59999", "nwis_dev_password", "localhost", "psycopg"):
        assert secret not in text


# ---------------------------------------------------------------------------
# configured and reachable: PostgreSQL serves it
# ---------------------------------------------------------------------------

@requires_db
@pytest.mark.parametrize("path,params", ROUTES_SIMPLE)
def test_db_reachable_data_source(make_client, path, params):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get(path, params=params)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data_source"] == "postgres"


@requires_db
def test_db_reachable_events_well_not_found_still_returns_empty_not_error(make_client):
    """A well with zero events is a normal empty result, not a 404 — same
    contract as the in-memory path (store.events_by_well.get(id, []))."""
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/events/DOES-NOT-EXIST-XYZ")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["events"] == []


@requires_db
def test_db_reachable_offset_rank_well_not_found_is_404(make_client):
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/offset_rank/DOES-NOT-EXIST-XYZ", params={"depth": 2500})
    assert resp.status_code == 404


@requires_db
def test_db_reachable_events_carry_source_type_provenance(make_client):
    """Pass 6: events previously dropped `source_type` on the floor when
    mapped from a DB row to the DrillingEvent model (the column was
    SELECTed by EventRepository but never passed to the constructor) --
    confirmed missing from a live response before this fix. 15/9-F-12 is
    a real Volve well whose events were parsed from real source documents,
    so they must read back as "REAL", never null or "SYNTHETIC"."""
    client = make_client(DB_URL_REACHABLE)
    resp = client.get("/api/v2/events/15%2F9-F-12")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 0
    for event in body["events"]:
        assert event["source_type"] == "REAL", event


def test_memory_mode_events_carry_source_type_provenance(make_client):
    """Same provenance honesty check for memory mode: the project's own
    synthetic testbed fixture events must read back as SYNTHETIC, and the
    real-document-parsed events (2 real Volve wells) as REAL -- never
    null, and never blurred together."""
    client = make_client(None)
    resp = client.get("/api/v2/events/15%2F9-F-12")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 0
    assert all(e["source_type"] == "REAL" for e in body["events"])

    resp2 = client.get("/api/v2/events/WELL-NHK-001")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["total"] > 0
    assert all(e["source_type"] == "SYNTHETIC" for e in body2["events"])


# ---------------------------------------------------------------------------
# DORS ranking-PARITY regression test -- the real one. See module docstring.
# ---------------------------------------------------------------------------

@requires_db
def test_offset_rank_db_matches_memory_exactly(make_client):
    """The DB-backed /offset_rank ranking must produce the exact same
    well order AND composite scores as the memory-backed path for the
    same well/depth. Regression guard for the well_type-default bug found
    during Pass 5 implementation (DbStoreSnapshot silently defaulted every
    trajectory's well_type to VERTICAL, which dors_engine.py's
    score_trajectory() reads directly -- corrupting the trajectory
    sub-score, and therefore the composite DORS score, for every
    non-vertical offset well by 0.075-0.5). A route-level 200-status test
    would never catch this class of bug; only a direct score comparison
    does."""
    client = make_client(None)
    mem_resp = client.get("/api/v2/offset_rank/15%2F9-F-12", params={"depth": 2500, "top_n": 14})
    assert mem_resp.status_code == 200
    mem_rankings = mem_resp.json()["rankings"]

    client_db = make_client(DB_URL_REACHABLE)
    db_resp = client_db.get("/api/v2/offset_rank/15%2F9-F-12", params={"depth": 2500, "top_n": 14})
    assert db_resp.status_code == 200
    db_rankings = db_resp.json()["rankings"]

    assert len(mem_rankings) == len(db_rankings) > 0
    for mem_r, db_r in zip(mem_rankings, db_rankings):
        assert mem_r["well_id"] == db_r["well_id"]
        assert abs(mem_r["dors_score"] - db_r["dors_score"]) < 0.0001, (
            f"DORS score mismatch for {mem_r['well_id']}: "
            f"memory={mem_r['dors_score']} db={db_r['dors_score']}"
        )
        for component in ("spatial", "formation", "depth", "trajectory", "hazard"):
            mem_c = mem_r["component_scores"][component]
            db_c = db_r["component_scores"][component]
            assert abs(mem_c - db_c) < 0.0001, (
                f"{component} score mismatch for {mem_r['well_id']}: memory={mem_c} db={db_c}"
            )


@requires_db
def test_corridors_db_matches_memory_exactly(make_client):
    """Same parity guard as above, for risk corridor clustering — verifies
    the full dependency chain (active well lookup, DORS ranking,
    get_events_for_top_wells) matches, not just that the route responds."""
    client = make_client(None)
    mem_resp = client.get("/api/v2/corridors/15%2F9-F-12", params={"depth": 2500})
    db_client = make_client(DB_URL_REACHABLE)
    db_resp = db_client.get("/api/v2/corridors/15%2F9-F-12", params={"depth": 2500})

    mem_corridors = sorted(
        (c["hazard_type"], c["depth_start_m"], c["depth_end_m"]) for c in mem_resp.json()["corridors"]
    )
    db_corridors = sorted(
        (c["hazard_type"], c["depth_start_m"], c["depth_end_m"]) for c in db_resp.json()["corridors"]
    )
    assert mem_corridors == db_corridors
