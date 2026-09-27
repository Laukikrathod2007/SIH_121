"""
NWIS Central Application Configuration
Pydantic Settings with environment variable overrides.
"""

from __future__ import annotations
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "eRTMAC-NWIS Backend Intelligence Core"
    PROJECT_DESCRIPTION: str = (
        "AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations "
        "(Dynamic Offset Relevance Engine + Stratigraphic Correlator + Risk Corridor Engine + Document Intelligence)"
    )
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Base Directories
    APP_DIR: Path = Path(__file__).resolve().parent
    BACKEND_DIR: Path = APP_DIR.parent
    ROOT_DIR: Path = BACKEND_DIR.parent

    # Storage Paths
    DATA_DIR: Path = APP_DIR / "data"
    SYNTHETIC_DATA_DIR: Path = APP_DIR / "data" / "synthetic"
    SAMPLE_DOCS_DIR: Path = APP_DIR / "data" / "sample_docs"
    UPLOAD_DIR: Path = APP_DIR / "data" / "uploads"
    LOG_DIR: Path = APP_DIR / "data" / "logs"
    SQLITE_DB_PATH: Path = APP_DIR / "data" / "nwis_jobs.db"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
