# eRTMAC-NWIS — SIH 26121

DRILLWISE (internal system name: eWIS — eWell Intelligence System). An
AI-powered offset-well intelligence platform for Oil India Limited, built
against Problem Statement 26121.

## How this repo maps to the problem statement's 7 outcomes

**The folder numbering under `modules/` does NOT map 1:1 to the PS's 7
outcomes** — this caused real confusion once already (see
`logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md`), so it's spelled out
explicitly here rather than left implicit. `modules/` follows a different
split — independently-deployable services grouped by shared runtime/data
dependencies, not by PS outcome:

| PS Outcome | What it asks for | Where the real code actually lives |
|---|---|---|
| i. Extraction (AI/NLP/OCR) | Structure historical drilling reports | `modules/01_document_intelligence/` |
| ii. Map-based nearby wells | Interactive map, user-defined radius | `modules/02_nwis_backend/engines/dors_engine.py` + `frontend/src/pages/NearbyWellsPage.tsx` |
| iii. Searchable knowledge repository | Events, lessons learned, mitigations | `modules/02_nwis_backend/search/knowledge_search.py` + `frontend/src/pages/HistoricalIntelligencePage.tsx`, `CopilotPage.tsx` |
| iv. Geological/drilling/reservoir correlation | Cross-well correlation by depth/formation | `modules/02_nwis_backend/engines/stratigraphic_correlator.py` + `frontend/src/pages/GeologicalCorrelationPage.tsx` |
| v. Predictive risk analytics | Mud loss, stuck pipe, kick, etc. | `modules/02_nwis_backend/engines/risk_corridor_engine.py` (live) + `modules/04_physics_engine/` + `modules/05_predictive_analytics/` (physics-based ML, wired over `/api/v3`) |
| vi. Real-time alerts | Proactive, ahead-of-bit warnings | `modules/02_nwis_backend/engines/risk_corridor_engine.py` + `modules/05_predictive_analytics/predictive/alert_advisory_engine.py` + `frontend/src/pages/AlertsAdvisoryPage.tsx` |
| vii. Unified dashboard | Single-pane view, field + office use | `frontend/` (the whole app, not one folder) |

**Why `modules/02_nwis_backend` alone covers outcomes ii, iii, iv, and vi**:
those four engines share one in-memory data store and call each other
directly at runtime (alerts depend on corridors, corridors depend on DORS
rankings, DORS uses stratigraphic correlation) — they are one cohesive
intelligence engine, not four independent services. Splitting them into
separate deployables purely to match the PS's numbering would trade a
working, tested system for premature distributed-systems complexity.

**Why `modules/` skips straight from `02` to `04`**: `03_physics_engine`
existed briefly as a combined module (ported from a teammate's branch) and
was then split into `04_physics_engine` and `05_predictive_analytics` to
match that branch's own internal numbering — the `03` slot was removed, not
renumbered. See logger Step 12 for the full history.

## Directory guide

- `modules/01_document_intelligence/` — OCR + NLP extraction pipeline (FastAPI, port 8001)
- `modules/02_nwis_backend/` — DORS ranking, stratigraphic correlation, knowledge search, risk corridors, alerts (FastAPI, port 8002)
- `modules/04_physics_engine/` — drilling-physics digital twin + ML data pipeline; **this module owns the actual FastAPI app and WebSocket** exposed over `/api/v3` (port 8003) — it imports module 05's predictive code into itself via a `sys.path` insert in `api/server.py`
- `modules/05_predictive_analytics/` — rule engine + isolation forest + XGBoost hazard fusion; **no standalone server of its own** — its `predictive/` package is imported into and served by module 04's process (see above; this corrects an earlier, backwards version of this line — verified in `AUDIT/01_CODEBASE_MAP.md` §4 and `AUDIT/02_CORE_INTEGRATION.md`)
- `frontend/` — the React cockpit, talking to all three backends above
- `database/` — PostgreSQL/PostGIS/pgvector/TimescaleDB schema (OSDU/WITSML/PPDM-aligned), **not yet wired into modules 01/02's live storage** — a standalone, verified-working layer for a future migration, not a live cutover
- `real_data/` — real Equinor Volve field documents/trajectories pulled for benchmarking, plus the parsing/validation scripts used against them
- `logger/` — the running, honest build log (`04_STEP_BY_STEP_IMPLEMENTATION_LOG.md`) and supporting architecture/research docs — the authoritative source for what's actually been built, tested, and found, in chronological order
- `research/` — domain research corpus (competitor platforms, standards, drilling physics)

## Running it

Each module runs independently:

```bash
cd modules/01_document_intelligence && python run_server.py   # :8001 (documented default; verified by actually running it — see AUDIT/02_CORE_INTEGRATION.md)
cd modules/02_nwis_backend && python run_server.py             # :8002 (documented default; verified clean, no port conflict on this machine as of this check)
cd modules/04_physics_engine && python run_server.py           # :8003 — run from THIS directory, not from repo root with `-m`.
                                                                #   The previously-documented `cd modules/04_physics_engine/api && python -m modules.04_physics_engine.run_server`
                                                                #   is verified BROKEN (raises `ModuleNotFoundError: No module named 'modules'`) because no
                                                                #   `modules/__init__.py` exists — `modules` only resolves as an implicit namespace package
                                                                #   from the repo root, not from inside modules/04_physics_engine/api. Plain `python run_server.py`
                                                                #   from inside modules/04_physics_engine/ works directly; see AUDIT/02_CORE_INTEGRATION.md.
cd frontend && npm run dev                                     # :5173
cd database && docker compose up -d                            # :5433 (Postgres — not yet consumed by 01/02)
```

See `logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md` for what's actually been
verified working, what's still open, and the real bugs found and fixed along
the way — that log is more current and more reliable than any status claim
in the earlier planning documents at this directory's root
(`EVALUATOR_ROADMAP_AND_FINAL_CONCLUSION.md` etc.), which predate most of the
real engineering and were written before the "100% ready" claims in them
were actually tested.
