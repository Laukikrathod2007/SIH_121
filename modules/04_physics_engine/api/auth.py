"""
NWIS Module 04 -- authentication & rate limiting.

No implementation lives here any more: authentication and rate limiting are
implemented ONCE, in Backend/app/core/auth.py, and this file re-exports the
names Module 04's routes and health payload use, so every
`Depends(require_api_key)` / `Depends(rate_limit)` in api/server.py resolves
to the same function objects the other modules use.

Behavior is unchanged: one shared X-API-Key (NWIS_API_KEY) on the
data/control-serving routes (`/health` and `/docs` stay open), auth OFF when
no key is configured, and a per-key sliding-window limiter with this
module's higher default ceiling (600 requests per 60 s -- the physics
status/step endpoints are polled at a high rate by the live frontend;
override with NWIS_RATE_LIMIT_PHYSICS_MAX_REQUESTS / _WINDOW_SECONDS).
"""

from app.core.auth import (  # noqa: F401
    API_KEY,
    auth_enabled,
    generate_api_key,
    rate_limit_physics as rate_limit,
    require_api_key,
)

RATE_LIMIT_ENABLED = rate_limit.enabled
RATE_LIMIT_MAX_REQUESTS = rate_limit.max_requests
RATE_LIMIT_WINDOW_SECONDS = rate_limit.window_seconds
