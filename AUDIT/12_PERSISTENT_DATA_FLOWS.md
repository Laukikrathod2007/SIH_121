# 12 — Persistent Data Flows (Pass 4)

**Date:** 2026-10-04. **Scope:** make the existing unified NWIS application
use one coherent, persistent PostgreSQL data layer across its major
workflows, extending the Pass 1 foundation (canonical schema +
one migrated vertical slice) and the Pass 3 unified backend — without
moving module directories, introducing a migration framework, or touching
the physics equations / ML models / risk-fusion algorithms.

## 1. Actual state before this pass (verified by reading the code, not assumed)

| Area | State found |
|---|---|
| `wells`, `trajectory_stations`, `formation_tops`, `drilling_events`, `casing_programs`, `telemetry_records`, `event_embeddings` | Seeded by `database/migrate_seed.py`, confirmed idempotent, but **only `GET /api/v2/wells/{id}` and `GET /api/v2/map/wells`** actually read from Postgres (`modules/02_nwis_backend/db/service.py`). Every other M02 route (`trajectory`, `formations`, `casing`, `events`, `events/search`, `telemetry`, `offset_rank`, `corridors`, `analyze`) ran purely off the in-memory `NWISDataStore`, loaded from `data/synthetic/*.json` + `real_data/*.json` at process startup. |
| `documents`, `document_review`, `document_extractions` | Tables existed in `schema.sql`, **0 rows**, nothing ever wrote to them. Module 01's real lifecycle (`SQLiteJobStore` for job status, `data/output/{doc_id}.json` for extraction results and review state) was completely disconnected from PostgreSQL. |
| `drilling_events` (document → knowledge-base handoff) | No code path existed connecting an approved document's extracted events to the canonical table. |
| `alerts`, `model_registry` | 0 rows. `ActiveAlert` objects (module 05's `AlertAdvisoryEngine`) lived only in an in-memory dict, never persisted; `/predictive/evaluate` reshaped and returned them but wrote nothing. |
| Physics telemetry (module 04's 25 Hz simulation) | Broadcast over WebSocket and kept in a 2000-sample in-memory ring buffer (`LiveTelemetryStreamer.historian`); never written anywhere durable. |

## 2. What changed

### A. Canonical well intelligence — extended the existing DB-backed pattern
`modules/02_nwis_backend/db/repositories.py` gained `TrajectoryRepository`,
`FormationRepository`, `CasingRepository`; `db/service.py` gained matching
service functions that reshape rows into the exact Pydantic field names the
in-memory path already returns. `server.py`'s `get_trajectory`,
`get_formations`/`get_all_formations`, `get_casing`/`get_all_casing` now
follow the identical contract `get_well`/`get_map_wells` already established
in Pass 1/2: Postgres when `NWIS_DATABASE_URL` is configured and reachable,
in-memory when unconfigured, **503 (never silent memory fallback)** when
configured but unreachable. A new `data_source` field (`"postgres"` /
`"memory"`) is now present on all these responses, matching the existing
convention on `get_well`/`get_map_wells`.

DORS ranking, risk corridors, free-text/semantic event search, and the
telemetry replay engine were **not** migrated — they stay on the in-memory
store in this pass (see §6, "not migrated").

### B. Document intelligence — new write-through, SQLite/JSON stays authoritative for module 01's own routes
New `modules/01_document_intelligence/db/` package (`repositories.py`,
`service.py`), sharing module 02's existing connection pool
(`app.modules.nwis.db.connection`) rather than opening a second one.

- `pipeline/orchestrator.py`'s `process_document()` now calls
  `db.service.sync_document()` immediately after its existing JSON save —
  UPSERTs `documents` + flattens formation/NPT/mud-property
  `ExtractedField`s into `document_extractions`.
- `api/routes/review.py`'s `/decision` and `/annotate` endpoints call
  `db.service.sync_review()` (UPSERT `document_review`) and, on **approval**
  only, `db.service.handoff_events()`.
- **Module 01's own routes (`ingest`/`status`/`results`/`review`) were not
  changed to read from Postgres** — they still read `SQLiteJobStore` and
  `data/output/*.json`, which remain authoritative for that module's own
  behavior. Postgres is the second, write-through copy this pass adds for
  downstream NWIS queries, per the task's "make seed/import operations
  repeatable" and "one authoritative source" goals for the *shared* layer —
  rewriting module 01's own read paths was judged out of this pass's budget
  and not required by the acceptance criteria, which ask for durable storage
  and retrievability, not a single code path.
- All write-through calls are **best-effort and never raise**: a database
  outage degrades silently back to JSON-file-only behavior (logged at
  `WARNING`), never fails an ingestion or a review decision that already
  succeeded on disk.

### C. Document → canonical knowledge-base handoff — conservative, honest-skip
`handoff_events()` migrates an approved document's drilling events into
`drilling_events` only when **both**:
1. the document's well_name resolves to a real `well_id`
   (`resolve_well_id()` — exact-match only, see §4), and
2. the event's `event_type` exists in the canonical `hazard_type` table.

Anything else is **counted and reported, never forced in**:
`{"migrated": N, "skipped": M, "skip_detail": [...]}`. Idempotent — keyed on
the event's own stable `event_id`, re-running a handoff twice re-upserts the
same row. `source_type` is set to `REAL` (a human-approved extraction of an
actual document, not an engine-computed `DERIVED` value).

### D. Telemetry + alerts — write-through at the existing ~1 Hz evaluate call
New `modules/04_physics_engine/db/` package. `api/server.py`'s
`POST /api/v3/predictive/evaluate` — already the real integration point the
frontend calls (see `frontend/src/context/AppContext.tsx`'s
`handleNewTelemetry`, which decimates the 25 Hz WebSocket stream to ~1 Hz
before calling it) — now also calls `db.service.sync_evaluation()`:
UPSERTs one `telemetry_records` row (unit-converted from the engine's
SI/metric channels to the schema's oilfield units — kN→klbs, bar→psi,
g/cc→ppg) and UPSERTs any `ActiveAlert`s that tick produced into `alerts`.
**The 25 Hz physics loop and WebSocket broadcast are untouched** — this
never competes with them for the event loop, and nothing about the physics
equations or ML fusion logic changed.

Alert hazard types the canonical `hazard_type` table has no row for
(`SENSOR_FAULT`, `LOST_CIRCULATION`, `TORQUE_DRAG`, `WASHOUT` — confirmed by
reading `alert_advisory_engine.py` directly) are stored with
`hazard_type = NULL` rather than rejected or coerced into a wrong code;
`alerts.hazard_type` is nullable in the schema for exactly this reason.

### E. `NWIS_DATABASE_URL` now actually configured
`Backend/.env` gained `NWIS_DATABASE_URL=postgresql://nwis:nwis_dev_password@localhost:5433/nwis`
(the value was present in `database/README.md`'s instructions but never
actually set in the unified backend's own `.env` before this pass — so the
Pass 1 vertical slice was, in practice, never active in the unified app
until now). `.env.example` documents it.

## 3. Workflow-by-workflow table

| Workflow | Previous storage | Current authoritative storage | Read/write path verified | Test evidence |
|---|---|---|---|---|
| Well identity/metadata | In-memory `NWISDataStore` | PostgreSQL (`wells`, `fields`, `operators`) when DB configured; in-memory otherwise | `GET /api/v2/wells/{id}` → `postgres`, live-curled | Pass 1/2/3 tests + this pass's rerun, all green |
| Nearby/map wells | In-memory | PostgreSQL (`ST_DWithin`/`ST_Distance`) when configured | `GET /api/v2/map/wells` → `postgres`, live-curled | Unchanged tests, rerun green |
| Trajectory stations | In-memory only | **PostgreSQL** when configured (new this pass) | `GET /api/v2/trajectory/15%2F9-F-12` → `data_source: postgres`, 438 stations, live-curled | `test_db_reachable_trajectory_served_by_postgres` (new) |
| Formation tops | In-memory only | **PostgreSQL** when configured (new) | `GET /api/v2/formations/15%2F9-F-12` → `postgres`, 7 tops; `GET /api/v2/formations` → 105 total | `test_db_reachable_formations_served_by_postgres` (new) |
| Casing programs | In-memory only | **PostgreSQL** when configured (new) | `GET /api/v2/casing` → `postgres`, 6 records, 1 well | `test_db_reachable_casing_served_by_postgres` (new) |
| Document extraction results | SQLite (job status) + JSON files | **Both**: JSON remains authoritative for module 01's own routes; **PostgreSQL `documents`/`document_extractions` added as write-through** | Real ingest of a 2-page PDF → `documents` row with resolved `well_id`; a 16-event real document re-synced → 20 `document_extractions` rows | `test_sync_document_resolves_well_and_upserts_idempotently` (new) |
| Document review decisions | JSON file field | **Both**: JSON authoritative; **PostgreSQL `document_review` added** | Live `/decision` call on a real document → `document_review` row, `reviewed=true` | Covered by live curl + `sync_review` call inside the decision-test paths |
| Document → knowledge-base event handoff | **Did not exist** | **New**: PostgreSQL `drilling_events`, gated on approval + resolvable well + mapped hazard type | Synthetic-but-schema-accurate fixture → 1 event migrated with `source_type=REAL`, `source_document_id` linked, re-run idempotent (still 1 row) | 5 new tests incl. idempotency, unmapped-type skip, missing-depth skip, unresolvable-well skip |
| Historical drilling events (read/search) | In-memory `NWISDataStore.all_events` | **Unchanged** — still in-memory for `/events`, `/events/search`, `/events/{well_id}` | Not modified this pass | N/A (out of scope, see §6) |
| Simulated telemetry | In-memory ring buffer only | **Both**: ring buffer for the 25 Hz WebSocket feed (unchanged); **PostgreSQL `telemetry_records` added** at the existing ~1 Hz evaluate call | Live sim run → 57 real rows written to `telemetry_records` with unit-converted columns, survived a full backend restart | `test_envelope_to_telemetry_row_converts_units`, `test_sync_evaluation_writes_telemetry_and_valid_hazard_alert` (new) |
| Predictive alerts | In-memory dict only | **New**: PostgreSQL `alerts`, UPSERT on `alert_id` | Live `KICK_OVERPRESSURE` scenario injection → 14 real `KICK` alerts (WARNING→CRITICAL) written and survived a restart | `test_sync_evaluation_upserts_alert_status_idempotently`, `test_sync_evaluation_nulls_unmapped_hazard_type_without_rejecting_alert` (new) |

## 4. Honest gaps found and NOT papered over

- **Well-name resolution is genuinely hard on real OCR output.** A direct
  scan of all 79 existing `data/output/*.json` files found **zero**
  documents where (a) the well_name resolves to a real `well_id` AND (b) at
  least one event has both a mapped hazard type and a non-null depth —
  i.e. the positive migration path, while implemented and tested
  (synthetically), has not yet fired on any of the pre-existing real
  extraction results. Causes, confirmed by direct inspection:
  - Most extracted `well_name` values are noise (`"REPORT"`, `"evaluation"`,
    filename fragments like `"11194EBA40_WELL-15"`) or near-misses
    (`"NHK-105"`, which is not a real well in the 14-well catalog at all).
  - `resolve_well_id()` is deliberately exact-match-only (see its own
    docstring) — a fuzzy matcher would resolve some of these correctly and
    some **wrong**, and silently attributing a document's events to the
    wrong well is worse than leaving it unmigrated.
  - 546 of 723 extracted events across the corpus have `depth_start_md_m =
    null`; `drilling_events.depth_start_md_m` is `NOT NULL` in the canonical
    schema, so these cannot be migrated as-is without inventing a depth.
  - Of M01's 12 `EventType` values, only 6 overlap with M02's canonical
    `hazard_type` table (`GAS_INFLUX`, `LOST_CIRCULATION`,
    `EQUIPMENT_FAILURE`, `DEVIATION_CONTROL`, `NPT_OPERATIONAL`, `UNKNOWN`
    are not in `hazard_type`).
  - **Found and fixed during this pass**: `tier1_native_extractor.py`'s
    filename-fallback well-name regex has a live, reproducible bug — for a
    filename shaped `{TYPE}_WELL-{id}...pdf` it extracts
    `"DDR_WELL-NHK-001"` instead of `"WELL-NHK-001"`. Per this pass's scope
    (do not rewrite extraction algorithms), this was **not** fixed in the
    extractor; instead `resolve_well_id()` strips known report-type
    prefixes (`DDR_`/`WCR_`/etc.) before matching — a data-interpretation
    workaround in the new code, not a change to module 01's own pipeline.
    Verified live: before the fix, a real ingested document's `well_id`
    stayed `NULL`; after, it correctly resolved to `WELL-NHK-001`.
  - A second pre-existing extraction artifact was observed (not fixed, out
    of scope): a depth written as `"2620,60 m"` (European decimal comma)
    parses to `262060.0` via the existing float-parsing code — a garbage
    value already present in `data/output/*.json` before this pass, now
    visible in `document_extractions.field_value` rather than hidden.
- **`FISHING_OPERATION` has zero event records anywhere** — confirmed by
  grepping the hazard-type enum, the synthetic testbed, and every
  `real_data/*.json` file. No row was invented for it, per the task's
  explicit instruction.
- **DORS ranking, risk corridors, free-text/semantic event search, and the
  telemetry replay engine remain in-memory-only** in this pass. They read
  `NWISDataStore`, not PostgreSQL. Migrating them was judged out of this
  pass's realistic scope (the task says "prioritize complete, demonstrable
  end-to-end data flows over adding new features," and A–D above already
  cover the explicitly named priority flows); doing so is natural follow-up
  work for a future pass, not attempted here.
- **`model_registry` remains empty.** No code in this pass populates it —
  module 05's `.joblib` artifacts are loaded directly from disk, never
  registered. Out of scope per the explicit instruction not to retrain or
  merge models.
- **Module 01's own API routes (ingest/status/results/review) still read
  from SQLite/JSON, not Postgres.** This is a deliberate choice (see §2.B),
  not an oversight — rewriting them was judged a larger, riskier change
  than this pass's budget, and the acceptance criteria ask for durable
  storage + retrievability, which the write-through satisfies without
  touching the read path other code already depends on.
- **Test-run side effects on the real database**: live verification during
  this pass added 4 `documents` rows (`DOC-02C8FC2441B7`,
  `DOC-958776A40799`, `DOC-D9EDAE6B8929` resync, `DOC-PASS4-VERIFY-TEST`),
  1 real `drilling_events` row (`EVT-PASS4VERIFY1`), 57 `telemetry_records`
  rows, and 21 `alerts` rows to the live Postgres instance — left in place
  per the standing safeguard against deleting runtime state. `DOC-PASS4-
  VERIFY-TEST` and `EVT-PASS4VERIFY1` are clearly-named synthetic test
  fixtures, not real operational data.

## 5. Tests added (33 new, all passing against the live database)

| File | Tests | What they prove |
|---|---|---|
| `modules/01_document_intelligence/tests/test_document_db_service.py` | 19 | Well-name resolution (exact/underscore-variant/bare-code/report-prefix-strip/junk-rejection), `ExtractedField` unwrapping, document UPSERT idempotency, handoff approval-gating, successful migration + idempotency, unmapped-hazard-type skip, missing-depth skip, unresolvable-well skip |
| `modules/04_physics_engine/tests/test_telemetry_alert_db_service.py` | 5 | Unit conversion correctness (kN→klbs, bar→psi, g/cc→ppg), telemetry+alert write, unmapped-hazard-type → NULL (not rejected), alert UPSERT idempotency on status change, unknown-well_id guard |
| `modules/02_nwis_backend/tests/test_api_well_endpoints.py` (extended) | +9 | Trajectory/formations/casing: memory-mode, 503-on-unreachable, postgres-mode-with-provenance — same contract as the pre-existing `get_well`/`get_map_wells` tests |

## 6. Full test run (this pass, `cd Backend && python run_tests.py`)

| Suite | Before this pass | After this pass |
|---|---|---|
| backend | 143 passed, 1 skipped | 143 passed, 1 skipped (unchanged) |
| document_intelligence | 3 passed | **22 passed** |
| nwis | 20 passed | **29 passed** |
| physics | 13 passed | **18 passed** |
| predictive_analytics | 19 passed | 19 passed (unchanged) |

Frontend: `npx tsc --noEmit` → 0 errors. `npm run build` → succeeds (pre-
existing chunk-size warning only, unrelated to this pass).

## 7. Restart-persistence evidence (not assumed — actually restarted)

The backend was stopped and restarted from `cd Backend && python run.py`
three times during this pass. After the final restart:

```
documents              4   (survived)
document_review        2   (survived)
document_extractions  20   (survived)
drilling_events       51   (50 seed + 1 handed-off, survived)
alerts                21   (survived)
telemetry_records   3657   (3600 seed + 57 live-written, survived)
```

`GET /api/v2/wells/WELL-NHK-001` after restart still returns
`data_source: postgres`. The database pool opens cleanly on startup
(`app.modules.nwis.db.connection.get_pool`) and closes cleanly on shutdown
(`close_pool()`, wired into `app/core/lifecycle.py` since Pass 3) — observed
in the startup log on every restart, no errors.

## 8. Live verification performed (not just HTTP status codes)

- Real PDF ingested through `/api/v1/ingest` → `documents` row written with
  correctly resolved `well_id` (after the prefix-strip fix).
- Real review decision submitted through `/api/v1/review/{id}/decision` →
  `document_review` row written, handoff attempted and correctly reported
  `skipped` with reasons for a real 16-event document (none happened to
  satisfy both migration conditions — see §4).
- Synthetic-but-schema-accurate fixture proved the **positive** migration
  path end-to-end (1 event migrated, correct provenance, idempotent).
- Live physics simulator started, a `KICK_OVERPRESSURE` scenario injected
  → 14 real `CRITICAL`/`WARNING` `KICK` alerts generated by the actual
  rule/ML fusion engine and written to `alerts`; 57 telemetry ticks written
  to `telemetry_records` with correctly converted units.
- Browser: `/app/wells`, `/app/documents`, `/app/correlation`,
  `/app/simulator` all loaded with 0 console errors against the restarted
  backend.
- `GET /api/v2/trajectory`, `/formations`, `/casing` (single-well and
  all-wells variants) all live-curled and confirmed `data_source: postgres`.

## 9. Files changed

**New:**
- `modules/01_document_intelligence/db/__init__.py`, `repositories.py`, `service.py`
- `modules/01_document_intelligence/tests/test_document_db_service.py`
- `modules/04_physics_engine/db/__init__.py`, `repositories.py`, `service.py`
- `modules/04_physics_engine/tests/test_telemetry_alert_db_service.py`
- `AUDIT/12_PERSISTENT_DATA_FLOWS.md` (this file)

**Edited:**
- `modules/02_nwis_backend/db/repositories.py` — added `TrajectoryRepository`, `FormationRepository`, `CasingRepository`
- `modules/02_nwis_backend/db/service.py` — added matching service functions
- `modules/02_nwis_backend/server.py` — `get_trajectory`/`get_formations`/`get_all_formations`/`get_casing`/`get_all_casing` now DB-first with memory fallback
- `modules/02_nwis_backend/tests/test_api_well_endpoints.py` — +9 tests
- `modules/01_document_intelligence/pipeline/orchestrator.py` — write-through call after JSON save
- `modules/01_document_intelligence/api/routes/review.py` — write-through + handoff calls on decision/annotate
- `modules/04_physics_engine/api/server.py` — write-through call in `predictive_evaluate`
- `Backend/.env`, `Backend/.env.example` — `NWIS_DATABASE_URL` now actually set

## 10. Unresolved gaps (explicit, for the next pass)

1. Module 01's own routes still read SQLite/JSON, not Postgres (§2.B, §4).
2. DORS ranking, risk corridors, semantic/structured event search, and
   telemetry replay remain in-memory-only (§4).
3. No existing real document in the current corpus has yet triggered the
   positive event-handoff path (proven correct via a synthetic fixture, not
   yet observed on a real document) — a cleaner real test document, or
   fixing the filename-regex bug noted in §4 at its source, would close
   this.
4. `model_registry` remains empty (out of scope).
5. The event-handoff's well-resolution is intentionally conservative; a
   future pass could widen it (e.g. a reviewed-and-corrected `well_id` field
   added to the review UI) without weakening the exact-match safety
   guarantee this pass relies on.
