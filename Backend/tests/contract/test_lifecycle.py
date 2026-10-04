"""
Application lifecycle: one startup, one simulation loop, a clean shutdown.

Guards: the physics simulation loop is never started twice (e.g. by a
double-registered router or a re-entered lifespan), importing a module starts
nothing, a failure in one module's startup step does not stop the others, and
shutdown releases the managed resources (sim task cancelled, DB pool closed).

Kind: contract -- drives the REAL lifespan via `with TestClient(app)`. The
heavyweight Docling / sentence-transformers pre-warms are replaced with no-ops
(`no_heavy_prewarm`) so the test does not spawn multi-second model loads.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.integrations import m02_nwis_backend, m04_physics_predictive as phys

pytestmark = pytest.mark.contract

SIM_TASK_NAME = "nwis-physics-sim-loop"


async def _sim_tasks_in_this_loop() -> int:
    return sum(1 for t in asyncio.all_tasks() if t.get_name() == SIM_TASK_NAME and not t.done())


@pytest.fixture()
def lifecycle(asgi_app, no_heavy_prewarm, open_auth):
    return asgi_app


def test_lifespan_starts_exactly_one_simulation_loop(lifecycle):
    assert not phys.sim_loop_running()                    # importing the app started nothing
    with TestClient(lifecycle) as client:
        assert phys.sim_loop_running()
        assert client.portal.call(_sim_tasks_in_this_loop) == 1
    assert not phys.sim_loop_running()


def test_start_sim_loop_is_idempotent_within_one_event_loop(lifecycle):
    with TestClient(lifecycle) as client:
        assert client.portal.call(phys.start_sim_loop) is False   # already running -> not restarted
        assert client.portal.call(phys.start_sim_loop) is False
        assert client.portal.call(_sim_tasks_in_this_loop) == 1


def test_repeated_startup_shutdown_cycles_never_accumulate_loops(lifecycle):
    for _ in range(3):
        with TestClient(lifecycle) as client:
            assert client.portal.call(_sim_tasks_in_this_loop) == 1
        assert not phys.sim_loop_running()


def test_stop_is_safe_when_nothing_is_running_and_when_called_twice(lifecycle):
    async def stop_twice():
        await phys.stop_sim_loop()
        await phys.stop_sim_loop()
        return phys.sim_loop_running()

    assert asyncio.run(stop_twice()) is False


def test_shutdown_cancels_the_loop_and_closes_the_database_pool(lifecycle, monkeypatch):
    closed = []

    def spy_close_pool():
        closed.append(True)
        return True

    monkeypatch.setattr("app.modules.nwis.db.connection.close_pool", spy_close_pool)
    with TestClient(lifecycle):
        assert phys.sim_loop_running()
    assert not phys.sim_loop_running()
    assert closed == [True]                               # pool closed exactly once, at shutdown


def test_a_failing_module_startup_step_does_not_block_the_others(lifecycle, monkeypatch):
    class BrokenStore:
        def load(self):
            raise RuntimeError("simulated NWIS data store failure")

    monkeypatch.setattr(m02_nwis_backend, "store", lambda: BrokenStore())
    with TestClient(lifecycle) as client:
        assert phys.sim_loop_running()                    # physics still came up
        assert client.get("/api/v3/health").status_code == 200
    assert not phys.sim_loop_running()


def test_ready_endpoint_reflects_the_running_simulation(lifecycle):
    with TestClient(lifecycle) as client:
        assert client.get("/ready").json()["physics_sim_loop_running"] is True
