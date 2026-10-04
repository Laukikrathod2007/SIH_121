"""
Evidence / PDF delivery (/api/evidence): serves bundled documents safely.

Kind: contract (in-process TestClient, real PDF files from the evidence
directory).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import EVIDENCE_PDF_DIR

pytestmark = pytest.mark.contract


@pytest.fixture()
def client(asgi_app):
    return TestClient(asgi_app)


@pytest.fixture(scope="module")
def real_pdf_name() -> str:
    names = sorted(p.name for p in EVIDENCE_PDF_DIR.glob("*.pdf"))
    assert names, f"no evidence PDFs found in {EVIDENCE_PDF_DIR}"
    return names[0]


def test_serves_a_real_pdf_inline(client, real_pdf_name):
    resp = client.get("/api/evidence", params={"name": real_pdf_name})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert resp.headers["content-disposition"].startswith("inline")


def test_every_bundled_document_is_servable(client):
    for pdf in sorted(EVIDENCE_PDF_DIR.glob("*.pdf")):
        r = client.get("/api/evidence", params={"name": pdf.name})
        assert r.status_code == 200 and r.content[:5] == b"%PDF-", pdf.name


@pytest.mark.parametrize("hostile", [
    "../../.env", "..\\..\\.env", "../../../etc/passwd", "....//....//etc/passwd",
    "/etc/passwd", "C:\\Windows\\win.ini", "..%2f..%2f.env", "%2e%2e/%2e%2e/.env",
    "a/../../.env", "subdir/file.pdf", "x\\y.pdf",
])
def test_path_traversal_and_separators_are_rejected(client, hostile):
    resp = client.get("/api/evidence", params={"name": hostile})
    assert resp.status_code == 400, (hostile, resp.status_code)


def test_missing_document_is_a_generic_404_that_does_not_list_the_directory(client, real_pdf_name):
    resp = client.get("/api/evidence", params={"name": "no-such-document.pdf"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Document not found."}
    for name in list(EVIDENCE_PDF_DIR.glob("*.pdf"))[:10]:
        assert name.name not in resp.text


def test_name_parameter_is_required(client):
    assert client.get("/api/evidence").status_code == 422


def test_a_directory_is_not_served_as_a_document(client):
    assert client.get("/api/evidence", params={"name": "."}).status_code in (400, 404)


def test_health_reports_the_document_count(client):
    body = client.get("/api/evidence/health").json()
    assert body["status"] == "healthy" and body["pdf_dir_reachable"] is True
    assert body["pdf_count"] == len(list(EVIDENCE_PDF_DIR.iterdir()))


def test_health_degrades_truthfully_when_the_directory_is_unreadable(client, monkeypatch, tmp_path):
    from app.api import evidence

    monkeypatch.setattr(evidence, "EVIDENCE_PDF_DIR", tmp_path / "does-not-exist")
    body = client.get("/api/evidence/health").json()
    assert body == {"status": "degraded", "pdf_dir_reachable": False, "pdf_count": None}
