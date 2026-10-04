# eRTMAC-NWIS Database Layer

A PostgreSQL schema for SIH 26121, modeled on the three standards the oil & gas
industry is actually converging on:

- **PPDM** (Professional Petroleum Data Management) — the master/reference
  data layer (wells, fields, operators, formations).
- **WITSML** (Wellsite Information Transfer Standard) — the work-product
  (drilling) data layer (trajectories, formation tops, drilling events, NPT
  records, mud properties, telemetry).
- **OSDU** (Open Subsurface Data Universe) — the master / work-product /
  derived three-tier separation this schema is organized around, and the
  idea of separating data from the applications that consume it.

Every table in `schema.sql` has a comment pointing at the real Pydantic model
or engine in this repo it was grounded in — nothing was invented without a
source. See that file's header for the exact list.

## Why three extensions, not a generic schema

This problem genuinely has three different data shapes, and each gets its own
purpose-built Postgres extension instead of being forced into plain columns:

- **PostGIS** — well locations and trajectory stations as real
  `geography` points, with GiST spatial indexes. This is what actually
  replaces the ad hoc haversine float-math currently in
  `modules/02_nwis_backend/engines/dors_engine.py`'s spatial scoring.
- **pgvector** — persistent, HNSW-indexed semantic search embeddings
  (`event_embeddings`), instead of recomputing them in-memory on every
  query the way `modules/02_nwis_backend/search/knowledge_search.py`
  currently does.
