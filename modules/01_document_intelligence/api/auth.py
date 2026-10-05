"""
NWIS Module 01 -- API authentication & rate limiting.

No implementation lives here any more: authentication and rate limiting are
implemented ONCE, in Backend/app/core/auth.py, and this file re-exports the
names Module 01's routes and health payload use, so everything in this
module depends on the same function objects as the other modules.

Behavior is unchanged: a single shared X-API-Key (NWIS_API_KEY) enforced on
routes that mutate state or cost money (ingest, job status, results,
review); `/`, `/docs`, `/redoc` and `/api/v1/health` stay open; auth is OFF
when no key is configured. The ingest endpoint -- the one that can trigger
a paid cloud-fallback call per request -- has its own, lower-ceiling
per-key sliding-window limiter (default 20 requests per 60 s; override with
NWIS_RATE_LIMIT_INGEST_MAX_REQUESTS / _WINDOW_SECONDS). status/results/review
share the general-purpose limiter (rate_limit_general, default 60/60s) --
previously unlimited, which let /review/{doc_id}/resync in particular (an
explicitly idempotent, safe-to-call-repeatedly Postgres write-through) be
hammered with no throttle at all.
"""

from app.core.auth import (  # noqa: F401
    API_KEY,
    auth_enabled,
    generate_api_key,
    rate_limit_general,
    rate_limit_ingest,
    require_api_key,
)

RATE_LIMIT_ENABLED = rate_limit_ingest.enabled
RATE_LIMIT_MAX_REQUESTS = rate_limit_ingest.max_requests
RATE_LIMIT_WINDOW_SECONDS = rate_limit_ingest.window_seconds
