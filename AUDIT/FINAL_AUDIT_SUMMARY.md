# SIH-26121 NWIS — Final Technical Audit Summary

**Date:** 2026-10-04
**Scope:** The complete, runtime-verified SIH-26121 application, audited against the authoritative verbatim problem statement (`research/research/PROBLEM_STATEMENT.md`). Every claim in this summary is backed by a specific finding in one of the six detailed documents: `05_SIH26121_TRACEABILITY.md`, `06_ML_AND_MODEL_AUDIT.md`, `07_DATA_PIPELINE_AUDIT.md`, `08_REAL_VS_SIMULATED.md`, `09_ARCHITECTURE_AND_DEAD_CODE.md`, `10_DEMO_READINESS.md`. This document does not introduce new findings — it synthesizes them.

---

## What is genuinely implemented?
- Module 01's full 6-layer document pipeline (real PyMuPDF + real Docling OCR + regex entity extraction + real physics validation), proven with a live end-to-end test during this audit.
- Module 02's real semantic knowledge search (genuine sentence-transformer embeddings), real DORS offset-ranking engine, real stratigraphic correlation, real risk-corridor and ahead-of-bit logic.
- 3 of 7 drilling hazards (STUCK_PIPE, KICK, WELLBORE_INSTABILITY) genuinely backed by trained ML models, live-verified end to end.
- Both 2D (Leaflet) and 3D (globe) nearby-wells visualizations, consuming the identical real backend data, with verified-correct geography and bidirectional state synchronization.
- The physics digital twin — real coupled ODE equations, live-confirmed to advance over real wall-clock time.
- The 14-page React dashboard, fully reachable, 0 console errors across every route in the latest end-to-end pass.

## What is partially implemented?
- PS requirement (v)'s "predictive analytics models" — true for 3 of 7 named hazards; the other 4 run on disclosed heuristics or (module 05) honestly unfitted ML.
- PS Problem-Description item (iii)'s casing-program cross-well correlation — real casing data exists, but it isn't correlated the way hazard corridors are.
- The "user-defined radius" requirement at the raw backend-API level — the parameter exists but functions as a scoring decay, not a hard filter; the frontend compensates correctly, so the user-facing feature itself works.

## What is simulated?
- All "real-time" telemetry/alerts are driven by a physics simulation, not real OIL India eRTMAC data — no such feed exists or was obtainable, and this is honestly disclosed throughout the code.
- 4 of 7 module-02 hazard types (MUD_LOSS, TORQUE_SPIKE, CEMENTING_FAILURE, OVERPRESSURE_ZONE) and both of module 05's ML pillars (Isolation Forest, XGBoost) run on heuristics/unfitted fallbacks, each honestly surfaced via a live status field.
- RiskPredictionPage's feature-importance and performance figures — explicitly labeled illustrative, not measured.

## What is hardcoded?
- Header.tsx's and SimulatorPage.tsx's idle-telemetry fallback constants — real risk, since nothing visually distinguishes them from live data.
- Module 01's `/benchmark` endpoint's competitor comparison table — hardcoded but currently unused by the frontend.
- Module 04's `/health` endpoint's top-level `"status"` field — a static string, not derived from an actual liveness check.

## What exists but is not wired?
- **The single most important finding of this audit**: `real_data/real_trained_models/{stuck_pipe,wellbore_instability}_model_REAL.joblib` — real models, genuinely trained on real Volve data with honest cross-validated accuracy, and completely invisible to the live system for two independent, compounding reasons (wrong directory + a dict-key mismatch that would still break loading even if the directory were fixed).
- Module 04's `PhysicsController`/`LiveTelemetryStreamer` — a complete second control path, alive only in tests.
- Several frontend-defined API functions (`getReviewQueue`, `getReviewDetail`, `getTemplates`, `setOperatorInputs`, etc.) with real, working backend routes and no UI caller.
- The entire PostgreSQL/PostGIS/pgvector/TimescaleDB layer — built, seeded once historically, confirmed not connected to any live module, and not even running as a container at the time of this audit.

