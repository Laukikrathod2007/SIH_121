"""
Regression test: GET /api/v2/analyze/{id} must not leak raw exception text to
the client. Before Pass 2 it did `raise HTTPException(500, f"Analysis error:
{str(e)}")`; this forces a distinctive exception and asserts neither its
message nor its class name reaches the response.

Kind: contract test (in-process TestClient). The failure is injected by
patching the orchestrator's `analyze` method for the duration of the test.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.modules.nwis import server as nwis_server

pytestmark = pytest.mark.contract


def test_analyze_well_error_is_generic_not_raw_exception(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    nwis_server.store.load()
    secret_text = "some internal orchestrator detail that must not leak"

    def _boom(self, **kwargs):
        raise RuntimeError(secret_text)

    monkeypatch.setattr(nwis_server.NWISOrchestrator, "analyze", _boom)

    client = TestClient(nwis_server.app)
    well_id = nwis_server.store.all_wells[0].well_id
    resp = client.get(f"/api/v2/analyze/{well_id}", params={"depth": 1000})

    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert secret_text not in detail
    assert "RuntimeError" not in detail
