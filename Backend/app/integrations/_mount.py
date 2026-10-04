"""
Shared helper for mounting a legacy service's routes onto the unified app.

Each legacy service (document intelligence, NWIS, physics/predictive) builds
its own FastAPI `app` at import time with every route already carrying its
own auth/rate-limit dependencies. Those dependencies are the SAME shared
function objects for all services (the legacy `auth.py` files re-export
app.core.auth), so copying the already-built route objects onto the unified
app preserves each route's exact contract and security behavior with no
re-declaration and no double checking.

Only the legacy app's own bare "/" (and, for physics, the bare "/health"
alias) are skipped: the unified app defines its own aggregate "/" and
"/health".
"""

from __future__ import annotations

from typing import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

_DEFAULT_SKIPPED_PATHS = frozenset({"/", "/health"})


def mount_legacy_routes(
    app: FastAPI,
    legacy_app: FastAPI,
    skip_paths: Iterable[str] = _DEFAULT_SKIPPED_PATHS,
) -> list[str]:
    """Append every HTTP/WebSocket route of `legacy_app` to `app` (except the
    paths in `skip_paths`). Returns the list of mounted paths."""
    skipped = set(skip_paths)
    mounted: list[str] = []
    for route in legacy_app.router.routes:
        if not isinstance(route, (APIRoute, APIWebSocketRoute)):
            continue  # skip FastAPI's own /openapi.json, /docs, /redoc routes
        if route.path in skipped:
            continue
        app.router.routes.append(route)
        mounted.append(route.path)
    return mounted
