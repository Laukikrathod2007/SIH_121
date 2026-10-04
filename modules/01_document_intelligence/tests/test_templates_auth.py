"""
Regression test: GET /api/v1/templates must require auth when auth is enabled,
matching every other data route in this module (ingest/status/results/review
are all gated via include_router(..., dependencies=[Depends(require_api_key)])).
Before Pass 2 it was registered directly on `app` with no dependencies=, i.e.
open regardless of auth configuration.

Kind: contract test (in-process TestClient against this module's own app).
The API key is set by patching the shared auth module's value -- no module
reloading or sys.modules manipulation.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.modules.document_intelligence.api import server

pytestmark = pytest.mark.contract

TEST_KEY = "test-key-for-templates-auth"


@pytest.fixture()
def auth_enabled_client(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", TEST_KEY)
    return TestClient(server.app)


def test_templates_requires_auth_when_enabled(auth_enabled_client):
    assert auth_enabled_client.get("/api/v1/templates").status_code == 401


def test_templates_rejects_wrong_key(auth_enabled_client):
    resp = auth_enabled_client.get("/api/v1/templates", headers={"X-API-Key": "nope"})
    assert resp.status_code == 401


def test_templates_accessible_with_valid_key(auth_enabled_client):
    resp = auth_enabled_client.get("/api/v1/templates", headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 200
