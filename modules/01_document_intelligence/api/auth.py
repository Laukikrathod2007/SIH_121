"""
NWIS Module 01 — API Authentication & Rate Limiting

Before this module existed, any process that could reach the server's port
could upload documents with no credential check at all — including pages
that (per pipeline/cloud_fallback.py) may get forwarded to a paid third-party
API. That's both a cost-abuse risk (anyone burns your Reducto/Extend.ai
credits) and, if this is ever bound to anything other than localhost, a data
exposure risk.

Design:
  - A single shared API key (NWIS_API_KEY), sent as the `X-API-Key` header.
    Not OAuth/JWT/per-user — this is a single-operator internal tool, not a
    multi-tenant product, so a shared secret is the right amount of
    complexity, not under- or over-engineered for what this actually is.
  - Auth is enforced only on routes that mutate state or cost money/leave
    the air-gapped boundary (ingest, job status, results). `/`, `/docs`,
    `/redoc`, and `/api/v1/health` stay open — health checks need to work
    for monitoring without a credential, and exposing "the server is up" and
    its OpenAPI schema isn't a meaningful information leak on its own.
  - If NWIS_API_KEY is unset, auth is OFF (every route open) — this matches
    the pre-existing behavior exactly, so a fresh checkout without any setup
    still runs for local development. run_server.py's production mode will
    refuse to start without a key (see there) so this can't be silently
    forgotten in a real deployment.
  - A lightweight in-process rate limiter on /ingest specifically, since
    that's the endpoint that can trigger a paid cloud API call per request.
    Per-API-key sliding window, in memory — fine for the single-process
    deployment this system targets (see api/job_store.py's docstring for the
    same caveat); swap for a shared store (Redis) if this ever runs as
    multiple processes.
"""

from __future__ import annotations
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, Request
from loguru import logger

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

API_KEY = os.environ.get("NWIS_API_KEY", "").strip()
RATE_LIMIT_ENABLED = os.environ.get("NWIS_RATE_LIMIT_ENABLED", "true").strip().lower() not in ("0", "false", "no")
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("NWIS_RATE_LIMIT_MAX_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("NWIS_RATE_LIMIT_WINDOW_SECONDS", "60"))


def auth_enabled() -> bool:
    return bool(API_KEY)


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """
    FastAPI dependency — attach to any router/route that should require auth.
    No-ops entirely if NWIS_API_KEY isn't configured (matches pre-existing
    open-by-default behavior for local dev).
    """
    if not auth_enabled():
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid X-API-Key header.",
        )


# ---------------------------------------------------------------------------
# Rate Limiting (in-process sliding window, keyed by API key or client IP)
# ---------------------------------------------------------------------------

_request_log: dict[str, deque] = defaultdict(deque)


async def rate_limit_ingest(request: Request, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """
    FastAPI dependency — caps requests per key (or per IP if auth is off) to
    NWIS_RATE_LIMIT_MAX_REQUESTS per NWIS_RATE_LIMIT_WINDOW_SECONDS. Protects
    the ingest endpoint specifically, since every accepted document can
    trigger a paid cloud-fallback call downstream.
    """
    if not RATE_LIMIT_ENABLED:
        return

    identity = x_api_key or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    window = _request_log[identity]

    while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()

    if len(window) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for {identity}: {len(window)} requests in window")
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: max {RATE_LIMIT_MAX_REQUESTS} requests per "
                f"{RATE_LIMIT_WINDOW_SECONDS}s."
            ),
        )

    window.append(now)


def generate_api_key() -> str:
    """Used by run_server.py to auto-provision a key on first run if none exists."""
    return secrets.token_urlsafe(32)
