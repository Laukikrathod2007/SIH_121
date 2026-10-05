"""
Unified configuration for the consolidated NWIS backend. ONE .env file
(Backend/.env), read once, here -- replaces the 3 modules' + evidence-
server's previously separate .env files and NWIS_CORS_ORIGINS/NWIS_ENV/
NWIS_HOST/NWIS_PORT handling. No secrets in source; everything below is
read from the environment, with explicit documented defaults for dev.
"""

from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(_ENV_PATH, override=False)
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

NWIS_ENV = os.environ.get("NWIS_ENV", "dev").strip().lower()
IS_PRODUCTION = NWIS_ENV == "production"

HOST = os.environ.get("NWIS_HOST", "0.0.0.0")
# Render (and most PaaS hosts) inject their own PORT env var and require the
# app to bind to it -- NWIS_PORT (this project's own name, for local-dev
# clarity) takes priority when explicitly set; PORT is the fallback so a
# bare `render.yaml`/platform deploy with no NWIS_PORT set still binds to
# the port the platform actually routes traffic to, instead of silently
# listening on 8000 and never receiving a request.
PORT = int(os.environ.get("NWIS_PORT") or os.environ.get("PORT") or "8000")

_default_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
_extra_origins = [o.strip() for o in os.environ.get("NWIS_CORS_ORIGINS", "").split(",") if o.strip()]
CORS_ORIGINS = _default_origins + _extra_origins

# Where each legacy service's source tree lives. These are NOT used to
# modify sys.path: they are the `__path__` of the canonical adapter
# packages in app/modules/*/__init__.py (app.modules.nwis -> M02_ROOT, ...),
# which is how `import app.modules.nwis.engines...` finds the real files
# without moving, copying or renaming the trees (their data, uploads,
# databases and .env files stay exactly where they are).
MODULES_ROOT = REPO_ROOT / "modules"
M01_ROOT = MODULES_ROOT / "01_document_intelligence"
M02_ROOT = MODULES_ROOT / "02_nwis_backend"
M04_ROOT = MODULES_ROOT / "04_physics_engine"
M05_ROOT = MODULES_ROOT / "05_predictive_analytics"

EVIDENCE_PDF_DIR = REPO_ROOT / "old" / "evidence-server" / "pdfs"

# NWIS_ENV values this codebase recognizes as a deliberate, acknowledged
# non-production environment. Anything outside this set (including an
# unset NWIS_ENV, which defaults to "dev" above) still runs -- dev workflows
# and the test suite deliberately run keyless -- but startup_security_check()
# below warns loudly rather than staying silent, so "auth is off" is never
# discovered after the fact on a deploy target that simply forgot to set
# NWIS_ENV=production.
KNOWN_DEV_ENVS = {"dev", "development", "local", "test"}


def startup_security_check() -> None:
    """Production mode must fail loudly on missing mandatory security
    config, not silently generate a temporary secret or accept an unsafe
    default. Call this once, early in main.py, before serving traffic.

    Every other case (including a merely-unrecognized NWIS_ENV, or a
    recognized dev env with no key) is allowed to start -- this must not
    break the existing test suite or local dev workflow, which deliberately
    run keyless -- but is now backed by a loud startup warning instead of
    silence, since the only thing distinguishing "authenticated production
    deploy" from "wide open to the internet" is this one env var."""
    from app.core.auth import API_KEY

    if IS_PRODUCTION:
        if not API_KEY:
            raise RuntimeError(
                "NWIS_ENV=production requires NWIS_API_KEY to be set explicitly "
                "in Backend/.env -- refusing to start with auth disabled in "
                "production. Set NWIS_API_KEY to a real secret (e.g. "
                "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"`) "
                "and restart."
            )
        return

    if NWIS_ENV not in KNOWN_DEV_ENVS:
        logger.warning(
            f"NWIS_ENV='{NWIS_ENV}' is not 'production' and not a recognized "
            f"dev alias ({sorted(KNOWN_DEV_ENVS)}). If this is a real "
            "deployment, set NWIS_ENV=production explicitly -- otherwise "
            "this process is running with none of production's startup "
            "safety checks."
        )
    if not API_KEY:
        logger.warning(
            "NWIS_API_KEY is not set -- every route in every module is "
            "running UNAUTHENTICATED right now (require_api_key is a no-op "
            "with no key configured). This is only safe for local "
            "development on localhost. Set NWIS_API_KEY before exposing "
            "this process to any network beyond localhost."
        )
