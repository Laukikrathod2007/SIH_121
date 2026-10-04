"""
The public API contract of the unified backend must not drift.

`baselines/pre_pass3_contract.json` was captured from the RUNNING backend
BEFORE the Pass 3 import-architecture refactor. These tests assert the
refactored application serves exactly the same operations, the same declared
parameters, and the same health payload shapes.

Kind: contract (in-process TestClient / OpenAPI generation; no real socket).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.contract


@pytest.fixture()
def client(asgi_app, nwis_store_loaded):
    return TestClient(asgi_app)


def _operations(spec: dict) -> set[str]:
    return {f"{m.upper()} {p}" for p, v in spec["paths"].items() for m in v}


def test_openapi_operations_match_the_pre_refactor_baseline(asgi_app, baseline):
    now = _operations(asgi_app.openapi())
    expected = set(baseline["operations"])
    assert now - expected == set(), f"new operations: {sorted(now - expected)}"
    assert expected - now == set(), f"operations lost: {sorted(expected - now)}"


def test_declared_parameters_match_the_baseline(asgi_app, baseline):
    spec = asgi_app.openapi()
    drift = {}
    for p, v in spec["paths"].items():
        for method, op in v.items():
            key = f"{method.upper()} {p}"
            got = sorted(x["name"] + ":" + x["in"] for x in op.get("parameters", []))
            if got != baseline["declared_parameters"].get(key):
                drift[key] = (baseline["declared_parameters"].get(key), got)
    assert not drift, drift


def test_openapi_covers_every_namespace(asgi_app):
    ops = _operations(asgi_app.openapi())
    for prefix in ("/api/v1/", "/api/v2/", "/api/v3/", "/api/evidence"):
        assert any(o.split(" ", 1)[1].startswith(prefix) for o in ops), prefix


def test_expected_key_routes_are_present(asgi_app):
    ops = _operations(asgi_app.openapi())
    for route in (
        "POST /api/v1/ingest", "GET /api/v1/jobs/{job_id}", "GET /api/v1/review/queue",
        "GET /api/v2/wells/{well_id}", "GET /api/v2/map/wells", "GET /api/v2/offset_rank/{well_id}",
        "GET /api/v2/stratigraphic_depth_track/{well_id}", "GET /api/v2/corridors/{well_id}",
        "GET /api/v2/events/search", "GET /api/v3/physics/status", "POST /api/v3/predictive/evaluate",
        "GET /api/evidence", "GET /health", "GET /ready",
    ):
        assert route in ops, route


def test_websocket_route_is_registered(asgi_app):
    ws_paths = [r.path for r in asgi_app.routes if type(r).__name__ == "APIWebSocketRoute"]
    assert ws_paths == ["/api/v3/physics/stream"]


@pytest.mark.parametrize("path", ["/api/v1/health", "/api/v2/health", "/api/v3/health", "/health"])
def test_health_payload_top_level_shape_is_unchanged(client, baseline, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert sorted(resp.json().keys()) == baseline["health_top_level_keys"][path]


def test_aggregate_health_reports_every_module_truthfully(client, baseline):
    body = client.get("/health").json()
    assert sorted(body["modules"].keys()) == baseline["aggregate_health_module_keys"]
    for name, info in body["modules"].items():
        assert info["status"] in {"healthy", "degraded", "unhealthy", "error"}, name
    # With the required stack installed and the store loaded, the rollup is healthy.
    assert body["status"] == "healthy"


def test_health_never_leaks_secrets_or_connection_strings(client, monkeypatch):
    from app.core import auth

    monkeypatch.setattr(auth, "API_KEY", "super-secret-test-key-123")
    text = client.get("/health").text + client.get("/api/v2/health").text + client.get("/api/v3/health").text
    assert "super-secret-test-key-123" not in text
    for needle in ("password", "postgresql://"):
        assert needle not in text.lower()


def test_ready_reports_store_and_does_not_start_anything(client):
    body = client.get("/ready").json()
    assert body["ready"] is True and body["m02_store_loaded"] is True
