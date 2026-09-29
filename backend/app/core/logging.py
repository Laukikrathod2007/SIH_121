"""
NWIS Unified Logging Configuration.
Provides structured logging using Loguru with a seamless standard-library fallback.
"""

from __future__ import annotations
import sys
import logging
from pathlib import Path
from app.config import settings

try:
    from loguru import logger as _loguru_logger

    def _setup_loguru():
        _loguru_logger.remove()
        _loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True,
        )
        log_file = settings.LOG_DIR / "nwis_backend_{time:YYYY-MM-DD}.log"
        _loguru_logger.add(
            str(log_file),
            rotation="10 MB",
            retention="14 days",
            encoding="utf-8",
            enqueue=True,
            level="INFO",
            backtrace=False,
            diagnose=False,
        )
        return _loguru_logger

    logger = _setup_loguru()

except ImportError:
    # Standard library fallback
    class _FallbackLogger:
        def __init__(self):
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
                handlers=[
                    logging.StreamHandler(sys.stderr),
                ]
            )
            self._logger = logging.getLogger("nwis")

        def info(self, msg, *args, **kwargs):
            self._logger.info(msg, *args, **kwargs)

        def success(self, msg, *args, **kwargs):
            self._logger.info(f"SUCCESS: {msg}", *args, **kwargs)

        def warning(self, msg, *args, **kwargs):
            self._logger.warning(msg, *args, **kwargs)

        def error(self, msg, *args, **kwargs):
            self._logger.error(msg, *args, **kwargs)

        def debug(self, msg, *args, **kwargs):
            self._logger.debug(msg, *args, **kwargs)

        def exception(self, msg, *args, **kwargs):
            self._logger.exception(msg, *args, **kwargs)

    logger = _FallbackLogger()
