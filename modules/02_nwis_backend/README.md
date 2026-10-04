# NWIS Module 02 — Backend Intelligence Core

> **PS Outcomes ii, iii, iv, v, vi:** Geospatial relevance, searchable knowledge base, geological correlation, predictive risk analytics, and real-time early warnings.

## Architecture

4-engine intelligence pipeline:

```
ACTIVE BIT POSITION (depth d_t)
         │
         ├─ ENGINE 1: DORS (5-Factor Offset Relevance Scoring)
         │   S_spatial + S_formation + S_depth + S_trajectory + S_hazard
         │   → Ranked list of top-N most relevant offset wells
         │
         ├─ ENGINE 2: Stratigraphic Depth Correlator
         │   d_strat = TVD(d) − Top_TVD(Formation_k)
         │   → Eliminates "Trajectory Trap" — MD≠TVD for directional wells
         │
         ├─ ENGINE 3: Historical Risk Corridor Engine
         │   R_H(t) = 0.45·P_history + 0.35·A_sensor + 0.20·M_ML
         │   → Clusters offset events into depth corridors
         │   → Issues 15–50m lookahead early warning
         │
         └─ ENGINE 4: 4-Pillar Confidence Evaluator
             Evidence Strength + Sensor Anomaly + Data Quality + Audit Status
             → Transparent, decoupled confidence (no black box!)
```

## Quick Start

```powershell
cd c:\Users\LAUKIK\Desktop\SIH121\modules\02_nwis_backend

# Install deps
pip install -r requirements.txt

# Step 1: Generate synthetic testbed data (Assam-Arakan Basin, 12 wells)
python run_server.py --gen

# Step 2: Validate all engines
python run_server.py --validate

# Step 3: Start server
python run_server.py
```

