"""
Central exception handling for the unified app. All 3 harvested modules'
own @app.exception_handler(Exception) registrations (on their throwaway
per-module app instances) never run -- only the ONE handler registered on
the real, served app does. Same pattern all 3 already used independently
(log full traceback server-side, return a generic client-safe JSON body,
never leak internals to the client) -- written once here instead of 3x.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred while processing this request.",
                "path": str(request.url.path),
            },
        )
