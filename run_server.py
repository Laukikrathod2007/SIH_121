"""
eRTMAC-NWIS Backend Quickstart Runner
Starts the FastAPI application and WebSocket server with automatic sys.path configuration.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print(f"Starting eRTMAC-NWIS Backend Core on http://{settings.HOST}:{settings.PORT}")
    print(f"Interactive API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 70)
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