- **TimescaleDB** — `telemetry_records` as a hypertable, for the 1Hz/25Hz
  sensor time-series at real rig data volumes (the current SQLite-backed
  approach won't scale to that).

## Setup

```bash
cd database
docker compose up -d --build   # builds Postgres 16 + PostGIS + TimescaleDB + pgvector
pip install -r requirements.txt
python migrate_seed.py          # loads the synthetic testbed + real Volve data
```

The database listens on **port 5433** (not 5432) — this machine already runs
an unrelated project's Postgres container on 5432.

Connect: `psql "host=localhost port=5433 dbname=nwis user=nwis password=nwis_dev_password"`

To actually use this database from module 02 instead of just populating it,
set (in `modules/02_nwis_backend/.env` or the process environment):

```
NWIS_DATABASE_URL=postgresql://nwis:nwis_dev_password@localhost:5433/nwis
```

**Verified working end-to-end** (2026-10-04, Phase 1 foundation pass):
`docker compose up -d --build` -> clean schema init with zero errors ->
`python migrate_seed.py` run twice in a row produced byte-identical row
counts (14 wells / 1691 trajectory stations / 105 formation tops / 50
events / 6 casing records / 3600 telemetry records / 45 embeddings) —
genuine idempotency, not assumed. `modules/02_nwis_backend`'s
`pytest tests/` (14 tests: schema/seed-idempotency/well-CRUD/geo-filtering/
provenance/API-contract) passed against this live container. `run_server.py`
started with `NWIS_DATABASE_URL` set, and `GET /api/v2/wells/15%2F9-F-12`
and `GET /api/v2/map/wells?center_well_id=15%2F9-F-12&radius_km=5` were
curled live and returned the real Volve well with `source_type: "REAL"`
and its one real offset well (`15/9-F-1`, 5m away) via an actual PostGIS
`ST_DWithin` query — not inferred, actually executed. Separately, the
original 2026-09-28 verification (12 synthetic wells / 1245 stations / 97
tops / 39 events / 3600 telemetry, pgvector cosine search, TimescaleDB
`time_bucket()`) also still holds.

Note: this machine's shared Python environment has a `sentence-transformers`
→ TensorFlow → protobuf version conflict unrelated to this project (some
other installed package's TF pin). `migrate_seed.py` sets `USE_TF=0` before
importing `sentence_transformers` to force the PyTorch backend and avoid it
entirely — no TF is needed here.

## Migration path — Phase 1 status (2026-10-04)

`modules/01_document_intelligence` and `modules/02_nwis_backend` are real,
independently working FastAPI services, previously live-tested extensively,
currently backed by SQLite (module 01's job store) and JSON files (module
02's synthetic testbed) plus in-process computation. **This database layer
still does not replace that storage wholesale, and module 01 has not been
changed to use it at all.**

Module 02 now has a genuine, opt-in, database-backed path for ONE
representative vertical slice — active well lookup -> nearby wells ->
well metadata — proving the architecture end to end rather than describing
it. See `modules/02_nwis_backend/db/` and that module's own documentation
for exactly what moved and what didn't. Everything else in module 02
(DORS ranking, risk corridors, telemetry replay, semantic search,
formations/casing/trajectory detail) is unchanged and still runs entirely
off the in-memory `NWISDataStore`, same as before this pass. Setting
`NWIS_DATABASE_URL`/`NWIS_DB_*` is required to activate the DB-backed path
at all; leaving it unset reproduces the exact pre-migration behavior.

## Judgment calls made while building this schema

- **`trajectory_stations` is one row per survey station, not one
  `LINESTRINGZ` per well.** The application's real access pattern (see
  `stratigraphic_correlator.py`'s `tvd_at_md`/`inclination_at_md` and
  `dors_engine.py`'s `score_trajectory`) is "interpolate between the
  station immediately above/below a given MD" — a point-per-station table
  with an MD index matches that directly, without unpacking a geometry via
  `ST_DumpPoints` on every lookup. A `geography(PointZ)` column is still
  kept per station for map/3D rendering and `ST_MakeLine()` aggregation on
  demand.
- **`drilling_events.event_id` / `risk_corridors.corridor_id` /
  `alerts.alert_id` are `TEXT`, not `UUID`.** The real Pydantic default
  factories generate short hex-string business keys (`EVT-XXXXXXXX`,
  `COR-XXXXXX`), not UUIDs — the schema matches what the application
  actually generates so this is directly loadable without an ID-mapping
  layer.
- **`RiskCorridor.contributing_wells`/`contributing_events` are native
  Postgres arrays, not a join table.** This is derived/IP output, wholly
  regenerated by the engine on every run — not master data with an
  independent lifecycle of its own — so the normalization cost of a join
  table buys little here.
- **`alerts.recommended_mitigation` is `JSONB`, not a separate table.** It's
  a value object owned 1:1 by its alert and never queried independently.

## Files

- `schema.sql` — the full DDL (three tiers + provenance layer).
- `Dockerfile` — Postgres 16 + PostGIS + TimescaleDB (from
  `timescale/timescaledb-ha:pg16-all`) + pgvector built from source (no
  single official image ships all three).
- `docker-compose.yml` — brings the database up on port 5433.
- `migrate_seed.py` — loads `modules/02_nwis_backend/data/synthetic/*.json`
  (synthetic Assam-Arakan testbed) AND `real_data/*.json` (the 2 real Volve
  wells `15/9-F-12`/`15/9-F-1`, mirroring `data_store.py`'s own REAL_WELLS
  filter exactly) into the schema, with correct `source_type` throughout,
  including generating real embeddings for `event_embeddings` via the same
  `all-MiniLM-L6-v2` model `knowledge_search.py` uses. Every insert is
  idempotent — running it twice in a row produces byte-identical row counts
  (verified; see "Setup" above).
- `requirements.txt` — deps for `migrate_seed.py` only (psycopg,
  sentence-transformers).

Module 02's own `db/` package (`modules/02_nwis_backend/db/connection.py`,
`repositories.py`, `service.py`, `api_schemas.py`) and its `tests/` are
documented in that module, not duplicated here — this README stays about
the schema and seed data, not module 02's internal architecture.

`_archived_prior_design/` holds an earlier, independent design exploration
(`DATABASE_DESIGN.md`, `SETUP_GUIDE.md`, `VISUALIZATION_TECH_STACK.md`, and a
separate `schema/` split into 4 files) from a prior session, predating and
superseded by `schema.sql` at this directory's top level — renamed (not
deleted, since it wasn't created in this pass) once `schema.sql` was
confirmed as the schema actually built, verified, and running.