Server starts at: **http://localhost:8002**  
API Docs: **http://localhost:8002/docs**

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v2/wells` | List all wells |
| `GET` | `/api/v2/map/wells` | GIS map data (lat/lon + metadata) |
| `GET` | `/api/v2/analyze/{well_id}?depth=2800` | **Full intelligence analysis** |
| `GET` | `/api/v2/offset_rank/{well_id}?depth=2800` | DORS ranking only |
| `GET` | `/api/v2/corridors/{well_id}?depth=2800` | Risk corridors |
| `GET` | `/api/v2/formations/{well_id}` | Formation tops |
| `GET` | `/api/v2/events?hazard_type=MUD_LOSS&formation=Tipam` | Search events |
| `GET` | `/api/v2/telemetry/{well_id}?depth=2800` | Live telemetry |
| `GET` | `/api/v2/health` | Health check |

## Synthetic Testbed

| Parameter | Value |
|---|---|
| Wells | 12 (Nahorkatiya, Moran, Baghjan, Hugrijan fields) |
| Formation Tops | 97 (Assam-Arakan authentic stratigraphy) |
| Drilling Events | 39 (authentic incidents with IADC NPT codes) |
| Telemetry | 3,600 1-Hz records with anomaly injection |
| Well Types | Vertical (50%), J-Type (35%), S-Type (15%) |

## Authentic Assam-Arakan Stratigraphy

| Formation | Typical Depth | Hazard Profile |
|---|---|---|
| Alluvium | 100–200m | N/A |
| Tipam Sandstone | 400–1200m | **Lost Circulation** (vugular) |
| Girujan Clay | 1200–1600m | **Wellbore Instability**, Stuck Pipe |
| Barail Sandstone | 1600–2200m | **Kick** (gas bearing) |
| Barail Coal-Shale | 2200–2500m | **Stuck Pipe** (swelling clays) |
| Kopili | 2500–2900m | **Lost Circulation** (fractured) |
| Sylhet Limestone | 2900–3200m | **Kick + Mud Loss** (prolific) |

## Canonical Database Layer (Phase 1 foundation, 2026-10-04)

Module 02 now has an OPT-IN, database-backed path for one representative
vertical slice: **active well lookup -> nearby wells -> well metadata**
(`GET /api/v2/wells/{id}` and `GET /api/v2/map/wells`). Everything else in
this module — DORS ranking, risk corridors, telemetry, semantic search,
live replay — is unchanged and still runs entirely off the in-memory
`NWISDataStore` described above.

**Architecture:** `server.py` route -> `db/service.py` (business logic,
response shaping, audit logging) -> `db/repositories.py` (the only file
with raw SQL) -> PostgreSQL/PostGIS (`database/schema.sql`).

**Why PostgreSQL is the source of truth for this one path:** nearby-well
lookup is fundamentally a geospatial query, and `engines/dors_engine.py`'s
`haversine_km()` float-math loop over every well in memory does not scale
and cannot use an index. PostGIS's `geography` column + GiST index lets
`ST_DWithin`/`ST_Distance` do the same geodesic distance calculation
database-side, indexed — the actual reason this slice, and not some other
endpoint, was chosen to prove the architecture (task's own reasoning, not
retrofitted).

**Enabling it** — set one of these (`.env` or process environment) and
restart the server:
```
NWIS_DATABASE_URL=postgresql://nwis:nwis_dev_password@localhost:5433/nwis
# or: NWIS_DB_HOST=localhost (+ NWIS_DB_PORT/NWIS_DB_NAME/NWIS_DB_USER/NWIS_DB_PASSWORD)
```
Leaving both unset reproduces the exact pre-migration behavior — every
route (migrated or not) is served by the in-memory store, as before this
pass. `GET /api/v2/health`'s `"database"` field reports whether a DB is
configured and currently reachable (`{"configured": true, "reachable":
false, "error": "<ExceptionClassName>"}` on failure — the exception's
class name only, never the full exception text, so a client-facing
payload never carries connection details like host/port/user); the two
migrated routes report which backend actually served a given response via
`"data_source"` (`"postgres"` or `"memory"`) in their JSON body.

**Database-failure behavior (Pass 2 hardening, 2026-10-04):** if the
database is configured but a request to it fails (connection refused,
timeout, SQL error), `GET /api/v2/wells/{id}` and `GET /api/v2/map/wells`
now return a genuine `503 Service Unavailable` instead of silently falling
back to the in-memory store. This was changed deliberately — the earlier
behavior (warn-and-fall-through to memory data) could present
possibly-stale or incomplete in-memory data as if the request had
succeeded normally, with no client-visible signal besides the
easy-to-miss `"data_source"` field. A `WellNotFoundError` (the well
genuinely doesn't exist) is unaffected and still returns `404`. If the
database is simply unconfigured, the in-memory path is unchanged, normal
dev-mode behavior — this 503 only applies when a DB is configured
(`NWIS_DATABASE_URL`/`NWIS_DB_*` is set) and the attempt to reach it fails.

**Local database setup, migration, and seeding** — see
`database/README.md`. Short version:
```bash
cd ../../database
docker compose up -d --build
pip install -r requirements.txt
python migrate_seed.py        # idempotent -- safe to run again
```

**Tests** — `pytest tests/` (`tests/test_db_foundation.py` exercises the
repository layer directly against a live DB, plus a pure-unit test of
`healthcheck()`'s error-field laundering that needs no DB at all;
`tests/test_api_well_endpoints.py` covers the in-memory fallback contract,
the DB-backed contract, AND the DB-configured-but-UNREACHABLE contract —
the last of these points `NWIS_DATABASE_URL` at an unreachable port and
asserts the new `503` behavior, needing no real Postgres/Docker either;
`tests/test_analyze_well_error_handling.py` proves `GET /api/v2/analyze/{id}`
no longer leaks raw exception text on failure). DB-dependent tests that
genuinely need a live, seeded database skip cleanly (not fail) if none is
reachable, so `pytest` still passes on a machine with no Docker running.

**What is NOT migrated**: trajectory station counts, formation tops, and
event counts/search returned by `GET /api/v2/wells/{id}` still come from
the in-memory store even when the DB path serves the well's own identity
fields — those entities have canonical tables in `database/schema.sql`
(`trajectory_stations`, `formation_tops`, `drilling_events`) but migrating
their *read* paths is separately-scoped follow-up work, not silently
implied as done here. DORS ranking, stratigraphic correlation, risk
corridors, live replay, and semantic search are entirely unmigrated and
continue to read only from `NWISDataStore`.

## Project Structure

```
02_nwis_backend/
├── run_server.py              ← START HERE
├── server.py                  ← FastAPI application
├── orchestrator.py            ← Master analysis coordinator
├── data_store.py              ← Singleton data loader
├── requirements.txt
├── engines/
│   ├── dors_engine.py         ← 5-factor DORS scoring
│   ├── stratigraphic_correlator.py  ← TVD / d_strat alignment
│   └── risk_corridor_engine.py      ← R_H(t) + 4-pillar confidence
├── models/
│   └── schemas.py             ← Pydantic data models
└── data/
    └── synthetic/
        ├── generate_testbed.py  ← Basin testbed generator
        ├── wells.json
        ├── trajectories.json
        ├── formation_tops.json
        ├── drilling_events.json
        └── telemetry_stream.json
```
