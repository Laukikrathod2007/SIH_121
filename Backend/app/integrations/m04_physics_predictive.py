"""
Module 04 (physics digital twin) + Module 05 (predictive analytics)
integration. Module 05 has no server of its own; Module 04's
`api.server` imports it, exactly as before, now through the canonical
packages `app.modules.physics` / `app.modules.predictive_analytics`.

Owns the simulation background loop's lifecycle. The loop is started and
stopped ONLY from the unified lifespan, never by an import, and starting is
idempotent: calling start_sim_loop() while a loop is already running is a
no-op, so a double-registered router or a re-entered lifespan cannot
produce two simulation loops.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Optional

from fastapi import FastAPI

from app.integrations._mount import mount_legacy_routes

_sim_task: Optional[asyncio.Task] = None


def _server():
    from app.modules.physics.api import server

    return server


def mount(app: FastAPI) -> list[str]:
    return mount_legacy_routes(app, _server().app)


async def health() -> dict:
    return _server()._health_payload()


def sim_loop_running() -> bool:
    return _sim_task is not None and not _sim_task.done()


async def start_sim_loop() -> bool:
    """Start the simulation loop unless one is already running.
    Returns True if a new loop was started, False if one already existed."""
    global _sim_task
    if sim_loop_running():
        return False
    _sim_task = asyncio.create_task(_server()._sim_loop(), name="nwis-physics-sim-loop")
    return True


async def stop_sim_loop() -> None:
    global _sim_task
    task, _sim_task = _sim_task, None
    if task is not None and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
