"""
Module 01 (Document Intelligence) integration.

Imports the service through its canonical package
(`app.modules.document_intelligence`, an adapter over
modules/01_document_intelligence/) and mounts its already-built routes.
Importing `api.server` runs that module's own top-level setup exactly once
(upload/output directories, the SQLite job store, router wiring) -- an
ordinary import, resolved by the normal import system, so there is no path
switching and no way for it to resolve to another module's `models`/`api`.

Nothing in the extraction pipeline is touched.
"""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI

from app.integrations._mount import mount_legacy_routes


def _server():
    from app.modules.document_intelligence.api import server

    return server


def mount(app: FastAPI) -> list[str]:
    return mount_legacy_routes(app, _server().app)


async def health() -> dict:
    """Module 01's own health payload (PyMuPDF required; Docling/spaCy/
    cloud-fallback reported honestly as optional)."""
    return await _server().health()


def docling_prewarm() -> Callable[[], object]:
    """Background pre-warm callable for the (optional) Docling OCR converter."""
    from app.modules.document_intelligence.pipeline.tier2_ocr_engine import (
        _get_docling_converter,
    )

    return _get_docling_converter
