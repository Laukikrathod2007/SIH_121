"""
Unit Tests for Well Intelligence, DORS Engine, and Stratigraphic Correlator.
"""

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.modules.well_intelligence.services.dors_engine import haversine_km, compute_dors
from app.modules.well_intelligence.services.orchestrator import NWISOrchestrator


def test_data_store_and_dors():
    store = NWISDataStore()
    store.load()
    assert store.is_loaded() is True
    assert len(store.all_wells) > 0

    # Haversine distance test
    dist = haversine_km(27.4728, 95.3467, 27.4912, 95.3689)
    assert dist > 0.0

    # Orchestrator full analysis test
    active_well = store.active_well_id
    orchestrator = NWISOrchestrator(store)
    analysis = orchestrator.analyze(active_well, current_depth_m=3200.0)

    assert analysis.active_well_id == active_well
    assert len(analysis.offset_rankings) > 0
    assert len(analysis.hazard_assessments) > 0


if __name__ == "__main__":
    test_data_store_and_dors()
    print("[PASS] All Well Intelligence & DORS tests passed!")
