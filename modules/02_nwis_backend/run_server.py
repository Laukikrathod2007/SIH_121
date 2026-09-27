"""
NWIS Module 02 — Entry Point
Run this to start the Backend Intelligence API.

Usage:
    python run_server.py            → Start server at http://localhost:8002
    python run_server.py --gen      → Generate synthetic testbed data first
    python run_server.py --validate → Run validation suite
"""

import sys
import os
from pathlib import Path

MODULE_ROOT = Path(__file__).parent
sys.path.insert(0, str(MODULE_ROOT))

# ---------------------------------------------------------------------------
# Generate testbed data
# ---------------------------------------------------------------------------
if "--gen" in sys.argv:
    print("Generating Assam-Arakan Basin testbed data...")
    sys.path.insert(0, str(MODULE_ROOT / "data" / "synthetic"))
    from generate_testbed import generate_all
    generate_all()
    print("Data generation complete! Run again without --gen to start server.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# Validation suite
# ---------------------------------------------------------------------------
if "--validate" in sys.argv:
    print("\n" + "=" * 60)
    print("  NWIS Module 02 — Validation Suite")
    print("=" * 60)

    sys.path.insert(0, str(MODULE_ROOT / "data" / "synthetic"))
    data_dir = MODULE_ROOT / "data" / "synthetic"

    # Check data files exist
    required = ["wells.json", "trajectories.json", "formation_tops.json", "drilling_events.json"]
    missing = [f for f in required if not (data_dir / f).exists()]
    if missing:
        print(f"  ERROR: Missing data files: {missing}")
        print("  Run: python run_server.py --gen")
        sys.exit(1)

    from data_store import NWISDataStore
    store = NWISDataStore()
    store.load(data_dir)

    print(f"\n  [OK] Data store loaded:")
    s = store.status()
    print(f"       Wells:     {s['wells']}")
    print(f"       Events:    {s['events']}")
    print(f"       Telemetry: {s['telemetry_records']} records")

    # Test DORS engine
    from engines.dors_engine import rank_offset_wells
    from engines.stratigraphic_correlator import formation_at_depth

    active_well = store.all_wells[0]
    test_depth = 2500.0
    active_tops = store.formation_tops_by_well.get(active_well.well_id, [])
    fm = formation_at_depth(active_tops, test_depth)

    rankings = rank_offset_wells(
        active_well=active_well,
        active_depth_m=test_depth,
        active_formation=fm.formation_name if fm else None,
        all_wells=store.all_wells,
        all_trajectories=store.all_trajectories,
        all_formation_tops=store.formation_tops_by_well,
        all_events=store.events_by_well,
        top_n=5,
    )
    print(f"\n  [OK] DORS Engine: Ranked {len(rankings)} offset wells at {test_depth:.0f}m")
    if rankings:
        r = rankings[0]
        print(f"       Top offset: {r.well_name} | DORS={r.dors_score:.3f} | Dist={r.distance_km:.1f}km")

    # Test Risk Corridor Engine
    from orchestrator import NWISOrchestrator
    orchestrator = NWISOrchestrator(store)
    result = orchestrator.analyze(active_well.well_id, test_depth)

    print(f"\n  [OK] Full Analysis Complete:")
    print(f"       Formation at {test_depth}m: {result.formation_at_bit}")
    print(f"       Overall Risk Level: {result.overall_risk_level.value}")
    print(f"       Active Corridors: {len(result.active_risk_corridors)}")
    print(f"       Hazard Assessments: {len(result.hazard_assessments)}")
    for ha in result.hazard_assessments:
        print(f"         {ha.hazard_type.value}: {ha.risk_level.value} "
              f"(composite={ha.composite_score:.3f})")

    if result.alert_message:
        print(f"\n  [ALERT] {result.alert_message}")

    print("\n  ALL VALIDATIONS PASSED — Module 02 is operational!")
    print("=" * 60)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Server Mode (default)
# ---------------------------------------------------------------------------
import uvicorn

if __name__ == "__main__":
    # Auto-generate data if missing
    data_check = MODULE_ROOT / "data" / "synthetic" / "wells.json"
    if not data_check.exists():
        print("  No testbed data found. Generating synthetic data first...")
        sys.path.insert(0, str(MODULE_ROOT / "data" / "synthetic"))
        from generate_testbed import generate_all
        generate_all()

    print("\n" + "=" * 60)
    print("  NWIS Backend Intelligence API — Module 02")
    print("  Engines: DORS | Stratigraphy | Risk Corridors | 4-Pillar")
    print("=" * 60)
    print("  Server:    http://localhost:8002")
    print("  Docs:      http://localhost:8002/docs")
    print("  Health:    http://localhost:8002/api/v2/health")
    print("  Map Data:  http://localhost:8002/api/v2/map/wells")
    print("=" * 60 + "\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        reload_dirs=[str(MODULE_ROOT)],
        log_level="info",
    )
