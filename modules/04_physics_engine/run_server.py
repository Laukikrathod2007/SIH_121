"""
NWIS Module 04 — Entry Point
Run this to start the Physics Digital Twin & Predictive Risk API.

Usage:
    python run_server.py            → Start server at http://localhost:8003
"""

import sys
import os
from pathlib import Path

# STANDALONE debug launcher. The product runs as ONE backend (Backend/run.py).
# This module's code is imported through its canonical packages
# `app.modules.physics` / `app.modules.predictive_analytics` (see
# Backend/app/modules/), so Backend/ -- which holds that `app` package -- is
# put on the path once, here, at launcher start.
MODULE_ROOT = Path(__file__).parent
BACKEND_ROOT = MODULE_ROOT.parents[1] / "Backend"
sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Server Mode (default)
# ---------------------------------------------------------------------------
import uvicorn


def _ensure_api_key() -> str:
    """Secure-by-default, matching modules/01 and modules/02's run_server.py:
    generate an API key on first run if none exists and persist it to .env."""
    from dotenv import load_dotenv, set_key
    env_path = MODULE_ROOT / ".env"
    load_dotenv(env_path, override=False)

    existing = os.environ.get("NWIS_API_KEY", "").strip()
    if existing:
        return existing

    # IMPORTANT: generate with stdlib `secrets` directly, not
    # api.auth.generate_api_key() -- importing api.auth executes its
    # module-level `API_KEY = os.environ.get(...)` read; if that happens
    # before os.environ is populated below, api.auth's API_KEY constant
    # freezes empty for this process's entire lifetime (see modules/01 and
    # modules/02's run_server.py for the same documented gotcha).
    import secrets
    new_key = secrets.token_urlsafe(32)
    env_path.touch(exist_ok=True)
    set_key(str(env_path), "NWIS_API_KEY", new_key)
    os.environ["NWIS_API_KEY"] = new_key
    print("=" * 60)
    print("  No NWIS_API_KEY found — generated one and saved it to .env")
    print(f"  API key: {new_key}")
    print("  Send it as header: X-API-Key: <key above>")
    print("  (Delete NWIS_API_KEY from .env to disable auth entirely.)")
    print("=" * 60)
    return new_key


if __name__ == "__main__":
    _ensure_api_key()

    env = os.environ.get("NWIS_ENV", "dev").lower()
    is_prod = env == "production"
    host = os.environ.get("NWIS_HOST", "0.0.0.0")
    port = int(os.environ.get("NWIS_PORT", "8003"))

    print("\n" + "=" * 60)
    print("  NWIS Physics Digital Twin & Predictive Risk API — Module 04")
    print("  Engines: DrillingPhysicsEngine | RealTimeRiskInferenceService | AlertAdvisoryEngine")
    print("=" * 60)
    print(f"  Mode:      {'production' if is_prod else 'dev'} (set NWIS_ENV=production to deploy)")
    print(f"  Server:    http://{host}:{port}")
    print(f"  Docs:      http://{host}:{port}/docs")
    print(f"  Health:    http://{host}:{port}/health")
    print(f"  WS Stream: ws://{host}:{port}/api/v3/physics/stream")
    print("=" * 60 + "\n")

    if is_prod:
        uvicorn.run("app.modules.physics.api.server:app", app_dir=str(BACKEND_ROOT), host=host, port=port, reload=False, log_level="info")
    else:
        uvicorn.run(
            "app.modules.physics.api.server:app",
            app_dir=str(BACKEND_ROOT),
            host=host,
            port=port,
            reload=True,
            reload_dirs=[str(MODULE_ROOT)],
            log_level="info",
        )
