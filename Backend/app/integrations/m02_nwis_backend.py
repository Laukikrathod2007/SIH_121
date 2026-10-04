"""
Module 02 (NWIS: wells, nearby-well intelligence, DORS, stratigraphic
correlation, risk corridors, knowledge search, telemetry replay) integration.

Imports the service through its canonical package (`app.modules.nwis`, an
adapter over modules/02_nwis_backend/) and mounts its already-built routes.
The hardened Postgres/PostGIS layer (`app.modules.nwis.db`) is used as-is.
"""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI

from app.integrations._mount import mount_legacy_routes


def _server():
    from app.modules.nwis import server

    return server


def mount(app: FastAPI) -> list[str]:
    return mount_legacy_routes(app, _server().app)


async def health() -> dict:
    return await _server().health()


def store():
    """The NWISDataStore singleton (loaded from the unified lifespan)."""
    return _server().store


def search_prewarm() -> Callable[[], object]:
    """Background pre-warm callable for the sentence-transformers model."""
    from app.modules.nwis.search.knowledge_search import _get_model

    return _get_model