## What is still missing?
- "Fishing operations," explicitly named in the PS's historical-event-types list, has no representation anywhere in the data model.
- A real eRTMAC data feed (not fixable within this project's scope — no such feed was ever available).

## What technically works end-to-end?
Document ingestion (real PDF → real structured JSON, proven live this audit), knowledge search (real query → real ranked results), nearby-wells discovery and visualization in both 2D and 3D (real data, real sync, verified geography), geological correlation, and the 3-of-7 ML-backed hazard predictions — all confirmed via direct, live runtime testing, not source inspection alone.

## What data is real vs synthetic?
A majority-synthetic, honestly-labeled mixed store: 12 of 14 wells, 39 of 44 events, and all telemetry are synthetic (procedurally generated, seeded, reproducible); 2 wells, 5 events, 10 casing records, and most formation/trajectory data for those 2 wells are real, extracted from genuine Equinor Volve field documents via the actual document-intelligence pipeline — not fabricated to look real. The boundary is precisely mapped in `08_REAL_VS_SIMULATED.md`, confirmed by exact live record-count matches at every step.

## Which ML models are actually trained and used?
Three `LogisticRegression` models (STUCK_PIPE, KICK, WELLBORE_INSTABILITY), trained on the synthetic testbed, live-serving real predictions today. That is the complete list of models actually load-bearing in production.

## Which .joblib/pickle/model artifacts are unused?
Two real-data-trained models (`real_data/real_trained_models/*_REAL.joblib`) — trained, committed, never loaded, for the two-fold reason documented above. Zero `.joblib` artifacts exist anywhere for module 05's Isolation Forest or XGBoost classifiers — they have never been fitted and persisted in any production run.

## Which pipelines are real?
Document extraction (module 01), semantic search (module 02), DORS/stratigraphic correlation (module 02), the physics simulation (module 04) — all genuinely real, live-verified computation, not stubs. Module 04's synthetic-data-generation pipeline is also real code but produces data that nothing currently trains on.

## What are the largest remaining technical gaps?
1. The orphaned real-data-trained hazard models (highest-value, smallest-effort fix available).
2. Module 02 and module 05's unreconciled, independently-scored hazard engines for the same real-world phenomena.
3. Module 05's two ML pillars have never been fitted in any production run.
4. The backend radius-filtering API contract doesn't match its name (frontend compensates, but the contract itself is misleading).
5. "Fishing operations" has no place in the data model.
6. The hardcoded-vs-live telemetry fallback ambiguity in two frontend components.

---

## Final status matrix

| Area | Status | Runtime Evidence | Main Limitation |
|---|---|---|---|
| SIH nearby-well requirement | PARTIAL (API) / IMPLEMENTED (feature) | Live `offset_rank`/`map/wells` calls | Backend radius param is a scoring weight, not a filter |
| Geospatial map (2D) | IMPLEMENTED | Live-rendered, 0 console errors | None significant |
| 3D globe | IMPLEMENTED | Live-rendered, geography verified correct after a real bug fix | No fly-to, no terrain/underground scenes |
| Well intelligence | IMPLEMENTED | Live DORS/correlation calls | None significant |
| Historical events | IMPLEMENTED | Live search, 44 events (39 synthetic + 5 real) confirmed exactly | Mostly synthetic by volume, honestly labeled |
| Document intelligence | PARTIAL | Live end-to-end ingestion test performed | Entity extraction is regex, not NLP/AI |
| OCR | IMPLEMENTED | Real Docling, confirmed live | None |
| NLP/entity extraction | **NOT NLP** — regex/rules | Confirmed from imports + live health check | Should not be marketed as NLP/AI |
| Knowledge search | IMPLEMENTED | Live semantic search confirmed | Brute-force scan, not a production vector index (fine at current scale) |
| Correlation | IMPLEMENTED | Live corridor/stratigraphic calls | None significant |
| Risk detection | PARTIAL | 3/7 hazards ML-backed, live-verified | 4/7 heuristic-only by disclosed data-insufficiency |
| Predictive analytics (module 05) | PARTIAL/SIMULATED | Live `UNFITTED_FALLBACK` status | 2 of 3 ML pillars never fitted in production |
| Alerts | IMPLEMENTED (mechanism) / SIMULATED (data source) | Live simulation advancement confirmed | Driven by physics sim, not real rig data |
| Recommendations | IMPLEMENTED | Real deterministic mitigation text, live-rendered | Not ML/LLM-generated — correctly not claimed to be |
| Physics/digital twin | IMPLEMENTED | Live before/after advancement test | Simulated, not real eRTMAC — honestly disclosed |
| Real-time/replay | IMPLEMENTED (replay) | `live/replay_engine.py`, honestly labeled | Not real-time rig data |
| ML models | PARTIAL | 3 live-serving models confirmed; 2 real-trained models orphaned; 2 module-05 models never fitted | See `06_ML_AND_MODEL_AUDIT.md` |
| Real datasets | CONFIRMED PRESENT | 2 real wells, 5 real events, real Volve PDFs/WITSML | Small in volume relative to synthetic |
| Synthetic datasets | CONFIRMED PRESENT | 12 wells, 39 events, all telemetry | Majority of the live data by volume |
| PostgreSQL/PostGIS | BUILT + SEEDED, NOT CONNECTED | Confirmed via exhaustive grep; container not even running | Separate, real follow-up work, not started |
| API integration | MOSTLY SOLID | Full contract audit performed | 8 dead frontend functions, 1 duplicated helper, 1 misleading radius param |
| Browser verification | PASS WITH KNOWN ISSUES | Full route + journey walkthrough in `04_E2E_VERIFICATION.md` | Two minor, documented cosmetic/UX items, no functional breaks |

---

## Exact list of gaps to address next (priority order)

1. **Wire the real-data-trained hazard models** — fix `hazard_predictor.py`'s `MODELS_DIR` and the `"pipeline"`/`"model"` dict-key mismatch so `real_data/real_trained_models/*.joblib` actually serve predictions. Smallest-effort, highest-authenticity win available.
2. **Decide and document the module 02 ↔ module 05 relationship** — either reconcile their hazard scores for the user, or clearly label them as two independent engines in the UI, rather than leaving the divergence invisible.
3. **Fit and persist module 05's Isolation Forest and XGBoost models** on real or synthetic training data, or explicitly scope this as future work in any judge-facing material.
4. **Fix the radius-filtering API contract** on `GET /api/v2/map/wells` and `/api/v2/offset_rank` so the backend itself implements a real radius filter, not just a scoring weight.
5. **Add a `FISHING` (or equivalent) hazard/event type** to the data model if "fishing operations" tracking is meant to be a real, demonstrable capability.
6. **Distinguish idle-telemetry fallback values from live data visually** in `Header.tsx` and `SimulatorPage.tsx`.
7. **Clean up dead/dormant code**: remove or wire `recharts`, consolidate the duplicated `haversineKm`, remove or finish `PhysicsController`/`LiveTelemetryStreamer`, decide the fate of the 8 unused frontend API functions.
8. **Correct module 04's `/health` to derive its `status` field from a real liveness check.**

None of these gaps were fixed in this audit pass, per the explicit instruction that this phase establishes ground truth only.
