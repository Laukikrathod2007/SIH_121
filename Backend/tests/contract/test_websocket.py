"""
The physics telemetry WebSocket works through the unified backend.

Kind: contract -- FastAPI's in-process WebSocket test client (the real ASGI
WebSocket route, the real simulation loop, no OS socket). The same behaviour
over a real socket is checked by tests/integration/test_live_server.py.

Note on authentication: the stream is intentionally NOT API-key gated -- the
browser WebSocket API cannot set custom headers -- and it is push-only. The
control endpoints (start/pause/step/...) ARE protected; both facts are asserted.
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


def test_stream_stays_open_without_a_key_but_control_endpoints_do_not(asgi_app, no_heavy_prewarm, keyed_auth):
    with TestClient(asgi_app) as client:
        assert client.post("/api/v3/physics/start").status_code == 401           # control: protected
        assert client.post("/api/v3/physics/start", headers={"X-API-Key": keyed_auth}).status_code == 200
        try:
            with client.websocket_connect("/api/v3/physics/stream") as ws:         # stream: open by design
                assert "sequence" in ws.receive_json()
        finally:
            client.post("/api/v3/physics/pause", headers={"X-API-Key": keyed_auth})
            client.post("/api/v3/physics/reset", headers={"X-API-Key": keyed_auth})


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
