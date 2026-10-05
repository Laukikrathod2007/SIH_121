"""
NWIS Module 02 -- authentication & rate limiting.

This module no longer contains its own implementation. Authentication and
rate limiting are implemented ONCE, in Backend/app/core/auth.py, and this
file re-exports exactly the names Module 02's routes and health payload use,
so every `Depends(require_api_key)` / `Depends(rate_limit)` in server.py
resolves to the SAME function objects the other modules use (not a second
copy that merely reads the same environment variable).

Behavior is unchanged: a single shared X-API-Key (NWIS_API_KEY), enforced
only on data-serving routes (health/root/docs stay open), auth OFF when no
key is configured, and a per-key sliding-window limiter (default 60 requests
per 60 s for this module's route class; override with
NWIS_RATE_LIMIT_GENERAL_MAX_REQUESTS / _WINDOW_SECONDS).
"""

from app.core.auth import (  # noqa: F401
    API_KEY,
    auth_enabled,
    generate_api_key,
    rate_limit_agent,
    rate_limit_general as rate_limit,
    require_api_key,
)

RATE_LIMIT_ENABLED = rate_limit.enabled
RATE_LIMIT_MAX_REQUESTS = rate_limit.max_requests
RATE_LIMIT_WINDOW_SECONDS = rate_limit.window_seconds
