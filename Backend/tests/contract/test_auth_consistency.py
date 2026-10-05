"""
Authentication is ONE implementation applied consistently to every protected
route in every service.

Two complementary checks:
  * structural -- walk each route's resolved dependency tree and require the
    shared app.core.auth.require_api_key (by object identity) on every route
    that is not an explicitly public one. This catches the class of bug where
    one route in one service is silently left open (it already happened once:
    /api/v1/templates).
  * behavioural -- real requests with no key / wrong key / right key against
    each endpoint group.

Kind: contract (in-process TestClient).
"""
from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import auth

pytestmark = pytest.mark.contract

# Deliberately public: health/readiness/root/docs, and the evidence PDF router (a
# plain <iframe>/<img> cannot send an X-API-Key header; it serves only bundled
# sample documents, with path-traversal protection). The WebSocket telemetry
# stream is listed here too for the SAME structural reason -- it's an
# APIWebSocketRoute, not an APIRoute, so it never carries a Depends() the
# walk below could see either way -- but it is NOT actually open: the
# browser WebSocket API can't set custom headers, so physics_stream() in
# modules/04_physics_engine/api/server.py checks the shared key as a
# `?api_key=` query parameter inside the handler itself, before accept().
# See test_physics_websocket_auth.py (module 04) for that behavioural check.
PUBLIC_PATHS = {
    "/", "/health", "/ready", "/api/v1/health", "/api/v2/health", "/api/v3/health",
    "/api/evidence", "/api/evidence/health", "/api/v3/physics/stream",
}
PROTECTED_PREFIXES = ("/api/v1/", "/api/v2/", "/api/v3/")


def _dependency_calls(dependant) -> set:
    calls = set()
    stack = [dependant]
    while stack:
        d = stack.pop()
        if d.call is not None:
            calls.add(d.call)
        stack.extend(d.dependencies)
    return calls


def _api_routes(app):
    return [r for r in app.routes if isinstance(r, APIRoute)]


def test_every_non_public_api_route_requires_the_shared_api_key(asgi_app):
    unprotected = [
        f"{sorted(r.methods)} {r.path}"
        for r in _api_routes(asgi_app)
        if r.path.startswith(PROTECTED_PREFIXES)
        and r.path not in PUBLIC_PATHS
        and auth.require_api_key not in _dependency_calls(r.dependant)
    ]
    assert not unprotected, f"routes missing the shared require_api_key: {unprotected}"


def test_public_routes_are_exactly_the_documented_set(asgi_app):
    """No route is public by accident: anything under /api/vN that does NOT carry
    the key check must be in PUBLIC_PATHS."""
    open_routes = {
        r.path for r in _api_routes(asgi_app)
        if r.path.startswith(PROTECTED_PREFIXES) and auth.require_api_key not in _dependency_calls(r.dependant)
    }
    assert open_routes <= PUBLIC_PATHS, open_routes - PUBLIC_PATHS


@pytest.mark.parametrize("path,limiter_name", [
    ("/api/v1/ingest", "rate_limit_ingest"),
    ("/api/v1/jobs/{job_id}", "rate_limit_general"),
    ("/api/v1/results/{doc_id}", "rate_limit_general"),
    ("/api/v1/review/queue", "rate_limit_general"),
    ("/api/v2/wells", "rate_limit_general"),
    ("/api/v2/offset_rank/{well_id}", "rate_limit_general"),
    ("/api/v3/physics/status", "rate_limit_physics"),
    ("/api/v3/predictive/evaluate", "rate_limit_physics"),
])
def test_each_group_uses_its_own_shared_rate_limiter(asgi_app, path, limiter_name):
    # path_format is the converter-free form ("{well_id}") that OpenAPI shows;
    # the route itself is declared "{well_id:path}" so IDs containing "/" work.
    route = next(r for r in _api_routes(asgi_app) if r.path_format == path)
    assert getattr(auth, limiter_name) in _dependency_calls(route.dependant)


SAMPLE_PROTECTED = [
    "/api/v1/jobs", "/api/v1/templates", "/api/v1/review/queue",
    "/api/v2/wells", "/api/v2/map/wells", "/api/v2/events", "/api/v2/formations",
    "/api/v3/physics/status", "/api/v3/predictive/models", "/api/v3/predictive/alerts/WELL-NHK-001",
]


@pytest.fixture()
def client(asgi_app, nwis_store_loaded, keyed_auth):
    return TestClient(asgi_app)


@pytest.mark.parametrize("path", SAMPLE_PROTECTED)
def test_missing_key_is_401_on_every_group(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", SAMPLE_PROTECTED)
def test_wrong_key_is_401_on_every_group(client, path):
    assert client.get(path, headers={"X-API-Key": "wrong"}).status_code == 401


@pytest.mark.parametrize("path", SAMPLE_PROTECTED)
def test_correct_key_is_accepted_on_every_group(client, keyed_auth, path):
    assert client.get(path, headers={"X-API-Key": keyed_auth}).status_code == 200


@pytest.mark.parametrize("path", sorted(p for p in PUBLIC_PATHS if p not in {"/api/evidence", "/api/v3/physics/stream"}))
def test_public_routes_need_no_key_even_when_auth_is_enabled(client, path):
    assert client.get(path).status_code == 200


def test_unauthenticated_mutating_calls_are_rejected(client):
    assert client.post("/api/v1/ingest", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")}).status_code == 401
    assert client.post("/api/v3/physics/start").status_code == 401
    assert client.post("/api/v3/predictive/evaluate", json={"well_id": "W", "telemetry": {"a": 1}}).status_code == 401


def test_401_body_is_a_stable_client_safe_message(client):
    body = client.get("/api/v2/wells").json()
    assert body == {"detail": "Missing or invalid X-API-Key header."}


def test_ingest_endpoint_is_rate_limited_with_429(asgi_app, keyed_auth):
    """The upload endpoint (the one that can trigger paid cloud calls) is capped at
    NWIS_RATE_LIMIT_INGEST_MAX_REQUESTS (default 20) per window."""
    limit = auth.rate_limit_ingest.max_requests
    auth.rate_limit_ingest.reset()
    client = TestClient(asgi_app)
    try:
        codes = [client.post("/api/v1/ingest", headers={"X-API-Key": keyed_auth}).status_code for _ in range(limit + 1)]
    finally:
        auth.rate_limit_ingest.reset()
    assert 429 not in codes[:limit]
    assert codes[limit] == 429
