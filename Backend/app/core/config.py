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
PORT = int(os.environ.get("NWIS_PORT", "8000"))

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


def startup_security_check() -> None:
    """Production mode must fail loudly on missing mandatory security
    config, not silently generate a temporary secret or accept an unsafe
    default. Call this once, early in main.py, before serving traffic."""
    if not IS_PRODUCTION:
        return
    from app.core.auth import API_KEY
    if not API_KEY:
        raise RuntimeError(
            "NWIS_ENV=production requires NWIS_API_KEY to be set explicitly "
            "in Backend/.env -- refusing to start with auth disabled in "
            "production. Set NWIS_API_KEY to a real secret (e.g. "
            "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"`) "
            "and restart."
        )
