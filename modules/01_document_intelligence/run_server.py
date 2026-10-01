"""
NWIS Module 01 — Server Entry Point
Run this file to start the complete Document Intelligence API.

Usage:
    python run_server.py

Or for the demo quick test (no server, just processes one PDF):
    python run_server.py --demo "path/to/your.pdf"

Server will start at: http://localhost:8001
API Documentation:   http://localhost:8001/docs
"""

import sys
import os
from pathlib import Path

# Force UTF-8 console output — Windows terminals default to a legacy codepage
# (cp1252) that cannot encode symbols like unicode checkmarks, which rich/loguru
# emit. Without this, CLI demo/test mode crashes with UnicodeEncodeError.
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# Add module root to Python path so imports work correctly
MODULE_ROOT = Path(__file__).parent
sys.path.insert(0, str(MODULE_ROOT))

# ---------------------------------------------------------------------------
# Demo Mode (no server — direct pipeline run)
# ---------------------------------------------------------------------------
if "--demo" in sys.argv:
    idx = sys.argv.index("--demo")
    if idx + 1 >= len(sys.argv):
        print("Usage: python run_server.py --demo path/to/file.pdf")
        sys.exit(1)

    pdf_path = sys.argv[idx + 1]
    from pipeline.orchestrator import run_demo
    run_demo(pdf_path)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Quick test on the Utah FORGE PDF (if it exists in this folder)
# ---------------------------------------------------------------------------
if "--test" in sys.argv:
    test_pdf = MODULE_ROOT.parent.parent / "Drilling Summary Well 16A(78)-32.pdf"
    if not test_pdf.exists():
        print(f"Test PDF not found at: {test_pdf}")
        sys.exit(1)
    from pipeline.orchestrator import run_demo
    run_demo(str(test_pdf))
    sys.exit(0)

# ---------------------------------------------------------------------------
# Server Mode (default)
# ---------------------------------------------------------------------------
import uvicorn


def _ensure_api_key() -> str:
    """
    Secure-by-default: if NWIS_API_KEY isn't set anywhere (shell env or
    .env), generate one now and persist it to .env so every subsequent run
    keeps using the same key instead of silently running wide open. This
    means a fresh checkout that's never had auth configured still starts
    authenticated, with zero setup burden — the alternative (refusing to
    start, or defaulting to no-auth) either breaks a first run or leaves the
    ingest endpoint open to anyone who can reach the port, which can also
    burn cloud-fallback API credits (see api/auth.py, pipeline/cloud_fallback.py).
    """
    from dotenv import load_dotenv, set_key
    env_path = MODULE_ROOT / ".env"
    load_dotenv(env_path, override=False)

    existing = os.environ.get("NWIS_API_KEY", "").strip()
    if existing:
        return existing

    # IMPORTANT: generate the key with stdlib `secrets` directly rather than
    # importing api.auth.generate_api_key(). Importing api.auth executes its
    # module-level `API_KEY = os.environ.get("NWIS_API_KEY", ...)` — if that
    # happens here, BEFORE os.environ is populated below, api.auth's API_KEY
    # constant freezes empty for this process's entire lifetime (Python
    # caches modules; a later os.environ assignment doesn't retroactively
    # re-run it). This bug was real and reproduced: the very first run after
    # generating a fresh key started the server with auth silently disabled,
    # working correctly only after a second restart.
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
    sys.path.insert(0, str(MODULE_ROOT))  # api.auth import below needs this
    _ensure_api_key()
    # NWIS_ENV controls dev vs. production behavior:
    #   dev (default)  -> auto-reload on code changes, single process
    #   production     -> no reload, configurable workers, bind host/port via env
    # Auto-reload uses a file-watcher + process respawn that is unsafe and
    # wasteful outside active development (it also silently drops in-flight
    # background pipeline jobs on every code save).
    env = os.environ.get("NWIS_ENV", "dev").lower()
    is_prod = env == "production"

    host = os.environ.get("NWIS_HOST", "0.0.0.0")
    port = int(os.environ.get("NWIS_PORT", "8001"))
    workers = int(os.environ.get("NWIS_WORKERS", "1"))

    print("\n" + "=" * 60)
    print("  NWIS Document Intelligence API")
    print("  Module 01: 6-Layer OCR + Rules-Based Extraction + Physics Validation")
    print("=" * 60)
    print(f"  Mode:    {'production' if is_prod else 'dev'} (set NWIS_ENV=production to deploy)")
    print(f"  Server:  http://{host}:{port}")
    print(f"  Docs:    http://{host}:{port}/docs")
    print(f"  Health:  http://{host}:{port}/api/v1/health")
    print("=" * 60)
    print("  Demo test:  python run_server.py --test")
    print("  Quick demo: python run_server.py --demo your_file.pdf")
    print("=" * 60 + "\n")

    if is_prod:
        # NOTE: the SQLite job store and in-process template-learning cache
        # assume a single worker process. Running workers > 1 here would
        # give each worker its own disconnected view of in-flight jobs.
        # If you need multi-process scaling, put a shared store (Postgres/
        # Redis) behind JOB_STORE first.
        if workers > 1:
            print(
                "  WARNING: NWIS_WORKERS > 1 is not yet safe — the SQLite job "
                "store and template cache are per-process. Forcing workers=1.\n"
            )
            workers = 1
        uvicorn.run(
            "api.server:app",
            host=host,
            port=port,
            reload=False,
            workers=workers,
            log_level="info",
        )
    else:
        uvicorn.run(
            "api.server:app",
            host=host,
            port=port,
            reload=True,          # Auto-reload on code changes (dev mode)
            reload_dirs=[str(MODULE_ROOT)],
            log_level="info",
        )
