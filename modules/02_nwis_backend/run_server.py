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
# Train hazard prediction models (see ml/train_hazard_models.py)
# ---------------------------------------------------------------------------
if "--train-ml" in sys.argv:
    from ml.train_hazard_models import main as train_ml_main
    train_ml_main()
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


def _ensure_api_key() -> str:
    """Secure-by-default, matching modules/01_document_intelligence/run_server.py:
    generate an API key on first run if none exists and persist it to .env,
    so this API doesn't run wide open with zero setup burden."""
    from dotenv import load_dotenv, set_key
    env_path = MODULE_ROOT / ".env"
    load_dotenv(env_path, override=False)

    existing = os.environ.get("NWIS_API_KEY", "").strip()
    if existing:
        return existing

    # IMPORTANT: generate the key with stdlib `secrets` directly rather than
    # importing auth.generate_api_key(). Importing the auth module executes
    # its module-level `API_KEY = os.environ.get("NWIS_API_KEY", ...)` — if
    # that happens here, BEFORE os.environ is populated below, the auth
    # module's API_KEY constant freezes empty for this process's entire
    # lifetime (Python caches modules; a later os.environ assignment doesn't
    # retroactively re-run it). That bug was real and reproduced: the very
    # first run after generating a fresh key started the server with auth
    # silently disabled, working correctly only after a second restart.
    import secrets
    new_key = secrets.token_urlsafe(32)
    env_path.touch(exist_ok=True)
    set_key(str(env_path), "NWIS_API_KEY", new_key)
    os.environ["NWIS_API_KEY"] = new_key
    print("=" * 60)
    print("  No NWIS_API_KEY found — generated one and saved it to .env")
    print(f"  API key: {new_key}")
    print("  Send it as header: X-API-Key: <key above>")
    print("  (Delete NWIS_API_KEY from .env to disable auth entirely.)")
    print("=" * 60)
    return new_key


if __name__ == "__main__":
    # Auto-generate data if missing
    data_check = MODULE_ROOT / "data" / "synthetic" / "wells.json"
    if not data_check.exists():
        print("  No testbed data found. Generating synthetic data first...")
        sys.path.insert(0, str(MODULE_ROOT / "data" / "synthetic"))
        from generate_testbed import generate_all
        generate_all()

    _ensure_api_key()

    # NWIS_ENV controls dev vs. production behavior, matching Module 01 —
    # auto-reload (the previous unconditional default) drops any benefit of
    # keeping a long-lived server around and isn't appropriate outside active
    # development.
    env = os.environ.get("NWIS_ENV", "dev").lower()
    is_prod = env == "production"
    host = os.environ.get("NWIS_HOST", "0.0.0.0")
    port = int(os.environ.get("NWIS_PORT", "8002"))

    print("\n" + "=" * 60)
    print("  NWIS Backend Intelligence API — Module 02")
    print("  Engines: DORS | Stratigraphy | Risk Corridors | 4-Pillar")
    print("=" * 60)
    print(f"  Mode:      {'production' if is_prod else 'dev'} (set NWIS_ENV=production to deploy)")
    print(f"  Server:    http://{host}:{port}")
    print(f"  Docs:      http://{host}:{port}/docs")
    print(f"  Health:    http://{host}:{port}/api/v2/health")
    print(f"  Map Data:  http://{host}:{port}/api/v2/map/wells")
    print("=" * 60 + "\n")

    if is_prod:
        uvicorn.run("server:app", host=host, port=port, reload=False, log_level="info")
    else:
        uvicorn.run(
            "server:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=[str(MODULE_ROOT)],
            log_level="info",
        )
