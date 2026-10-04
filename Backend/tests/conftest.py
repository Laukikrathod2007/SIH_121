"""
Shared fixtures for the Backend test suite.

Test kinds (see pytest.ini markers):
  unit         pure logic / static analysis / fresh-subprocess import checks
  contract     in-process HTTP against the assembled app (FastAPI TestClient or
               httpx ASGITransport -- no real socket, no real server)
  integration  needs a REAL running server on localhost:8000 (`python run.py`)
  db           needs a reachable PostgreSQL/PostGIS

Nothing here edits sys.path or sys.modules: `app` is importable because
pytest.ini sets `pythonpath = .` (Backend/).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BASELINE_FILE = Path(__file__).resolve().parent / "baselines" / "pre_pass3_contract.json"

TEST_API_KEY = "backend-test-suite-key"  # never a real credential


@pytest.fixture(scope="session")
def baseline() -> dict:
    """API contract captured from the running backend BEFORE the Pass 3 refactor."""
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def asgi_app():
    """The one real application object (importing it is the 'canonical entry
    point imports everything' check)."""
    from app.main import app

    return app


@pytest.fixture()
def open_auth(monkeypatch):
    """Disable API-key auth for a test (patches the shared auth module)."""
    from app.core import auth

    monkeypatch.setattr(auth, "API_KEY", "")


@pytest.fixture()
def keyed_auth(monkeypatch):
    """Enable API-key auth with a throwaway test key; returns the key."""
    from app.core import auth

    monkeypatch.setattr(auth, "API_KEY", TEST_API_KEY)
    return TEST_API_KEY


@pytest.fixture()
def nwis_store_loaded():
    """The in-memory NWIS store is loaded by the app's lifespan; tests that use
    TestClient WITHOUT a lifespan load it explicitly (idempotent)."""
    from app.integrations import m02_nwis_backend

    m02_nwis_backend.store().load()
    return m02_nwis_backend.store()


@pytest.fixture()
def no_heavy_prewarm(monkeypatch):
    """Lifespan tests must not spawn the multi-second Docling / sentence-
    transformers pre-warm threads."""
    from app.integrations import m01_document_intel, m02_nwis_backend

    monkeypatch.setattr(m01_document_intel, "docling_prewarm", lambda: (lambda: None))
    monkeypatch.setattr(m02_nwis_backend, "search_prewarm", lambda: (lambda: None))
