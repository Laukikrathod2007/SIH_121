"""
API Endpoint Integration Tests.
"""

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from app.main import app


def run_api_tests():
    with TestClient(app) as client:
        # Test Root & Health
        root_resp = client.get("/")
        assert root_resp.status_code == 200
        assert root_resp.json()["status"] == "operational"

        health_resp = client.get("/api/v1/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # Test Wells
        wells_resp = client.get("/api/v1/wells")
        assert wells_resp.status_code == 200
        data = wells_resp.json()
        assert data["total"] > 0

        first_well_id = data["wells"][0]["well_id"]
        detail_resp = client.get(f"/api/v1/wells/{first_well_id}")
        assert detail_resp.status_code == 200

        map_resp = client.get("/api/v1/map/wells")
        assert map_resp.status_code == 200

        # Test Analysis & DORS
        analyze_resp = client.get(f"/api/v1/analyze/{first_well_id}?depth=3000")
        assert analyze_resp.status_code == 200
        assert "offset_rankings" in analyze_resp.json()

        # Test Corridors
        corridors_resp = client.get(f"/api/v1/corridors/{first_well_id}?depth=3000")
        assert corridors_resp.status_code == 200

        # Test Telemetry
        telemetry_resp = client.get(f"/api/v1/telemetry/{first_well_id}?depth=3000")
        assert telemetry_resp.status_code == 200

        # Test Document Jobs
        jobs_resp = client.get("/api/v1/documents/jobs")
        assert jobs_resp.status_code == 200

        # Test Document Templates
        templates_resp = client.get("/api/v1/documents/templates")
        assert templates_resp.status_code == 200


if __name__ == "__main__":
    run_api_tests()
    print("[PASS] All API endpoint tests passed!")
