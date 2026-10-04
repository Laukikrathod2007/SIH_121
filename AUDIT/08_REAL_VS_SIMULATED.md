# Real vs. Synthetic vs. Simulated — Complete Data Boundary Map

**Date:** 2026-10-04
**Classifications used:** REAL SOURCE DATA, SYNTHETIC DATA, DERIVED DATA, STATIC COMMITTED OUTPUT, RUNTIME GENERATED, SIMULATED REPLAY.

---

## Master dataset table

| Dataset | Location | Classification | Generation Method | Record Count | Consumer | Used in Normal Session? | Status |
|---|---|---|---|---|---|---|---|
| Synthetic wells | `modules/02_nwis_backend/data/synthetic/wells.json` | SYNTHETIC DATA | `generate_testbed.py`, fabricated Assam-Arakan field | 12 | `data_store.py` | Y | STATIC COMMITTED OUTPUT, default-loaded |
| Synthetic trajectories | `.../synthetic/trajectories.json` | SYNTHETIC DATA | same | 12 | `data_store.py` | Y | STATIC COMMITTED OUTPUT |
| Synthetic formation tops | `.../synthetic/formation_tops.json` | SYNTHETIC DATA | same | 97 | `data_store.py` | Y | STATIC COMMITTED OUTPUT |
| Synthetic drilling events | `.../synthetic/drilling_events.json` | SYNTHETIC DATA | same | 39 | `data_store.py` | Y | STATIC COMMITTED OUTPUT |
| Synthetic telemetry | `.../synthetic/telemetry_stream.json` | SYNTHETIC DATA | same, one well only | 3,600 records | `data_store.py` | Y | STATIC COMMITTED OUTPUT |
| `real_casing_records_all.json` | `real_data/` | REAL SOURCE DATA (extracted) | Module 01 extraction of real Volve PDFs | 10 | `data_store.py` (additive) | Y | ADDITIVELY MERGED at live startup |
| `real_formations_fresh.json` | `real_data/` | REAL SOURCE DATA (extracted, filtered) | Module 01 extraction | 43 raw → filtered to 2 real wells, depth-sanity-filtered | `data_store.py` (additive) | Y | ADDITIVELY MERGED |
| `real_events_depth_tagged_fresh.json` | `real_data/` | REAL SOURCE DATA (extracted) | Module 01 extraction | 33 raw → 5 live (filter + dedup) | `data_store.py` (additive) | Y | ADDITIVELY MERGED — confirmed 39+5=44 matches live `/api/v2/health` exactly |
| `real_events_module01.json` | `real_data/` | REAL/DERIVED (broader set) | Module 01 extraction | 119 | **Not referenced by `data_store.py`** | **N** | UNVERIFIED consumer — appears orphaned relative to the live store |
| `real_trajectories.json` | `real_data/` | REAL/DERIVED (older/partial) | `parse_real_trajectories.py` | 2 | Superseded by the WITSML variant | N | STATIC, orphaned |
| `real_trajectories_witsml.json` | `real_data/` | REAL → DERIVED (minimum-curvature computed from real survey angles) | `extract_real_trajectories.py`/`parse_witsml_trajectories.py` | 22 station-sets, only 2 reachable live | `data_store.py` (additive, keyed to 2 wells) | Y (2 of 22 entries) | ADDITIVELY MERGED, mostly unreachable |
| `REAL_WELL_F12`, `REAL_WELL_F1` | `data_store.py` source (hardcoded Python objects) | REAL SOURCE DATA (hand-transcribed) | Hardcoded in source, not JSON-loaded | 2 | `data_store.py`, appended to `all_wells` | Y | STATIC/HARDCODED — confirmed 12+2=14 matches live health exactly |
| `real_data/volve/*.pdf` | `real_data/volve/` | REAL SOURCE DATA | Genuine public Equinor Volve field documents | 14 PDFs | Source input to extraction scripts; 3 copied into `evidence-server/pdfs/` | Indirectly (as extracted JSON) | SOURCE ARCHIVE |
| `real_data/witsml/` | `real_data/witsml/` | REAL SOURCE DATA | Genuine WITSML XML exports, 23 real wells | 23 subdirs | Source input to `parse_witsml_trajectories.py` | N | SOURCE ARCHIVE, archival only |
| `real_data/_tmp_results/` | `real_data/_tmp_results/` | DERIVED (intermediate) | Module 01 extraction run dumps across iterations | 15+ JSON, 4 round subdirs | Standalone scripts only during one-time extraction | N | STANDALONE SCRIPT ARTIFACT / scratch |
| REAL-trained hazard models | `real_data/real_trained_models/*.joblib` | DERIVED (ML, real-data-trained) | `train_hazard_models_real.py` | 2 files | **Nobody** — confirmed by hash comparison and loader-path grep | **N** | ORPHANED — trained, never loaded (see `06_ML_AND_MODEL_AUDIT.md`) |
| Synthetic-trained hazard models | `modules/02_nwis_backend/data/models/*.joblib` | SYNTHETIC-DATA-TRAINED | `train_hazard_models.py` | 4 files | `hazard_predictor.py` — **what the live system actually serves** | Y | STATIC COMMITTED OUTPUT, actively loaded |
| Module 04 synthetic physics data | In-memory only, never written to disk as a dataset | SIMULATED / RUNTIME GENERATED | `SyntheticDataGenerator.generate_scenario_run()` with a physics quality gate | Ephemeral | Only `dataset_reporter.py` (standalone, never fully run — output file doesn't exist) and unit tests | **N** | NEVER PERSISTED, never touches a live API |
| Module 01 output JSONs | `modules/01_document_intelligence/data/output/*.json` | DERIVED DATA | Real PDF in → real extracted JSON out | Dozens | Module 01 API (job results) | Y | DERIVED, confirmed genuine via spot-check against a real 10.9MB root-level PDF |
| `modules/01_document_intelligence/data/jobs.db` | same dir | RUNTIME GENERATED (SQLite) | Job tracking | 65,536 bytes, 86 real rows | Module 01 API | Y | RUNTIME GENERATED, genuinely non-empty |
| `evidence-server/pdfs/` | `evidence-server/pdfs/` | MIXED: synthetic + real | 39 synthetic DDR fixtures + 3 real Volve docs | 42 files | Evidence Viewer on citation click | Y | STATIC COMMITTED OUTPUT, mixed, serves the live viewer |
| `nwis-map-package/server/pdfs/` | `nwis-map-package/server/pdfs/` | SYNTHETIC DATA only | Same 39 synthetic fixtures, no real docs | 39 files | Superseded standalone package, not the live app | UNVERIFIED (likely N) | STATIC COMMITTED OUTPUT, synthetic-only, superseded |
| `database/schema.sql` + Postgres/PostGIS/pgvector/TimescaleDB | `database/` | N/A (schema) / DERIVED (seed) | Hand-written DDL; `migrate_seed.py` loads the synthetic testbed once | N/A / one historical seed run (per dated README claim) | **Nothing at runtime** — confirmed via exhaustive grep, zero `psycopg`/`sqlalchemy`/`asyncpg` imports anywhere outside `database/` itself; **the Docker container is not even running on this machine right now** | **N** | BUILT + SEEDED once (historically) but **NOT RUNTIME-CONNECTED** — confirmed with certainty, not assumed |

---

## What a normal user session actually touches

When a user opens the app and clicks through Dashboard → Nearby Wells → Offset Map → Document Ingestion → Knowledge Search, the session touches exactly:

1. **Module 02's in-memory `NWISDataStore`**: 12 synthetic wells/trajectories/97 formation tops/39 events/3,600 telemetry records from `data/synthetic/*.json`, additively merged with 2 real wells, their real trajectories, filtered real formation tops, 5 deduped real events, and 10 real casing records from `real_data/*.json`.
2. **Module 02's hazard-prediction `.joblib` models** from `data/models/` — trained on synthetic data only, confirmed by hash, never the orphaned `real_data/real_trained_models/` ones.
3. **Module 01's SQLite `jobs.db`** (86 real rows) and `data/output/*.json` — genuinely derived from real uploaded PDFs.
4. **`evidence-server/pdfs/`** (39 synthetic + 3 real) when a citation is opened.

**Never touched by a normal session**: the orphaned REAL-trained models; the entire `database/` layer (not running, not imported anywhere); module 04's synthetic-generator output (ephemeral, consumed only by an unused reporter script and tests); the raw `real_data/witsml/` and `_tmp_results/` archives (source/scratch material for already-run, one-time extraction scripts); `real_events_module01.json` and the superseded `real_trajectories.json`; `nwis-map-package/server/pdfs/`.

---

## Hardcoded/simulated-value findings (repository-wide pattern search)

Search covered: `Math.random`, `random(`, `demo`, `mock`, `dummy`, `placeholder`, `sample`, `fallback`, `FIXME`, `TODO`, `hardcoded`, `illustrative`, `"not measured"`, `simulated`, `replay`, `fake`, `stub`, plus hardcoded coordinates/well-IDs/risk values/performance metrics/fake delays. Legitimate rendering constants (`GLOBE_RADIUS`, port numbers, CSS, etc.) are excluded as non-findings per instruction.

| # | File:line | What | Intentional | User-visible | Confusable with real data | Status |
|---|---|---|---|---|---|---|
| 1 | `frontend/src/pages/RiskPredictionPage.tsx:38-48,178-181,199,209` | `featureImportances` array; ROC-AUC 0.949, PR-AUC 0.946, Lead Time 120s, Inference Latency 24.53ms | Y, explicitly disclosed | Y | **No** — every figure is labeled "(illustrative — not measured)" inline | SIMULATED, correctly disclosed |
| 2 | `frontend/src/components/layout/Header.tsx:79,85,92,95` | Idle-state fallback constants (`2450.0`, `2315.6`, `'Barail Sand'`, `'0.250'`) shown when `telemetry` is null | Y (UI needs a non-blank state) | Y | **Yes** — nothing on-screen distinguishes this from live telemetry | HARDCODED — real, pre-existing UI risk |
| 3 | `frontend/src/pages/SimulatorPage.tsx:33,261,267,272,276` | Numeric fallbacks (`\|\| 1.29`, `\|\| 2435`, `\|\| 242`, `\|\| 0.02`, `\|\| 118`) when telemetry fields are null | Y | Y | **Yes** — same lack-of-distinction issue as #2 | HARDCODED |
| 4 | `modules/01_document_intelligence/api/routes/results.py:127-183` (`/results/{doc_id}/benchmark`) | Static competitor comparison table (Reducto/LandingAI/Tesseract figures) | Y | **No — confirmed zero callers anywhere in the live frontend** | N today | HARDCODED, dormant/unused |
| 5 | `modules/04_physics_engine/api/server.py:214-241` (`_health_payload()`) | Top-level `"status": "healthy"` hardcoded unconditionally, never derived from an actual liveness check (unlike module 01's health, which does real import checks) | Uncertain — looks like an oversight | Y (`/health` endpoint) | Yes — an operator could see "healthy" even if the sim loop silently died | STATIC HEALTH RESPONSE — flag for a future fix, not fixed this pass |

### Confirmed legitimate (not findings)
- `hazard_predictor.py`'s `trained_model`/`heuristic_fallback` disclosure, surfaced honestly to the UI via a real badge — exemplary, not a finding.
- `live/replay_engine.py`'s "Live Replay" — extensively and honestly disclosed as trajectory-driven depth progression through real stored data, labeled "Replay" in the UI, not hidden.
- `PdfEvidenceViewer.tsx`'s honest "source document not found" message for events with no real ingested PDF — a deliberate anti-fabrication design choice.
- Default well-ID fallbacks shown only in empty/loading states (`Header.tsx`'s `WELL-NHK-001` option, `NearbyWellsPage.tsx`'s initial `WELL-NHK-002` state) — reasonable, low-risk, overwritten once real data loads.
- `useCommandCenterData.ts`'s defensive guard against module 02's real backend quirk (telemetry endpoint always returns one synthetic well's data regardless of requested `well_id`) — the frontend correctly discards mismatched data rather than mislabeling it. The underlying module 02 behavior is a genuine backend limitation, not a frontend fabrication.
- No `Math.random()` calls found anywhere in `frontend/src` generating fake metrics.

### The one new, not-previously-documented finding
**Module 04's `/health` endpoint's top-level `status` field is a static string, never computed from a real check** — every other field in the same response (`engine.*`, `predictive.*`) is live-computed, but `status` itself is not. This is a real, if minor, monitoring-honesty gap: the health endpoint could theoretically report "healthy" while the simulation loop has actually crashed. Not fixed in this audit pass (audit-only phase); flagged for a future targeted fix.
