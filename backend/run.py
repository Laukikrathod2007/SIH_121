"""
eRTMAC-NWIS Unified Backend Server Runner.
Run: python run.py (or from repo root: python backend/run.py)
"""

import sys
from pathlib import Path
import uvicorn

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting eRTMAC-NWIS Unified Backend Server...")
    print(f"📡 API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📊 Redoc Explorer:    http://{settings.HOST}:{settings.PORT}/redoc")
    print("=" * 70)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
