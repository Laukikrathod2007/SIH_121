# SIH 26121 — Implementation Audit Against the Original Problem Statement

> **Method**: every claim below was verified from actual source code, live
> endpoint calls against a running server, or direct inspection of real
> data files during this audit — not from README/comment claims taken at
> face value. Where a comment turned out to be stale or wrong, that is
> flagged explicitly. Nothing was modified during this audit.
>
> **Branches audited**: `backend-working` (modules 01/02/04/05, database
> schema, real_data/) and `laukik` (frontend). These two branches are not
> currently merged — a live demo requires running services from both.

---

## 1. EXECUTIVE VERDICT

**Total atomic PS requirements extracted: 16**

| Status | Count | Requirements |
|---|---|---|
| ✅ FUNCTIONAL | 5 | R1, R5, R11, R14, R15 |
| 🟡 FUNCTIONAL + SIMULATED | 6 | R2, R3, R4, R6, R7, R13 |
| 🟠 PARTIAL | 4 | R8, R9, R10, R12 |
| 🔵 HARDCODED | 0 | — |
| 🟣 MOCKED/STUBBED | 0 | — |
| 🔴 MISSING | 0 | — |
| ⚪ UNVERIFIED / N/A-for-prototype | 1 | R16 |

**No item is hardcoded, mocked, or missing outright.** That is a genuinely
strong result, but it is not the same as "fully complete" — 6 requirements
depend on synthetic default data rather than real OIL data, and 4 have a
real but incomplete implementation. Read the matrix below before repeating
either "we hardcoded nothing" or "everything works" as a standalone claim —
both are true only with the qualifications attached.

**One correction to an earlier, less careful audit that was run against
this same codebase**: that audit claimed module 01 uses "spaCy PetroNER."
This is false. Verified directly in
`modules/01_document_intelligence/pipeline/tier3_entity_extractor.py`:
entity extraction is a deliberately regex/rules-based engine, explicitly
documented as NOT an ML/NER model. Repeating the spaCy claim to a judge
would be a real, avoidable risk.

---

## 2. LINE-BY-LINE PS COMPLIANCE MATRIX

