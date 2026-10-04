"""
Document intelligence end to end through the unified app: upload a real PDF,
run the real 6-layer extraction pipeline, poll the job, read results, review.

Kind: contract (in-process TestClient; the real pipeline code and a real
sample PDF are exercised -- this is NOT mocked).

Runtime-state isolation: every place the module writes (uploads, extraction
outputs, learned templates, the SQLite job store) is redirected to pytest's
temp directory, so running this suite never adds files to, or changes, the
real modules/01_document_intelligence/data/ -- a test asserts exactly that.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[3]
REAL_DATA = REPO / "modules" / "01_document_intelligence" / "data"
SAMPLE_PDF = REAL_DATA / "sample_docs" / "synthetic_oil_india_ddr.pdf"


def _snapshot(path: Path) -> set[str]:
    return {p.name for p in path.glob("*")} if path.exists() else set()


@pytest.fixture()
def isolated_m01(monkeypatch, tmp_path):
    from app.modules.document_intelligence.api import job_store
    from app.modules.document_intelligence.api.routes import ingest, results, review, status
    from app.modules.document_intelligence.pipeline import layer4_template_learner as learner
    from app.modules.document_intelligence.pipeline import orchestrator

    uploads, outputs, templates = tmp_path / "uploads", tmp_path / "output", tmp_path / "templates"
    for d in (uploads, outputs, templates):
        d.mkdir()
    store = job_store.SQLiteJobStore(tmp_path / "jobs.db")

    monkeypatch.setattr(ingest, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(ingest, "JOB_STORE", store)
    monkeypatch.setattr(status, "JOB_STORE", store)
    monkeypatch.setattr(results, "OUTPUT_DIR", outputs)
    monkeypatch.setattr(results, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(review, "OUTPUT_DIR", outputs)
    monkeypatch.setattr(orchestrator, "OUTPUT_DIR", outputs)
    monkeypatch.setattr(learner, "TEMPLATES_DIR", templates)
    monkeypatch.setattr(learner, "_registry", None)       # rebuilt lazily from the (empty) temp dir
    return {"uploads": uploads, "outputs": outputs, "templates": templates, "store": store}


@pytest.fixture()
def client(asgi_app, open_auth, isolated_m01):
    return TestClient(asgi_app)


def _wait_for_job(client, job_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["status"] in ("COMPLETED", "FAILED"):
            return job
        time.sleep(0.25)
    raise AssertionError(f"job {job_id} did not finish in {timeout}s")


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="sample PDF not present")
def test_real_pdf_is_extracted_end_to_end(client, isolated_m01):
    real_output_before = _snapshot(REAL_DATA / "output")
    real_uploads_before = _snapshot(REAL_DATA / "uploads")
    real_templates_before = _snapshot(REAL_DATA / "templates")

    resp = client.post("/api/v1/ingest", files={"file": ("pass3_test.pdf", SAMPLE_PDF.read_bytes(), "application/pdf")})
    assert resp.status_code == 202
    job = _wait_for_job(client, resp.json()["job_id"])
    assert job["status"] == "COMPLETED", job
    assert job["progress_percent"] == 100 and job["total_pages"] >= 1

    doc_id = job["document_id"]
    result = client.get(f"/api/v1/results/{doc_id}")
    assert result.status_code == 200
    events = client.get(f"/api/v1/results/{doc_id}/events").json()
    assert events, "the extraction pipeline found no drilling events in the sample DDR"
    assert client.get(f"/api/v1/results/{doc_id}/formations").status_code == 200
    assert client.get(f"/api/v1/results/{doc_id}/npt").status_code == 200

    # review workflow endpoints work on the extracted document
    assert client.get("/api/v1/review/queue").status_code == 200
    assert client.get(f"/api/v1/review/{doc_id}").status_code == 200

    # the original PDF is served back for the evidence viewer
    file_resp = client.get(f"/api/v1/documents/{doc_id}/file")
    assert file_resp.status_code == 200 and file_resp.content[:5] == b"%PDF-"

    # all state landed in the temp dirs ...
    assert list(isolated_m01["outputs"].glob("*.json")) and list(isolated_m01["uploads"].glob("*.pdf"))
    # ... and the real runtime data was not touched.
    assert _snapshot(REAL_DATA / "output") == real_output_before
    assert _snapshot(REAL_DATA / "uploads") == real_uploads_before
    assert _snapshot(REAL_DATA / "templates") == real_templates_before


def test_non_pdf_upload_is_rejected_with_400(client):
    resp = client.post("/api/v1/ingest", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_missing_file_is_a_422_validation_error(client):
    assert client.post("/api/v1/ingest").status_code == 422


def test_unknown_job_is_404(client):
    assert client.get("/api/v1/jobs/JOB-DOES-NOT-EXIST").status_code == 404


def test_unknown_document_results_are_404(client):
    assert client.get("/api/v1/results/DOC-DOES-NOT-EXIST").status_code == 404
    assert client.get("/api/v1/review/DOC-DOES-NOT-EXIST").status_code == 404


def test_a_corrupt_pdf_fails_the_job_cleanly_without_a_traceback(client):
    resp = client.post("/api/v1/ingest", files={"file": ("broken.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")})
    assert resp.status_code == 202
    job = _wait_for_job(client, resp.json()["job_id"])
    assert job["status"] == "FAILED"
    assert "Traceback" not in (job.get("error") or "") + (job.get("message") or "")
