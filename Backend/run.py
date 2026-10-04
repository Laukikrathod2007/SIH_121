"""
NWIS Unified Backend -- the ONE correct way to start the entire backend.

    cd Backend
    python run.py            # or, from anywhere:  python Backend/run.py

Listens on http://0.0.0.0:8000 by default (override with NWIS_HOST/NWIS_PORT
in Backend/.env). No subprocess launching, no separate module servers --
document intelligence, well/geospatial intelligence, the physics digital twin
+ predictive analytics, and evidence delivery are all served by this one
process.

Import root: Python places this script's own directory (Backend/) first on
sys.path when it is run as a script, and `app_dir` below pins the same root
for uvicorn (including its auto-reload child process), so startup does not
depend on the current working directory and nothing here edits sys.path.
"""
from __future__ import annotations

from pathlib import Path

import uvicorn

from app.core.config import HOST, IS_PRODUCTION, PORT

BACKEND_ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    print("=" * 60)
    print("  NWIS Unified Backend")
    print("=" * 60)
    print(f"  Mode:   {'production' if IS_PRODUCTION else 'dev'} (set NWIS_ENV=production to deploy)")
    print(f"  Server: http://{HOST}:{PORT}")
    print(f"  Docs:   http://{HOST}:{PORT}/docs")
    print(f"  Health: http://{HOST}:{PORT}/health")
    print("=" * 60)
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        app_dir=str(BACKEND_ROOT),
        reload=not IS_PRODUCTION,
        reload_dirs=[str(BACKEND_ROOT), str(BACKEND_ROOT.parent / "modules")] if not IS_PRODUCTION else None,
    )
