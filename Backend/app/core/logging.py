"""
One rotating log sink for the unified process (in addition to the default
stderr sink loguru already provides). Each harvested module's own
`logger.add(...)` call (in its own server.py top-level code) still runs
during harvest -- that's NOT a bug: each adds a DIFFERENTLY NAMED sink
file (nwis_module01_*.log, nwis_module02_*.log, nwis_module04_*.log), so
loguru's multi-sink support handles this correctly with no guard needed.
This sink is the unified process's OWN top-level log, additional to those.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from app.core.config import REPO_ROOT

LOG_DIR = REPO_ROOT / "Backend" / "data" / "logs"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_DIR / "nwis_unified_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        level="INFO",
        backtrace=False,
        diagnose=False,
    )
