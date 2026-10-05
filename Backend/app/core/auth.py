"""
Unified auth + rate limiting for the consolidated NWIS backend.

Deduplicated from modules/01_document_intelligence/api/auth.py,
modules/02_nwis_backend/auth.py, and modules/04_physics_engine/api/auth.py
-- all three had byte-for-byte identical require_api_key/rate_limit logic
(same deque/time.monotonic() sliding window), differing only in their
default ceiling per module (M01's /ingest=20/60s, M02's general=60/60s,
M04's physics=600/60s -- a real, deliberate difference, justified by
M04's own docstring: physics polling is legitimately high-frequency).
Written once here; `make_rate_limiter()` is instantiated 3 times with
3 different defaults so that per-route-class behavior survives the merge
unchanged.

Single shared NWIS_API_KEY (Pass 3 consolidation decision): this was a
single-operator internal tool with 3 independently-reachable processes
before this pass, each with its own API key -- that per-module key
*isolation* only ever provided a real security boundary when each module
was reachable on its own port. Merged behind one process/one port, 3 keys
only added operational friction (3 secrets to keep in sync) with no
remaining security benefit, so this consolidation uses ONE shared key.
"""

from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Header, HTTPException, Request
from loguru import logger

# Importing config FIRST guarantees Backend/.env has been loaded into the
# environment before NWIS_API_KEY / NWIS_RATE_LIMIT_* are read below,
# regardless of which module imports this one first. (The legacy modules'
# own `auth.py` files used to load their own module-local .env files, which
# is how three different keys could end up in one process.)
import app.core.config  # noqa: F401  (imported for its .env-loading side effect)

API_KEY = os.environ.get("NWIS_API_KEY", "").strip()
RATE_LIMIT_ENABLED = os.environ.get("NWIS_RATE_LIMIT_ENABLED", "true").strip().lower() not in ("0", "false", "no")


def auth_enabled() -> bool:
    return bool(API_KEY)


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if not auth_enabled():
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def make_rate_limiter(env_prefix: str, default_max_requests: int, default_window_seconds: int = 60):
    """
    Returns a plain async dependency FUNCTION (not a class instance) --
    FastAPI's dependant-building introspection (inspect.signature +
    get_type_hints on the callable passed to Depends()) works reliably
    for plain functions; a callable class instance's __call__ triggered a
    real, confirmed bug here (FastAPI mis-resolved `request: Request` as a
    required query parameter instead of the special injected Request
    type, producing a spurious 422 on every request -- reproduced in
    isolation, not specific to this app). A closure over mutable state
    (the deque-based sliding window) is the safe, idiomatic FastAPI
    pattern instead.

    env_prefix e.g. "NWIS_RATE_LIMIT_INGEST" -> reads
    NWIS_RATE_LIMIT_INGEST_MAX_REQUESTS / _WINDOW_SECONDS, falling back to
    the module's original hardcoded default if unset. NWIS_RATE_LIMIT_ENABLED
    (no prefix) is the one shared kill switch across all route classes,
    matching all 3 original modules' own single enable flag.
    """
    enabled = RATE_LIMIT_ENABLED
    max_requests = int(os.environ.get(f"{env_prefix}_MAX_REQUESTS", str(default_max_requests)))
    window_seconds = int(os.environ.get(f"{env_prefix}_WINDOW_SECONDS", str(default_window_seconds)))
    request_log: dict[str, deque] = defaultdict(deque)

    async def rate_limit(request: Request, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
        if not enabled:
            return
        identity = x_api_key or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        window = request_log[identity]
        while window and now - window[0] > window_seconds:
            window.popleft()
        if len(window) >= max_requests:
            logger.warning(f"Rate limit exceeded for {identity}: {len(window)} requests in window")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {max_requests} requests per {window_seconds}s.",
            )
        window.append(now)

    # Exposed so each module's /health payload can truthfully report the
    # limits actually in force (they used to import module-level constants).
    rate_limit.enabled = enabled
    rate_limit.max_requests = max_requests
    rate_limit.window_seconds = window_seconds
    rate_limit.reset = request_log.clear  # test hook: forget all recorded requests
    return rate_limit


# One limiter per route class -- defaults match each module's original
# ceiling exactly (M01 ingest=20/60s, M02 general=60/60s, M04 physics=600/60s).
rate_limit_ingest = make_rate_limiter("NWIS_RATE_LIMIT_INGEST", default_max_requests=20)
rate_limit_general = make_rate_limiter("NWIS_RATE_LIMIT_GENERAL", default_max_requests=60)
rate_limit_physics = make_rate_limiter("NWIS_RATE_LIMIT_PHYSICS", default_max_requests=600)
# Agentic Knowledge Copilot: each call can involve several tool-calling
# rounds and a local LLM generation that takes real wall-clock seconds
# (confirmed live: ~10-20s per round on this machine's CPU) -- a much
# lower ceiling than rate_limit_general's cheap-DB-read 60/60s default,
# same reasoning that gave rate_limit_ingest its own lower ceiling.
rate_limit_agent = make_rate_limiter("NWIS_RATE_LIMIT_AGENT", default_max_requests=10)
