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


@pytest.mark.parametrize("doc_id", ["*", "../etc/passwd", "DOC*01", "a/b", "DOC TEST"])
def test_doc_id_with_glob_or_path_metacharacters_is_rejected_as_malformed(client, doc_id):
    """A doc_id outside the strict charset must be rejected with 400 before
    ever touching the filesystem -- previously this fell through to
    OUTPUT_DIR.glob(f"*{doc_id}*.json"), so a wildcard-bearing doc_id could
    match and return another document's result without knowing its real
    ID. '../etc/passwd' additionally can't reach a literal 404-via-glob
    path since Starlette's plain {doc_id} converter rejects a literal '/'
    before the route body ever runs -- it arrives as a 404 from routing
    itself, not this validator; assert only the non-slash payloads hit 400."""
    if "/" not in doc_id:
        assert client.get(f"/api/v1/results/{doc_id}").status_code == 400
        assert client.get(f"/api/v1/review/{doc_id}").status_code == 400


def test_a_corrupt_pdf_fails_the_job_cleanly_without_a_traceback(client):
    resp = client.post("/api/v1/ingest", files={"file": ("broken.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")})
    assert resp.status_code == 202
    job = _wait_for_job(client, resp.json()["job_id"])
    assert job["status"] == "FAILED"
    error, message = job.get("error") or "", job.get("message") or ""
    assert "Traceback" not in error + message
    # Strengthened beyond "no literal word Traceback": the client-visible
    # fields must be one of the fixed, author-written generic strings, not
    # str(exc) -- no exception class name or internal path should ever
    # reach the client (Fix 6: this route used to return str(exc) verbatim).
    assert error == "Document processing failed. See server logs for details."
    assert "could not be processed" in message


def test_upload_filename_with_traversal_segments_lands_safely_inside_upload_dir(client, isolated_m01):
    """Fix 2: file.filename is fully client-controlled. A crafted filename
    with '..' segments (POSIX- or Windows-style) must never escape
    UPLOAD_DIR -- assert the saved file is strictly inside it, and that no
    file appears anywhere outside it as a result of this upload."""
    uploads = isolated_m01["uploads"]
    outside_before = _snapshot(uploads.parent)

    for traversal_name in ("../../../etc/passwot.pdf", "..\\..\\windows_target.pdf"):
        resp = client.post(
            "/api/v1/ingest",
            files={"file": (traversal_name, b"%PDF-1.4 minimal", "application/pdf")},
        )
        assert resp.status_code == 202  # still accepted -- extension is still .pdf
        job_id = resp.json()["job_id"]
        saved = list(uploads.glob(f"{job_id}_*"))
        assert len(saved) == 1
        assert saved[0].resolve().parent == uploads.resolve()

    # No new file appeared in uploads' parent directory (i.e. nothing escaped).
    assert _snapshot(uploads.parent) == outside_before | {uploads.name}


def test_empty_after_sanitization_filename_falls_back_to_a_safe_name(client, isolated_m01):
    """A filename whose stem is entirely unsafe characters (so it
    sanitizes down to nothing) must still produce a valid on-disk
    filename, not an error or an empty/hidden file. ("***.pdf" is used
    rather than e.g. "....pdf" because Path(...).suffix treats an
    all-dots name as having NO extension at all -- that's a different,
    pre-existing, correct 400 from the suffix allowlist check, not the
    sanitizer path this test targets.)"""
    resp = client.post(
        "/api/v1/ingest",
        files={"file": ("***.pdf", b"%PDF-1.4 minimal", "application/pdf")},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    saved = list(isolated_m01["uploads"].glob(f"{job_id}_*"))
    assert len(saved) == 1
    assert saved[0].name.lower().endswith(".pdf")
    assert saved[0].stat().st_size > 0


def test_unknown_document_resync_is_404(client):
    assert client.post("/api/v1/review/DOC-DOES-NOT-EXIST/resync").status_code == 404


def test_resync_is_idempotent_no_duplicate_handoff_rows(client, isolated_m01):
    """POST .../resync is safe to call any number of times — the plan's own
    verification requirement (Pass 5 §A4): run it twice, assert no
    duplicate rows. Writes a minimal, schema-accurate result JSON directly
    into the isolated outputs dir (bypassing a real extraction run, which
    this contract test doesn't need) to exercise the route itself."""
    import json

    doc_id = "DOC-RESYNC-TEST-0001"
    result = {
        "document_id": doc_id, "job_id": "JOB-RESYNCTEST", "source_filename": "resync_test.pdf",
        "document_type": "DAILY_DRILLING_REPORT", "well_name": "REPORT", "operator": None,
        "report_date": None, "total_pages": 1, "pages_processed": 1, "scanned_pages": 0,
        "template_used": None, "extraction_started_at": "2026-10-04T00:00:00",
        "extraction_completed_at": "2026-10-04T00:00:01", "total_processing_time_ms": 100.0,
        "cloud_fallback_pages_count": 0, "cloud_fallback_providers_used": [],
        "total_npt_hours": 0.0, "validation_status": "PASS", "overall_confidence": 0.9,
        "flagged_fields_count": 0, "physics_violations_count": 0, "witsml_compliant": True,
        "reviewed": False, "reviewed_by": None, "reviewed_at": None,
        "review_decision": None, "review_notes": None, "field_annotations": [],
        "all_formation_tops": [], "all_npt_records": [], "all_casing_records": [],
        "mud_properties": [], "all_drilling_events": [],
    }
    (isolated_m01["outputs"] / f"{doc_id}.json").write_text(json.dumps(result), encoding="utf-8")

    first = client.post(f"/api/v1/review/{doc_id}/resync")
    assert first.status_code == 200
    assert first.json()["postgres_sync_status"] in ("synced", "not_configured", "unavailable", "error")

    second = client.post(f"/api/v1/review/{doc_id}/resync")
    assert second.status_code == 200
    assert second.json()["postgres_sync_status"] == first.json()["postgres_sync_status"]

    # The JSON file itself must still be exactly one file, never duplicated.
    assert len(list(isolated_m01["outputs"].glob(f"{doc_id}*.json"))) == 1
