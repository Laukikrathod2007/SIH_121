"""
LIVE integration tests -- a real server process, real sockets, real services.

Kind: integration. These talk to the backend you started with the canonical
command and are SKIPPED (with a reason, never counted as passes) when nothing
answers on localhost:8000:

    cd Backend && python run.py          # terminal 1
    cd Backend && pytest tests/integration -m integration      # terminal 2

What is verified over real HTTP / a real WebSocket:
  health of all four modules, authentication on every group, correct data from
  the NWIS engines, the physics WebSocket stream, evidence delivery and
  path-traversal rejection, genuine multi-connection concurrency, and that the
  retired service ports (8001/8002/8003/4100) are really closed.

Document ingestion writes to the REAL runtime data directory (uploads, outputs,
job database, learned templates), so it only runs when NWIS_LIVE_INGEST=1.
The API key is read from Backend/.env in-process and is never printed.
"""
from __future__ import annotations

import os
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values

pytestmark = pytest.mark.integration

BASE = os.environ.get("NWIS_TEST_BASE_URL", "http://127.0.0.1:8000")
BACKEND = Path(__file__).resolve().parents[2]


def _server_up() -> bool:
    try:
        return httpx.get(f"{BASE}/ready", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def server():
    if not _server_up():
        pytest.skip(f"no backend answering at {BASE} -- start it with: cd Backend && python run.py")
    return BASE


@pytest.fixture(scope="module")
def key() -> str:
    return (dotenv_values(BACKEND / ".env").get("NWIS_API_KEY") or "").strip()


@pytest.fixture()
def api(server, key):
    headers = {"X-API-Key": key} if key else {}
    with httpx.Client(base_url=server, headers=headers, timeout=60) as client:
        yield client


def test_health_of_every_module_over_real_http(server):
    body = httpx.get(f"{server}/health", timeout=30).json()
    assert body["status"] == "healthy", body
    assert set(body["modules"]) == {"document_intelligence", "nwis_backend", "physics_predictive", "evidence"}
    assert all(m["status"] == "healthy" for m in body["modules"].values())


def test_authentication_is_enforced_on_every_group(server, key):
    if not key:
        pytest.skip("server has no API key configured (auth disabled) -- nothing to enforce")
    for path in ("/api/v1/jobs", "/api/v2/wells", "/api/v3/physics/status"):
        assert httpx.get(f"{server}{path}", timeout=20).status_code == 401, path
        assert httpx.get(f"{server}{path}", headers={"X-API-Key": "wrong"}, timeout=20).status_code == 401, path
        assert httpx.get(f"{server}{path}", headers={"X-API-Key": key}, timeout=20).status_code == 200, path


def test_nwis_engines_return_real_data(api):
    wells = api.get("/api/v2/wells").json()
    assert wells["total"] >= 12
    assert api.get("/api/v2/wells/15%2F9-F-12").json()["well"]["well_id"] == "15/9-F-12"
    ranked = api.get("/api/v2/offset_rank/WELL-HGJ-012", params={"depth": 1500}).json()
    assert ranked["total_ranked"] > 0
    hard = api.get("/api/v2/offset_rank/WELL-HGJ-012", params={"depth": 1500, "max_distance_km": 10}).json()
    assert hard["hard_filter_applied"] is True and 0 < hard["total_ranked"] < ranked["total_ranked"]
    assert api.get("/api/v2/stratigraphic_depth_track/WELL-HGJ-012", params={"depth": 1500}).json()["wells_aligned"] > 0
    assert api.get("/api/v2/map/wells", params={"center_well_id": "WELL-HGJ-012", "radius_km": 15}).json()["radius_filter_applied"]


def test_physics_websocket_streams_over_a_real_socket(api, server):
    from websockets.sync.client import connect

    api.post("/api/v3/physics/start")
    try:
        with connect(server.replace("http", "ws") + "/api/v3/physics/stream", open_timeout=10) as ws:
            import json

            frames = [json.loads(ws.recv(timeout=10)) for _ in range(3)]
    finally:
        api.post("/api/v3/physics/pause")
        api.post("/api/v3/physics/reset")
    seq = [f["sequence"] for f in frames]
    assert seq == sorted(seq) and len(set(seq)) == 3
    assert frames[0]["provenance"]["tier"] == "SYNTHETIC"


def test_evidence_serves_pdfs_and_rejects_traversal(api):
    from app.core.config import EVIDENCE_PDF_DIR

    name = sorted(p.name for p in EVIDENCE_PDF_DIR.glob("*.pdf"))[0]
    ok = api.get("/api/evidence", params={"name": name})
    assert ok.status_code == 200 and ok.content[:5] == b"%PDF-"
    for hostile in ("../../.env", "..\\..\\.env", "/etc/passwd", "C:\\Windows\\win.ini"):
        assert api.get("/api/evidence", params={"name": hostile}).status_code == 400
    assert api.get("/api/evidence", params={"name": "missing.pdf"}).status_code == 404


def test_real_multi_connection_concurrency_stays_correct(server, key):
    """Genuinely parallel connections (separate sockets/threads), mixed across
    services. NWIS calls are kept few so the shared 60/min limiter isn't the thing under test."""
    headers = {"X-API-Key": key} if key else {}
    checks = [
        ("/api/v1/health", lambda b: b["status"] == "healthy"),
        ("/api/v3/physics/status", lambda b: "is_running" in b),
        ("/api/v3/predictive/models", lambda b: isinstance(b, list) and b),
        ("/api/evidence/health", lambda b: b["status"] == "healthy"),
        ("/api/v2/wells/WELL-HGJ-012", lambda b: b["well"]["well_id"] == "WELL-HGJ-012"),
        ("/health", lambda b: b["status"] == "healthy"),
    ]
    failures: list[str] = []

    def worker(i: int):
        with httpx.Client(base_url=server, headers=headers, timeout=60) as c:
            for path, check in (checks[i % len(checks):] + checks[: i % len(checks)]):
                r = c.get(path)
                if r.status_code != 200 or not check(r.json()):
                    failures.append(f"[{i}] {path}: {r.status_code} {r.text[:120]}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(8)))
    assert failures == [], failures


@pytest.mark.parametrize("port", [8001, 8002, 8003, 4100])
def test_retired_service_ports_are_closed(port):
    """The old per-module servers and the Node evidence server are not needed (and not running)."""
    with socket.socket() as s:
        s.settimeout(1)
        assert s.connect_ex(("127.0.0.1", port)) != 0, f"something is still listening on :{port}"


@pytest.mark.skipif(os.environ.get("NWIS_LIVE_INGEST") != "1", reason="writes to real runtime data; set NWIS_LIVE_INGEST=1 to run")
def test_live_pdf_ingestion_round_trip(api):
    import time

    pdf = BACKEND.parent / "modules" / "01_document_intelligence" / "data" / "sample_docs" / "synthetic_oil_india_ddr.pdf"
    resp = api.post("/api/v1/ingest", files={"file": ("live_ingest_test.pdf", pdf.read_bytes(), "application/pdf")})
    assert resp.status_code == 202
    job = resp.json()["job_id"]
    for _ in range(120):
        status = api.get(f"/api/v1/jobs/{job}").json()
        if status["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)
    assert status["status"] == "COMPLETED", status
