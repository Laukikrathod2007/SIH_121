"""
NWIS Module 04 — API Authentication & Rate Limiting

Mirrors modules/01_document_intelligence/api/auth.py and
modules/02_nwis_backend/auth.py exactly: a single shared API key
(NWIS_API_KEY), sent as the `X-API-Key` header, enforced only on the
data/control-serving routes; `/health` and `/docs` stay open for
monitoring. Auth is OFF when NWIS_API_KEY is unset, matching the other two
modules' open-by-default local-dev behavior.
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
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("NWIS_RATE_LIMIT_MAX_REQUESTS", "600"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("NWIS_RATE_LIMIT_WINDOW_SECONDS", "60"))


def auth_enabled() -> bool:
    return bool(API_KEY)


async def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    if not auth_enabled():
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


_request_log: dict[str, deque] = defaultdict(deque)


async def rate_limit(request: Request, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Higher default ceiling than modules 01/02 -- this module's control
    endpoints (physics/step, physics/status) are legitimately polled at a
    high rate by a live-streaming frontend, unlike document ingest or
    analysis endpoints."""
    if not RATE_LIMIT_ENABLED:
        return

    identity = x_api_key or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    window = _request_log[identity]
    while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()

    if len(window) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s.",
        )
    window.append(now)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)