| ID | PS Requirement | Status | Actual Implementation | Data Source | Hardcoded? | Simulated? | Mocked? | Evidence | Test/Verification | Gap |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | AI/NLP/OCR extraction & structuring from WCR/DDR documents | ✅ FUNCTIONAL | 6-layer pipeline: PyMuPDF native → Docling OCR → regex/rules entity extraction → template learner → physics validator → WITSML JSON | Real Equinor Volve PDFs (14 documents, 979 pages) + real synthetic-DDR test fixtures | No | No (real docs) | No | `modules/01_document_intelligence/pipeline/{orchestrator,tier1_native_extractor,tier3_entity_extractor}.py`; frontend `DocumentIngestionPage.tsx` (real upload→poll→result, no simulated progress bar) | Live: uploaded real PDFs via `/api/v1/ingest`, polled `/api/v1/jobs/{id}`, inspected real `/api/v1/results/{doc_id}` output this session (Steps 13-20) | Extraction quality varies with document layout (inherent to any regex extractor, disclosed in logger) |
| R2 | Interactive geospatial map, user-defined radius | 🟡 FUNC+SIM | Real Leaflet map (`BasinMap.tsx`), real lat/lon projection (CartoDB tiles, no hand-rolled math), real 5-50km slider driving both the map circle and the well list/DORS table | Synthetic Assam-Arakan testbed (12 wells) by default | No | Yes (well set is synthetic) | No | `frontend/src/components/BasinMap.tsx`, `pages/NearbyWellsPage.tsx` | Built frontend, confirmed radius slider changes both circle geometry and filtered well count | Real Volve well coordinates exist (`real_data/`) but aren't the map's live data source |
| R3 | Instant access to historical events from offset wells | 🟡 FUNC+SIM | Real `GET /api/v2/events/{well_id}` endpoint, real UI rendering (dossier panels, correlation columns) | Synthetic 39-event testbed by default; 119 real Volve-extracted events exist in `real_data/` but are not loaded into the live store | No | Yes (default data) | No | `modules/02_nwis_backend/server.py` events routes; `data_store.py` | Verified live endpoint returns real synthetic records; real events verified via standalone script (Step 13-16), not through the live app | Real events not wired into the live data store (same module 01↔02 gap as R9/R10) |
| R4 | Searchable knowledge repository (events, lessons, mitigations) | 🟡 FUNC+SIM | Real sentence-transformer semantic search (`all-MiniLM-L6-v2`), real BM25 keyword fallback, self-reports which mode actually ran | Synthetic testbed by default; separately validated against 119 real events with Hit@5=2/2 (Step 18) via a standalone script, not the live app | No | Yes (live default) | No | `modules/02_nwis_backend/search/knowledge_search.py`; frontend `HistoricalIntelligencePage.tsx`, `CopilotPage.tsx` (both explicitly labeled "not an AI-generated synthesis") | Live `/api/v2/events/search` call returns `search_mode: "semantic"` confirmed genuinely running, not keyword fallback | Real-data validation exists but isn't the default live search corpus |
| R5 | Correlate geological/drilling/reservoir data by depth & formation | ✅ FUNCTIONAL | Real stratigraphic depth-normalization: ξ = (TVD − formation top) / thickness, eliminates MD-vs-TVD "trajectory trap" | Synthetic by default; validated against real WITSML/PDF survey data for 22 real wells (Steps 17, 19) | No | Partially (live default synthetic) | No | `engines/stratigraphic_correlator.py`; frontend `GeologicalCorrelationPage.tsx` computes ξ client-side from two real API numbers, not fabricated | Live-verified: interpolated TVD fell within real station brackets in 98/100 real bracket tests | Same synthetic-default gap as above |
| R6 | Correlate mud losses across wells | 🟡 FUNC+SIM | `HazardType.MUD_LOSS` real end-to-end (extraction → DORS hazard score → risk corridor → heuristic prediction) | Synthetic default; real extraction validated (Step 13-16) | No | Yes (default) | No | `models/schemas.py`, `dors_engine.py::score_hazard`, `hazard_predictor.py` | Live `/api/v2/analyze` shows MUD_LOSS assessment with real computed score | Below the 8-example ML threshold even in the real pull (7 real examples) — heuristic-only either way |
| R7 | Correlate kicks across wells | 🟡 FUNC+SIM | `HazardType.KICK` real end-to-end; real trained ML model exists (synthetic-trained, 0.817 AUC) | Synthetic-trained model; real KICK events extracted (17, Step 15) but only 1 had a usable real depth+trajectory — too few to retrain on real data | No | Yes (model is synthetic-trained) | No | Same files as R6 | Live-verified in `/api/v2/analyze` output | Real-data retraining attempted (Step 22) and explicitly could not reach the sample threshold |
| R8 | Correlate stuck pipe across wells | 🟠 PARTIAL→strong | `HazardType.STUCK_PIPE` real end-to-end, **and now the only hazard type with a real-data-trained AND deployed model** (0.661 mean leave-one-well-out AUC across 3 real folds, beats the synthetic model's 0.622) | **Real Volve data** (10 real events, 3 real wells) as of Step 24 | No | No (deployed model is real-data-trained) | No | `real_data/train_hazard_models_real.py`; `data/models/stuck_pipe_model.joblib` (real, synthetic backed up separately) | Verified live: composite score changed after deployment, confirming real inference, not just a file on disk | This is the strongest real-data proof point in the whole system — worth leading with in a demo |
| R9 | Correlate casing programs across wells | 🟠 PARTIAL | Real extraction (module 01, `CasingRecord`, 3 real bugs found & fixed extracting it — Step 20), real module 02 endpoint (`GET /api/v2/casing/{well_id}`, Step 23) | **Real** — 10 real casing records, 2 real Volve wells only | No | No (genuinely real, just thin) | No | `tier3_entity_extractor.py::extract_casing_records`; `server.py`'s `/api/v2/casing*` routes | Live-verified: `GET /api/v2/casing/15%2F9-F-12` returns 6 real records; synthetic wells correctly 404 | Only 2 wells have real data; no live UI page renders this endpoint yet (backend-only) |
| R10 | Correlate cementing practices across wells | 🟠 PARTIAL | `CasingRecord.top_of_cement_md_m` real field, real extraction attempted; `HazardType.CEMENTING_FAILURE` now fully live in `/api/v2/analyze` (Step 24 closed a real gap — this hazard type was missing from the live assessment loop entirely before this audit's session) | Real, thin (same 2 wells as R9) | No | No | No | Same as R9, plus `orchestrator.py::ALL_HAZARDS` | Live-verified CEMENTING_FAILURE composite score appears in `/api/v2/analyze` | "Cementing practices" as correlatable data (cement volume, type) has no dedicated schema beyond top-of-cement depth |
| R11 | Correlate formation-specific risks | ✅ FUNCTIONAL | `HIGH_RISK_FORMATIONS` heuristic lookup, real formation-group logic, feeds both DORS `S_formation` and hazard heuristic scoring | Synthetic formation names by default; real North Sea formation profile exists and is used during real-data validation runs | No | Partially | No | `hazard_predictor.py`, `domain_rules.py::FORMATION_PROFILES` | Verified via real Volve document runs with `NWIS_FORMATION_PROFILE=NORTH_SEA_VOLVE` | — |
| R12 | Predictive analytics models: mud loss / stuck pipe / overpressure / torque spike / cementing | 🟠 PARTIAL | Real hybrid design: trained ML where ≥8 real-caliber examples exist, physics heuristic elsewhere, and the API always discloses which path produced a score (`m_ml_source`) | Mixed — see below | No | Partial | No | `hazard_predictor.py` module docstring explains the design rationale in detail | Live-verified all 7 hazard types (not 6 — OVERPRESSURE_ZONE added this session) return real per-hazard scores | **Precise breakdown, not a single answer**: STUCK_PIPE = real-data ML (deployed). KICK, WELLBORE_INSTABILITY = synthetic-data ML. MUD_LOSS, TORQUE_SPIKE, CEMENTING_FAILURE, OVERPRESSURE_ZONE = heuristic only, no trained model at all. The PS's literal wording ("predictive analytics **models**") is only fully met for 1 of 7 hazard types on real data, 3 of 7 on synthetic data, and not met (by ML) for the remaining 3 |
| R13 | Real-time/proactive alerts | 🟡 FUNC+SIM | Real risk corridor clustering, real lookahead/early-warning logic (proximity-based state machine, independent of the composite score), real alert generation and mitigation lifecycle in the UI | Alerts are computed from real logic over **simulated telemetry** (a real reduced-order physics ODE solver, module 04 — not live rig sensor data, and not fabricated numbers either) | No | Yes (telemetry is simulated) | No | `risk_corridor_engine.py::identify_risk_corridors/_build_corridor`; `AlertsAdvisoryPage.tsx` (real lifecycle: detected→acknowledged→mitigated→cleared, wired to real `mitigateAlert`/`refreshAlerts` calls) | Verified a real early-warning case fires correctly (Step 3.4/§4.3 of the original benchmark doc — a real bug fix, not a demo scripted result) | "Real-time" here means the physics simulation runs continuously and alerts respond to it live — it is not live OIL rig data, and the UI does not claim it is |
| R14 | Recommendations for proactive decision-making | ✅ FUNCTIONAL | Real, domain-expert-authored mitigation text per hazard type, looked up deterministically — not AI-generated, and never presented as AI-generated anywhere in the UI | Static text authored once per hazard type (7 types as of this session) | Yes — **and this is correct, not a flaw**: mitigation actions are real engineering knowledge (SPE/IADC-style interventions), appropriately a lookup table, not something that should be ML-generated | No | No | `risk_corridor_engine.py`'s `actions`/`recommended_actions` dicts (2 locations, both now including OVERPRESSURE_ZONE — Step 24) | Live-verified real text returned per hazard in `/api/v2/analyze` | None — this is a case where "hardcoded" is the technically correct and honest design, not a gap |
| R15 | Dashboard for field + office personnel | ✅ FUNCTIONAL | 12-page React/TypeScript app, dark SCADA theme, all pages traced this audit call real backend endpoints (module 01 and/or 02) with no live fake-data page found | Depends on page — see R1-R13 for each page's specific data provenance | No | Partially (inherits from backend) | No | All files under `frontend/src/pages/` | Read all 12 pages directly this audit; `npm run build` succeeds with zero TypeScript errors | Frontend (`laukik` branch) and the newest backend work (`backend-working` branch) are not merged — see §9 |
| R16 | Standalone platform alongside eRTMAC | ⚪ N/A for prototype | Architecturally true — this is an independently-deployable set of services, not embedded inside anything else | N/A | N/A | N/A | N/A | `README.md`'s explicit module-to-outcome mapping | No real eRTMAC system exists to integrate against in a hackathon context — this is a production-deployment requirement, not a prototype gap (see §6 distinction) | Cannot be tested until real eRTMAC access exists |

---

## 3. END-TO-END FEATURE AUDIT

**R1 — Document extraction** (the cleanest full trace in the system):
```
INPUT: real PDF (DDR/WCR/mud log) uploaded via DocumentIngestionPage.tsx
  → POST /api/v1/ingest (multipart, real FastAPI endpoint)
  → orchestrator.py: PyMuPDF native text OR Docling OCR per page
  → tier3_entity_extractor.py: regex/rules extraction (mud props, events,
    formations, NPT, casing, reservoir properties)
  → domain_rules.py: physics validation, OCR digit-slip auto-repair
  → DocumentExtractionResult (WITSML-mapped JSON) saved to data/output/
OUTPUT: GET /api/v1/results/{doc_id} → real JSON
UI: DocumentIngestionPage.tsx polls job status, renders real formation/NPT
    tables from the real response, offers human review (approve/reject)
```
Every link in this chain was independently verified this session against
real Volve documents, including finding and fixing 3 real bugs in the
casing extraction step alone (Step 20).

**R8 — Stuck pipe prediction** (the strongest real-ML trace):
```
INPUT: real Volve DDR/completion/end-of-well reports (14 documents)
  → tier3_entity_extractor.py: real STUCK_PIPE event extraction, depth-tagged
  → real_data/train_hazard_models_real.py: builds real feature rows via
    module 02's own build_features() (depth, pore pressure, inclination,
    well type, formation group) — real WITSML trajectory for 3/4 wells,
    documented 0.0-inclination fallback for the 4th (no trajectory exists)
  → LogisticRegression + StandardScaler, real leave-one-well-out CV
LOGIC: real leave-one-well-out AUC = 0.661 (3 folds: 0.683, 0.633, 0.667)
OUTPUT: deployed to data/models/stuck_pipe_model.joblib (format-verified
    against the real consuming code, not assumed compatible)
UI: /api/v2/analyze's STUCK_PIPE assessment now reflects this real model
    — verified live, composite score changed after deployment
```

**R13 — Real-time alerts**:
```
INPUT: simulated telemetry (module 04's real ODE physics solver — not
    live rig sensors, not fabricated numbers)
  → risk_corridor_engine.py: clusters historical hazard events into depth
    corridors, computes proximity risk independently of composite score
  → 4-pillar confidence, real hybrid ML/heuristic hazard scoring
OUTPUT: AlertAdvisory objects with real causal evidence chains
UI: AlertsAdvisoryPage.tsx — real 4-stage lifecycle (detected → ack →
    mitigate → clear), calls real mitigateAlert()/refreshAlerts()
```

---

## 4. HARDCODED / MOCKED / SIMULATED INVENTORY

**Genuinely hardcoded (and correctly so — domain knowledge, not fake data):**
- `risk_corridor_engine.py`'s two `actions`/`recommended_actions` dicts —
  real SPE/IADC-style mitigation text per hazard type. This SHOULD be a
  lookup table; classifying it as a flaw would be wrong.
- `RiskPredictionPage.tsx` lines 36-46 (`featureImportances` array) and
  several inline "(illustrative)" figures (ROC-AUC 0.949, PR-AUC 0.946,
  inference latency 24.53ms) — **self-labeled in the UI itself** as
  illustrative/not measured, with a module-docstring explaining exactly
  why (ported reference numbers, no live endpoint to measure against).
  This is the single largest block of non-real numbers in the frontend,
  and it is the most honestly disclosed.

**Simulated (real pipeline, synthetic/simulated input) — not hardcoded:**
- The entire live data store default (`modules/02_nwis_backend/data/synthetic/`)
  — 12 wells, 97 formation tops, 39 events, 3600 telemetry records,
  generated by `generate_testbed.py`. Every engine that reads this data is
  real; the data itself is synthetic, modeled on Assam-Arakan basin
  parameters, not actual OIL records.
- `AppContext.tsx`'s `DEFAULT_TELEMETRY` object (lines 52-79) — an initial
  placeholder shown before the first real WebSocket/poll packet arrives,
  explicitly tagged `provenance: 'SYNTHETIC'`. Overwritten by real data
  within ~1 second of connection.
- `SimulatorPage.tsx`'s "Internal Physics State Inspector" section uses
  small hardcoded fallback constants (e.g. `telemetry?.ecd_gcc || 1.29`)
  only for the brief window before telemetry loads — not presented as
  live once real data exists.

**A stale-comment issue, not a fabrication, found this audit:**
- `AppContext.tsx` (lines 37-49) and `SystemStatusPage.tsx` (lines 178-183)
  both state module 03's physics/WebSocket backend "has no FastAPI/
  WebSocket routes exposed yet" and "nothing is currently listening."
  This was independently verified **false as of this session**: module
  04/05 (module 03's actual successor, built this session on the
  `backend-working` branch) exposes exactly the routes the frontend
  expects (`GET /api/v3/health`, `WS /api/v3/physics/stream`,
  `POST /api/v3/predictive/evaluate`), confirmed live via direct curl
  earlier this session. The frontend code was written before module 04/05
  existed as a real, routed server and was never updated — this is a
  **branch-synchronization gap**, not deceptive code. It does mean that on
  the `laukik` branch alone, with only modules 01/02 running, the comment
  is accurate; the fix is merging branches, not rewriting logic.

**No `Math.random()`, no fake array literals presented as real records, no
canned "AI-generated" response text, and no backend route found that
returns a hardcoded constant instead of a computed value.**

---

## 5. REAL IMPLEMENTATION INVENTORY

These qualify as genuinely real because they were traced end-to-end and
verified against actual runtime behavior or real data, not just present in
the codebase:

1. **DORS 5-factor offset-well ranking** (`dors_engine.py`) — real Haversine
   spatial scoring, real Hausdorff-profile trajectory similarity (validated
   against 22 real wells, correctly distinguished a near-horizontal and a
   near-vertical real well as most dissimilar).
2. **Stratigraphic depth correlator** — real ξ-coordinate math, validated
   against real survey brackets (98/100 correct interpolations).
3. **6-layer document extraction pipeline** — real, validated against 14
   real Volve documents with a documented history of real bugs found and
   fixed (kick/kickoff false positives, basin-hardcoded formations,
   well-name heuristics, casing fraction parsing, cutoff-context false
   positives).
4. **Hybrid ML/heuristic hazard prediction** — real trained
   LogisticRegression models where data supports it, honest heuristic
   fallback elsewhere, always discloses which path produced a score.
5. **Real-data-trained, real-data-validated, real-data-deployed STUCK_PIPE
   model** — the one point in the system where every link (extraction →
   features → training → cross-validation → deployment → live inference)
   is real data end to end.
6. **Semantic knowledge search** — genuinely uses sentence-transformer
   embeddings when available (self-reports `search_mode`), validated
   against real extracted events with real ground-truthed queries.
7. **Risk corridor / alert lifecycle** — real clustering, real proximity
   state machine, real UI lifecycle wired to real mutation endpoints.
8. **Frontend-backend wiring generally** — every one of the 12 pages read
   during this audit calls a real, cited backend endpoint; several
   (`RiskPredictionPage`, `HistoricalIntelligencePage`, `CopilotPage`,
   `SystemStatusPage`) contain explicit in-code disclosure comments
   distinguishing real from illustrative data, which is itself evidence of
   a deliberate, maintained honesty discipline across this codebase.

---

## 6. MISSING / PARTIAL REQUIREMENTS

**R9/R10 — Casing/cementing correlation (PARTIAL)**
- Current state: real extraction, real endpoint, only 2 real wells.
- Gap: no frontend page renders `/api/v2/casing` yet; not wired into any
  scoring engine (deliberately — see logger Step 21/23 for why forcing it
  into DORS would fabricate a relationship the PS doesn't ask for).
- Minimum work: a UI panel calling the existing real endpoint (small);
  broader real coverage requires pulling more Volve documents.
- Necessary for SIH prototype: the backend piece is done; a UI panel would
  materially strengthen a demo of this specific PS line item.
- Future/OIL work: real per-well casing programs from OIL's own records.

**R12 — Predictive models for all 6 named hazards (PARTIAL)**
- Current state: 1/7 hazard types (STUCK_PIPE) has a real-data-trained,
  deployed model. 2/7 (KICK, WELLBORE_INSTABILITY) have synthetic-trained
  models. 4/7 (MUD_LOSS, TORQUE_SPIKE, CEMENTING_FAILURE,
  OVERPRESSURE_ZONE) are heuristic-only.
- Gap: real-data retraining for the remaining hazard types is blocked on
  real data breadth, not a code limitation — traced precisely to why (too
  few real depth-tagged events per hazard type, concentrated in too few
  wells) in logger Steps 18-22.
- Minimum work: pull more of the ~1,759 real Volve DDRs beyond the 14
  processed so far (the same real fix identified for R3/R4's data breadth
  too — this is the single highest-leverage next real-data action across
  multiple requirements at once).
- Necessary for SIH prototype: the hybrid design (real model where
  justified, honest heuristic elsewhere, always disclosed) is itself a
  defensible prototype answer — judges should be told this design choice
  explicitly rather than asked to assume more ML coverage exists.
- Future/OIL work: full 6/6 real-data model coverage needs real OIL
  historical event volume.

**R2/R3/R4/R5/R6/R7/R13 — synthetic default data (FUNCTIONAL+SIMULATED, not
strictly "missing," but the most likely judge question)**
- Current state: real engines, real UI, synthetic data unless a specific
  real-data validation script is run separately.
- Gap: no live toggle or endpoint currently serves the real Volve dataset
  as the *default* data a judge would see just by opening the app.
- Minimum work: point `data_store.py` at a real-data JSON export instead
  of (or alongside) the synthetic testbed for the demo session — small,
  bounded, does not require the full Postgres migration.
- Necessary for SIH prototype: **yes, high priority** — this single change
  would upgrade 6 of 16 requirements' live-demo answer from "functional on
  synthetic data" to "functional on real data," with no new code.
- Future/OIL work: full real OIL data at production scale.

**Branch merge (not a PS requirement, but blocks demoing several
requirements together)**
- Current state: frontend lives on `laukik`; the newest backend work
  (Steps 20-24: overpressure/fishing/casing/cementing/reservoir schema,
  real STUCK_PIPE deployment) lives on `backend-working`, uncommitted
  changes stashed.
- Minimum work: merge or rebase before a live demo — otherwise the demo
  environment must run mismatched code between what the frontend expects
  and what the backend actually serves.

---

## 7. CLAIMS WE MUST NOT MAKE

1. ❌ "Our extraction pipeline uses spaCy / an NER model."
   ✅ "Extraction uses a deliberately deterministic, petroleum-domain
   regex/rules engine — chosen over ML/NER for auditability, since every
   extracted field traces to an exact pattern match, not a black-box
   inference."

2. ❌ "All 6 (or 7) hazard types are predicted by trained ML models."
   ✅ "A hybrid design: trained models where real historical data supports
   it (currently STUCK_PIPE on real data, KICK/WELLBORE_INSTABILITY on
   synthetic data), an explicit, disclosed physics heuristic elsewhere —
   the API always reports which path produced a given score."

3. ❌ "This is validated against real Oil India Limited data."
   ✅ "Validated against real, public Equinor Volve field data (14
   documents, 22 wells, real WITSML surveys) — a real, non-synthetic
   dataset, but not OIL's own operational data, which is confidential and
   was never available to this prototype."

4. ❌ "The dashboard shows real-time drilling telemetry."
   ✅ "The dashboard streams live output from a real physics-based
   simulation (a coupled ODE digital twin), not live rig sensor data — the
   simulation itself is genuine and reduced-order-model-based, not a
   scripted animation."

5. ❌ "The Copilot / knowledge search uses AI-generated answers (RAG/LLM)."
   ✅ "A grounded retrieval system: real semantic search over real event
   records, with summary text template-filled from the actual returned
   fields — no LLM is configured anywhere in this project, and the UI
   says so explicitly."

6. ❌ "Casing and cementing programs are correlated across all wells."
   ✅ "Casing/cementing correlation is real but currently covers 2 wells
   with real extracted data — the pipeline and endpoint are real and
   ready to scale with more real documents, not yet broad."

---

## 8. DEMO-READINESS

A live flow that can be shown honestly, end to end, right now:

1. **Input**: a real, unmodified Equinor Volve PDF (e.g.
   `WELL-15_9-F-1A_COMPLETION.pdf` from `real_data/volve/`).
2. **Action**: drag-and-drop it into Document Ingestion.
3. **Processing**: watch the real job progress bar poll `/api/v1/jobs/{id}`
   (visibly real — page/OCR counts update as it runs, not a fixed-duration
   fake bar).
4. **Result**: real extracted formation tops, real casing records (size,
   shoe depth), real events, shown in the actual returned JSON (exportable).
5. **Evidence**: click "View Source PDF" — the extracted fields are shown
   against the actual source document, page-anchored.

A second, independently strong flow:

1. **Input**: select the active well and open Live Drilling.
2. **Action**: click "Start Simulation."
3. **Processing**: real ODE physics engine begins streaming telemetry over
   a real WebSocket at a real, visible Hz rate (shown in the header).
4. **Result**: risk scores in `/api/v2/analyze` update live, including the
   real-data-trained STUCK_PIPE model's score changing as depth/formation
   change — point this out explicitly, it is the strongest real-ML proof
   point in the system.
5. **Evidence**: System Status page shows real health-check JSON from both
   live backends, refreshed on demand.

**Do not** demo the Feature Importance table on Risk Prediction as if it
were measured — it is labeled "illustrative" for a real reason and a judge
who reads the badge will ask about it.

---

## 9. SIH JUDGE RISK AREAS

| Judge question | Real answer, with evidence |
|---|---|
| "Is this real-time data or a simulation?" | Simulation — a real coupled ODE physics solver (module 04), not live rig sensors. Show `AppContext.tsx`'s `provenance: 'SYNTHETIC'` tag and the module docstrings that say so directly. |
| "Are all 6 hazards predicted by ML?" | No — show the `m_ml_source` field in a live `/api/v2/analyze` response; 3 report `trained_model`, 4 report `heuristic_fallback`, and explain why (§6/R12 above). |
| "Is this validated on OIL's own data?" | No — real Equinor Volve public data, not OIL's confidential records. Show `real_data/` and the logger's Step 13-24 benchmark trail. |
| "Does changing the well/depth/radius actually change results?" | Yes for every page audited — verified this session by tracing each page's fetch call and its dependency array; no page was found returning a static result regardless of input. |
| "Is the Copilot an LLM?" | No — no LLM is configured in this project at all; show the grounded-retrieval disclosure banner directly on that page. |
| "What's real about the casing/cementing capability specifically?" | 10 real casing records, 2 real wells, a real live endpoint (`/api/v2/casing`) — be precise about the "2 wells" scope rather than implying broader coverage. |
| "Why does the frontend say module 03 isn't connected when I can curl it?" | A real branch-synchronization gap, not a lie — the frontend comment predates module 04/05's real build-out on a different branch. Merge before a demo where this could come up. |

---

## 10. FINAL GAP PLAN (priority order for closing PS gaps before evaluation)

1. **Merge `backend-working` into the frontend's branch (or vice versa)** —
   blocks demoing Steps 20-24's real work (overpressure/casing/cementing
   endpoints, the deployed real STUCK_PIPE model) together with the UI at
   all. Zero new logic, pure integration risk if skipped.
2. **Point the live data store at real data for the demo session** —
   highest-leverage single change; upgrades 6 of 16 requirements from
   "functional+simulated" to "functional on real data" with no new code,
   just a data-source swap for `data_store.py`.
3. **Add a UI panel for `/api/v2/casing`** — the backend half of R9/R10 is
   done and currently invisible in the UI; this is a small, contained
   frontend addition.
4. **Pull more real Volve documents** — the single real fix underlying
   both R3/R4's data-breadth gap and R12's ML-coverage gap; not a code
   change, a data-sourcing action via the existing Databricks pipeline.
5. **Reconcile the stale module-03 comments** once branches are merged and
   module 04/05 is confirmed reachable from the frontend's actual runtime
   environment — small, but removes a real, findable inconsistency.

Everything else in this audit (R16's eRTMAC integration, full 6/6 real-ML
coverage, broad real casing/cementing coverage) is legitimately
production/OIL-deployment scope per §6's completeness distinction, not a
prototype-blocking gap.
