"""
The physics telemetry WebSocket works through the unified backend.

Kind: contract -- FastAPI's in-process WebSocket test client (the real ASGI
WebSocket route, the real simulation loop, no OS socket). The same behaviour
over a real socket is checked by tests/integration/test_live_server.py.

Note on authentication: a browser WebSocket constructor cannot set custom
headers, so this route does NOT use Depends(require_api_key) like every
other route -- but it is not open, either (Fix 4 of the production-
readiness pass: it used to be fully unauthenticated). The shared
NWIS_API_KEY is checked inside the handler itself, as a `?api_key=` query
parameter, before websocket.accept(). When no key is configured
(auth_enabled() is False, matching every other route's behaviour), the
stream stays open with no query param -- that's `open_auth`'s world below.
`keyed_auth`'s tests assert the opposite: a key IS configured, so the
stream requires it exactly like the control endpoints do, just via query
param instead of header.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.integrations import m04_physics_predictive as phys

pytestmark = pytest.mark.contract

REQUIRED_FRAME_KEYS = {"well_id", "sequence", "timestamp", "channels", "provenance"}


@pytest.fixture()
def running_app(asgi_app, no_heavy_prewarm, open_auth):
    with TestClient(asgi_app) as client:
        assert client.post("/api/v3/physics/start").status_code == 200
        try:
            yield client
        finally:
            client.post("/api/v3/physics/pause")
            client.post("/api/v3/physics/reset")


def test_websocket_streams_telemetry_frames_in_sequence(running_app):
    with running_app.websocket_connect("/api/v3/physics/stream") as ws:
        frames = [ws.receive_json() for _ in range(4)]
    for f in frames:
        assert REQUIRED_FRAME_KEYS <= set(f)
    seq = [f["sequence"] for f in frames]
    assert seq == sorted(seq) and len(set(seq)) == len(seq), seq


def test_streamed_telemetry_is_labelled_synthetic_not_field_data(running_app):
    with running_app.websocket_connect("/api/v3/physics/stream") as ws:
        frame = ws.receive_json()
    assert frame["provenance"]["tier"] == "SYNTHETIC"
    assert frame["provenance"]["source"] == "NWIS_PHYSICS_ENGINE"


def test_stream_without_a_key_is_rejected_when_auth_is_enabled(asgi_app, no_heavy_prewarm, keyed_auth):
    """Fix 4: previously this stream was open regardless of auth state.
    With a key configured, connecting with no `?api_key=` must be rejected
    (WS close code 1008, policy violation) before any frame is sent -- the
    client never even completes the opening handshake."""
    with TestClient(asgi_app) as client:
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/v3/physics/stream"):
                pass
        assert exc.value.code == 1008


def test_stream_with_the_wrong_key_is_rejected(asgi_app, no_heavy_prewarm, keyed_auth):
    from starlette.websockets import WebSocketDisconnect

    with TestClient(asgi_app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/v3/physics/stream?api_key=wrong-key"):
                pass
        assert exc.value.code == 1008


def test_stream_with_the_correct_key_still_works_but_control_endpoints_also_need_it(asgi_app, no_heavy_prewarm, keyed_auth):
    with TestClient(asgi_app) as client:
        assert client.post("/api/v3/physics/start").status_code == 401           # control: protected (header)
        assert client.post("/api/v3/physics/start", headers={"X-API-Key": keyed_auth}).status_code == 200
        try:
            with client.websocket_connect(f"/api/v3/physics/stream?api_key={keyed_auth}") as ws:  # stream: protected (query param)
                assert "sequence" in ws.receive_json()
        finally:
            client.post("/api/v3/physics/pause", headers={"X-API-Key": keyed_auth})
            client.post("/api/v3/physics/reset", headers={"X-API-Key": keyed_auth})


def test_stream_stays_open_with_no_key_when_auth_is_disabled(asgi_app, no_heavy_prewarm, open_auth):
    """When NWIS_API_KEY is unset (auth disabled, same as every other
    route), the stream must still work with no query param -- this is the
    one-shared-key model, not a new independent secret."""
    with TestClient(asgi_app) as client:
        assert client.post("/api/v3/physics/start").status_code == 200
        try:
            with client.websocket_connect("/api/v3/physics/stream") as ws:
                assert "sequence" in ws.receive_json()
        finally:
            client.post("/api/v3/physics/pause")
            client.post("/api/v3/physics/reset")


def test_client_disconnect_is_cleaned_up(running_app):
    from app.modules.physics.api import server as physics_server

    with running_app.websocket_connect("/api/v3/physics/stream") as ws:
        ws.receive_json()
    deadline = time.time() + 3
    while physics_server._ws_clients and time.time() < deadline:
        time.sleep(0.05)
    assert len(physics_server._ws_clients) == 0


def test_stopped_simulation_does_not_stream_new_frames(asgi_app, no_heavy_prewarm, open_auth):
    with TestClient(asgi_app) as client:
        assert client.get("/api/v3/physics/status").json()["is_running"] is False
        with client.websocket_connect("/api/v3/physics/stream") as ws:
            # No frames are pushed while stopped; start it and the first frame arrives.
            client.post("/api/v3/physics/start")
            try:
                assert "sequence" in ws.receive_json()
            finally:
                client.post("/api/v3/physics/pause")
                client.post("/api/v3/physics/reset")
    assert not phys.sim_loop_running()


def test_connections_over_the_cap_are_rejected(asgi_app, no_heavy_prewarm, open_auth, monkeypatch):
    """Fix 4's other half: _ws_clients was previously an unbounded set.
    Cap it low for this test and confirm the (cap+1)th connection is
    rejected with WS close code 1013 (try again later) rather than being
    accepted unconditionally."""
    from app.modules.physics.api import server as physics_server
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setattr(physics_server, "MAX_WS_CLIENTS", 2)
    with TestClient(asgi_app) as client:
        with client.websocket_connect("/api/v3/physics/stream") as ws1:
            with client.websocket_connect("/api/v3/physics/stream") as ws2:
                with pytest.raises(WebSocketDisconnect) as exc:
                    with client.websocket_connect("/api/v3/physics/stream"):
                        pass
                assert exc.value.code == 1013
