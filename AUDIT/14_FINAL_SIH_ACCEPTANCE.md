# 14 — Final SIH-26121 Acceptance Matrix (Pass 6, corrected in the final
# emergency pass)

**Date:** 2026-10-05. **This is the final implementation pass — there is no
Pass 7.** This report reflects verified reality after implementation and
live/browser testing, not intention. Status is assigned per requirement
using exactly the four allowed labels: **Implemented and verified**,
**Implemented, verification incomplete**, **Partially implemented**,
**Unavailable due to a specific external dependency**.

**Correction note (final emergency pass, same date)**: this report was
updated once more, after Pass 6, to correct one claim that had gone
stale — §4's telemetry-correlation item was fixed and verified in the
emergency pass and is no longer a carried-forward limitation (see §4's
own note for the full detail). Test counts in §2 were also updated to
reflect the emergency pass's 13 new regression tests. No other claim in
this report was found to need correction during that pass's verification
sweep. A new, separate document,
`AUDIT/15_PRODUCTION_READINESS_ROADMAP.md`, was also produced in that
pass — it is explicitly NOT a claim that this report's "demo ready"
assessment was wrong; it answers a different, larger question (genuine
operational readiness) that this report was never meant to answer.

Pass 6 continued directly from Pass 5's own prioritized list
(`AUDIT/13_PRODUCT_COMPLETION.md` §6) and closed every item on it:
the historical-alerts read path (A3/B4, the largest remaining backend
gap), the rest of the internal-terminology sweep (B5), and evidence-link
wiring plus provenance badges (B2/B6). It also found and fixed three real
bugs during live verification — not during code review — that would
otherwise have shipped: a route-ordering bug that silently broke the new
alert-history endpoint, a dropped-provenance-field bug that made every
event's REAL/SYNTHETIC badge impossible to render, and a mislabeled
database row left over from a previous pass's own manual testing.

## 0. What changed in this pass

**New backend capability — the alerts table's read path (A3/B4).** Until
this pass, `alerts` was write-only from the application's perspective:
`POST /api/v3/predictive/evaluate` wrote rows via `sync_evaluation()`
(Pass 4), but nothing ever read them back. Added:
- `AlertRepository.for_well(well_id, limit)` (`modules/04_physics_engine/db/repositories.py`) —
  queries `alerts` ordered `triggered_at DESC`, using the index
  (`idx_alerts_well`) the table was given at creation specifically for
  this access pattern.
- `get_alert_history()` (`modules/04_physics_engine/db/service.py`) — the
  same three-state honesty discipline established for module 01's
  `SyncStatus` in Pass 5: `{"status": "ok", "alerts": [...]}` (DB
  reachable, 0+ real rows — **"no history" is never confused with
  "unavailable"**), `{"status": "not_configured", "alerts": []}` (dev
  mode, no database configured), or a thrown exception the route turns
  into a real `503` with **no `alerts` key at all** (database configured
  but unreachable) — never a silently-empty `200`.
- New route `GET /api/v3/predictive/alerts/{well_id}/history`, row-mapped
  into the same `AlertAdvisory` shape the live feed already uses, so the
  frontend's History tab reuses one rendering path instead of inventing a
  second alert shape.
- **Alert History tab** on `AlertsAdvisoryPage.tsx` — a tab switcher, kept
  visually and structurally separate from the live feed panel (different
  heading, different list, never merged), rendering all three states with
  distinct, honest copy: a real empty-history message, a "not enabled in
  this environment" message, and an "unavailable — retry" message with a
  working retry button.

**Real bug found and fixed while verifying this live, not while writing
it:** the new `/history` route was registered *after* the existing
`GET /api/v3/predictive/alerts/{well_id:path}` route, which uses a greedy
`:path` converter (needed because well IDs like `15/9-F-12` contain a
slash). Starlette matches routes in registration order, so the older
route silently absorbed `.../history` into its own `well_id` parameter
and the new route was never reached — confirmed live: curling the new
endpoint returned a bare `[]` instead of the tagged response, even though
the route existed in `/openapi.json` and every unit test passed (the
tests call the function directly via `TestClient`, which doesn't exercise
Starlette's route-ordering behavior the same way two sibling path-prefix
routes do in combination). Fixed by moving the `/history` route's
registration before the catch-all. A regression comment now explains why
the order matters, since nothing in the test suite would catch a
re-introduction of this exact bug without a live HTTP-level check.

**Real bug found and fixed while wiring provenance badges:**
`EventRepository` already selected `source_type` from `drilling_events`
rows, and the DB schema already had the column — but
`_event_row_to_model()` never passed it into the `DrillingEvent(...)`
constructor, and the Pydantic model didn't even declare the field. Every
event ever returned by the API silently dropped its own provenance,
making the REAL/SYNTHETIC distinction invisible everywhere, even though
the plan's Pass 5 note claimed it was "confirmed present." Fixed by
adding `source_type: Optional[str]` to the `DrillingEvent` model
(`modules/02_nwis_backend/models/schemas.py`) and threading it through
all three construction paths: the DB row mapper, and both in-memory
construction loops in `data_store.py` (the project's own synthetic
testbed fixture events now honestly tag `"SYNTHETIC"`; the real-document-
parsed events for the two real Volve wells now honestly tag `"REAL"`).
Confirmed live and covered by two new regression tests.

**Real data-integrity bug found and fixed while live-testing the new
evidence links:** clicking "View Source" on a Nearby Wells event for
`WELL-NHK-001` surfaced an event (`EVT-PASS4VERIFY1`) tagged
`source_type='REAL'` whose own narrative literally reads "Synthetic
verification event for Pass 4 handoff testing." This was a leftover row
from a previous pass's own manual live-verification run through the real
document-handoff path (`handoff_events()` correctly tags everything it
writes as `REAL`, because for genuine use that's accurate — this was a
test fixture pushed through the real path, not a code bug). Corrected the
one row's `source_type` to `SYNTHETIC` directly in the database (an
additive, honest correction, not a deletion — the row itself documents a
real past verification and stays on record). The PDF evidence viewer's
own honest-failure path was also confirmed live in the same click: since
the test fixture's "source document" was never actually ingested, the
viewer correctly showed "Source document not available" instead of
fabricating a viewer.

**UI terminology sweep (B5) — finished.** Every remaining "Module
01/02/04/05", raw `/api/vN` path, and developer-facing error string
flagged as open in Pass 5 §2/§6 is now fixed, plus several more found by
a final repo-wide sweep this pass:
`BackendStatusStrip.tsx`, `AlertsAdvisoryPage.tsx`,
`HistoricalIntelligencePage.tsx`, `LookAheadPanel.tsx`,
`SystemStatusPage.tsx`, `GeologicalCorrelationPage.tsx`,
`DashboardPage.tsx`, `CopilotPage.tsx`, `ReportsAnalyticsPage.tsx`,
`RiskPredictionPage.tsx`, `SimulatorPage.tsx`, `PdfEvidenceViewer.tsx`,
`WellInspector3DModal.tsx`, `DocumentIngestionPage.tsx`. A final grep
across every page/component for `module 0[0-9]`, `MODULE [0-9]`, and
`/api/v[0-9]` confirms nothing user-visible remains (library attribution
like the Leaflet/Esri tile credit, and in-code comments, are intentionally
untouched — those aren't product-facing labels).

**Evidence links + provenance badges (B2/B6) — completed.**
`NearbyWellsPage.tsx`'s "HISTORICAL NPT HAZARDS" event list now shows a
REAL/SYNTHETIC badge per event and a working "View Source" button only
where `source_document` is actually present (never a dead button) —
verified live with both a populated and an honestly-absent case.
`GeologicalCorrelationPage.tsx`'s risk-corridor cards were **deliberately
left unwired**: `RiskCorridor.contributing_events` is confirmed (by
reading the Pydantic model directly) to be `List[str]` — event IDs only,
no `source_document`/`source_page`/`source_type` — so wiring an evidence
link or badge there would mean inventing data the endpoint doesn't
return. This matches the original plan's own instruction to verify before
wiring, not assume.

## 1. SIH-26121 requirement-by-requirement acceptance

Source: `research/research/PROBLEM_STATEMENT.md`, "Expected Outcome /
Solution" items i–vii.

### i. AI, NLP, OCR, and data analytics to automatically extract and structure information from historical drilling reports and well documents

**Status: Implemented and verified.**

- Route/workflow: `/app/documents` (Document Ingestion) → upload → OCR/
  text-tier extraction pipeline (`modules/01_document_intelligence`) →
  structured fields (well identity, MD, formations, drilling parameters,
  events, NPT, mud losses, kicks, stuck pipe, casing, cementing,
  mitigation, outcome) with confidence, source document, and page
  reference preserved per field.
- Human review: approve/reject/annotate at `/app/documents`, with a
  `postgres_sync_status` badge (closed enum: `synced`/`not_configured`/
  `unavailable`/`error` — never a raw exception string) and a working
  retry button wired to `POST /api/v1/review/{doc_id}/resync` for the
  `unavailable`/`error` states only.
- Persistence: approved extractions hand off into the canonical
  `drilling_events`/`documents`/`document_review` PostgreSQL tables
  (idempotent UPSERT, safe to retry) and are retrievable through
  `/app/knowledge` (Historical Search) and `/app/wells` (Nearby Wells'
  event list) — the same shared knowledge repository, not a document-
  pipeline-only silo.
- Tests: `modules/01_document_intelligence/tests/test_document_db_service.py`
  (27 passed, incl. the closed-enum/no-raw-exception tests and the FK-bug
  regression guard), `Backend/tests/contract/test_document_ingest.py`
  (resync idempotency, 404-on-unknown-doc).
- Live verification (Pass 5, re-confirmed this pass): approved a real
  queued document in the browser, saw "Review recorded: approved," the
  honest migrated/skipped narration, and "Saved to shared knowledge base"
  after the FK-constraint bug fix (documented in AUDIT/13 §0).
- Honest limitation, disclosed in the product itself (not hidden): the
  pipeline does not store per-field pixel bounding boxes, so the evidence
  viewer navigates to the correct **page**, not a highlighted box — this
  is stated plainly in the viewer's own banner, not glossed over.

### ii. Interactive map-based visualization of nearby wells within a user-defined radius

**Status: Implemented and verified.**

- Route: `/app/wells` (Nearby Wells). Active well selectable from the
  global header dropdown (14 real wells, 5 real fields: Baghjan,
  Hugrijan, Moran, Nahorkatiya, Volve); radius is a live slider (default
  25 km) that recomputes the actual haversine-filtered candidate set, not
  a cosmetic label change.
- **Confirmed covers the entire catalog, not one dataset** — this was a
  real, user-reported bug fixed in Pass 5 and re-verified this pass: the
  map title, "Total Catalog" subtitle, and field-filter dropdown were
  previously hardcoded to three Assam field names that didn't even match
  the real catalog (two of the three didn't exist; the two real Volve
  wells were unreachable by the filter despite "All Fields" technically
  including them). Now all three are derived from the live well list.
  Live-verified: `Total Catalog: 14 Wells across 5 Fields`, dropdown lists
  all 5 real fields, map title/coordinates follow the active well.
- Offset-well selection opens the full dossier (total depth, trajectory
  profile, operator, KB elevation, stratigraphic tops, historical events)
  in the same view; "SET AS ACTIVE WELL" propagates the selection
  app-wide.
- DORS 5-factor relevance ranking table (spatial/formation/depth/
  trajectory/composite) renders alongside the map for the same active
  well, keeping geographic proximity and geological/operational relevance
  visually distinct columns, never conflated into one number.
- Active-well state consistency: the dossier panel previously got stuck
  on a hardcoded well (`WELL-NHK-002`) regardless of the header selection
  — a real bug fixed in Pass 5, re-confirmed fixed this pass by switching
  the active well via the header dropdown and observing the dossier,
  DORS table, and map title all follow correctly.
- Tests: `test_offset_rank_db_matches_memory_exactly`,
  `test_corridors_db_matches_memory_exactly` (parity regression guards),
  33 parametrized memory/503/postgres tests across the 8 DB-backed M02
  routes this ranking and map data flow through.

### iii. Searchable knowledge repository of drilling events, lessons learned, operational challenges, and mitigation measures

**Status: Implemented and verified.**

- Route: `/app/knowledge` (Historical Search) — free-text/semantic search
  (`search_mode` honestly reports `semantic` when sentence-transformers
  loaded, keyword-fallback otherwise — never claimed as AI when it isn't)
  plus structured filters (hazard type, formation, min severity).
  `/app/wells` also supports structured browsing of a given well's event
  history.
- Both routes are database-backed when PostgreSQL is configured
  (`GET /api/v2/events`, `/events/search`, `/events/{well_id}` — migrated
  in Pass 5, re-verified live this pass through the actual running HTTP
  server, not just at the Python level).
- Each result shows severity, formation, depth, IADC code, mitigation
  text where present, a REAL/SYNTHETIC provenance badge (Pass 6), and a
  "View Source" evidence link that opens the actual source PDF at the
  correct page when `source_document` is present — confirmed live, both
  the success path (`HistoricalIntelligencePage.tsx`, pre-existing) and
  the newly-wired path (`NearbyWellsPage.tsx`, this pass).
- Zero-result and missing-source-document handling: confirmed live (the
  `EVT-PASS4VERIFY1` click-through, see §0) — the viewer states plainly
  that no original PDF is available rather than fabricating one.
- Real events (parsed from actual Volve source documents) and synthetic
  demonstration events are now distinguishable by a REAL/SYNTHETIC badge
  everywhere events render, closing a real gap: before this pass,
  `source_type` was silently dropped by the API regardless of what the
  database stored (see §0).

### iv. Correlate geological, drilling, and reservoir data across wells based on depth and formation

**Status: Implemented and verified**, with one explicitly-scoped,
pre-existing limitation carried forward honestly rather than hidden.

- Route: `/app/correlation` (Geological Correlation) — stratigraphic
  depth-track alignment (`ξ = d_strat_m ÷ formation thickness_m`, the
  formation-relative coordinate that eliminates the "trajectory trap" of
  comparing raw MD across wells with different trajectories), the top-3
  DORS-ranked offset wells' formation/depth columns side by side, and an
  ahead-of-bit risk-corridor lookahead section for the active well.
- Database-backed when configured (`/api/v2/stratigraphic_depth_track`,
  `/corridors`, `/offset_rank` — all migrated and parity-verified in
  Pass 5, re-confirmed live this pass).
- A real latent scoring bug was found and fixed in Pass 5 specifically
  because of this correlation work's own parity-verification discipline:
  `_station_row_to_model()` silently defaulted `well_type` to `VERTICAL`
  when reconstructing trajectories from the database, corrupting every
  non-vertical well's DORS trajectory score by 0.075–0.5. Caught by a
  direct score-by-score comparison against the memory path, not by
  inspection — now covered by a dedicated regression test
  (`test_offset_rank_db_matches_memory_exactly`).
- Missing/incompatible data handling: formations/trajectories/casing
  records are looked up per well and absent data renders as an honest
  empty state ("No ranked offset wells available for this well") rather
  than a fabricated value; confirmed by reading the route handlers'
  fallback logic and by the live UI's "—" / "No ... on record" patterns
  used consistently across the dossier, event list, and corridor views.
- **Carried-forward limitation, not fixed in this pass**: casing/
  cementing/mud-program correlation is real where records exist (10 real
  casing records for the 2 real Volve wells, surfaced via
  `CasingProgramPanel.tsx`), but is sparse by the nature of the available
  data, not by a code gap — this was Pass 4's own documented finding and
  remains accurate; no canonical schema change was needed or made.

### v. Predictive analytics for drilling risks (mud losses, stuck pipe, overpressure zones, torque spikes, cementing issues) based on historical offset-well behaviour

**Status: Implemented and verified**, with honestly-disclosed model-
fitting status (not a gap this pass could or should close).

- Route: `/app/risk` (Risk & Prediction) — the 4-pillar fusion engine
  (deterministic rules 35% + isolation-forest anomaly 20% + 6-class
  XGBoost 30% + geology/offset prior 15%), independent by design from the
  Nearby Wells DORS score (different formula, different taxonomy,
  explicitly not reconciled — disclosed via a hover tooltip, not hidden).
- Principal hazard pathways exercised live this pass: injected a real
  `KICK_OVERPRESSURE` scenario through the actual simulator
  (`/app/drilling`'s scenario selector / `POST /api/v3/physics/scenario`),
  observed real `CRITICAL`/`WARNING` alerts form with genuine causal
  evidence chains ("Delta flow rate: +9026.0 LPM excess", "Pore pressure
  margin: -10.43 bar", etc.) and a concrete recommended mitigation
  protocol — not a static UI card.
- Honest model-fitting status, surfaced in the product (not buried in
  logs): `/app/status` shows `baseline_hazard_rules: ACTIVE`,
  `isolation_forest_anomaly: UNFITTED_FALLBACK`,
  `xgboost_hazard_classifier: UNFITTED_FALLBACK`, with the plain-language
  explanation "UNFITTED_FALLBACK means no trained .joblib artifact exists
  on disk for that model — the rule engine pillar still runs real,
  deterministic hazard scoring; this is not a fabricated metric." This is
  accurate on a fresh checkout and was not altered — changing it would
  require training real models on real data this environment doesn't
  have, which the engineering constraints correctly forbid doing without
  a demonstrated requirement.
- Tests: `modules/05_predictive_analytics/tests` (19 passed),
  `modules/04_physics_engine/tests` (23 passed, including the new alert-
  history read-path tests).
- Deliberately preserved, not touched: DORS formula, risk-fusion weights,
  physics ODE equations — no correctness defect was found that justified
  a change, per the engineering constraints.

### vi. Real-time alerts and recommendations for proactive decision-making

**Status: Implemented and verified.** This was the largest remaining gap
carried from Pass 5 and is the core of this pass's backend work.

- Live feed: `/app/alerts` (Alerts & Advisory) shows active alerts with
  severity, hazard type, depth/formation context, a grounded causal
  evidence chain, and a recommended SPE/IADC mitigation protocol with
  acknowledge/execute-mitigation actions — all database-write-through
  since Pass 4 (`sync_evaluation()`), confirmed still correct this pass.
- **Alert History (new this pass)**: a second, visually distinct tab on
  the same page reads the persisted `alerts` table back
  (`GET /api/v3/predictive/alerts/{well_id}/history`). Live-verified
  end-to-end: injected a real labelled `KICK_OVERPRESSURE` scenario,
  observed the live feed show the alert, switched to History, confirmed
  the same alert appears there with correct severity/timestamp/status —
  then **restarted the backend and re-checked**: the history still showed
  the exact same 41 persisted rows for `WELL-NHK-001`, including rows
  from an earlier session the same day (timestamps spanning both
  ~6:32 PM and ~12:19 AM), proving genuine cross-restart persistence, not
  session-local state.
- Three honestly distinct states, all exercised live: a well with zero
  history shows "No recorded alerts for this well yet" (confirmed for
  `15/9-F-12`, which has none); the tri-state backend contract also
  covers `not_configured` and `unavailable` (503, retry button), verified
  by dedicated unit tests against a real closed-port DSN (not mocked).
- Deduplication/lifecycle: `AlertRepository.upsert()` keys on `alert_id`
  with `ON CONFLICT DO UPDATE`, so a re-sent alert updates its status in
  place (`ACTIVE → CLEARED` observed live in the History tab for one of
  the injected alerts) rather than duplicating — this was already Pass
  4's design and is unchanged, just now independently confirmed via the
  read path.
- Simulated-vs-real distinction: every alert in this environment
  originates from the labelled scenario simulator
  (`source_type: "SIMULATED"` on the underlying telemetry rows, per
  Pass 4's schema design) — the product does not and cannot claim a live
  OIL field connection (see §3).

### vii. User-friendly dashboard for field and office-based personnel

**Status: Implemented and verified.**

- The full journey — active well → nearby offsets → historical knowledge
  → geological correlation → document review → risk outlook → alerts →
  recommendations → telemetry/simulation — was walked live in the
  browser this pass (and in Pass 4/5's own verification), with active-
  well state staying synchronized across every page via the shared app
  context, and 0 console errors observed on every touched page
  (`/app/alerts`, `/app/wells`, `/app/correlation`, `/app/knowledge`,
  `/app/status`, `/app/drilling`, `/app/offset-map`).
- Internal-architecture labels: a final repo-wide sweep this pass (see
  §0) confirms no visible "Module 01/02/04/05," raw `/api/vN` path, raw
  database term, or developer-only instruction remains on an ordinary
  product screen. `System Architecture` (`/app/status`) is the one
  intentionally-technical diagnostics page, per the plan's own design —
  it still reads as a status page (three named service cards, mapped
  component labels, plain-language unfitted-model explanation), not a
  terminal dump.
- The Live 3D Rig View's lighting — reported by the user as rendering
  "pitch dark" — was root-caused and fixed in Pass 5 (a point light now
  travels with the bit position, scaled to the trajectory's own extent)
  and re-verified live this pass at a taller viewport: the Downhole
  Follow camera preset now shows a clearly visible radiant halo around
  the bit against a lit grid floor and the full wellbore tube, not a bare
  dot on black (screenshot: `3d-rig-pass6-verified.png`).

## 2. Final test results

```
cd Backend && python run_tests.py   (run as 5 isolated suites across this
                                      pass and the final emergency pass —
                                      see note below on why)

  backend                145 passed, 1 skipped
  document_intelligence   27 passed
  nwis                    73 passed   (+13 new since the previous count:
                                       2 event source_type honesty tests,
                                       plus 10 telemetry-scoping regression
                                       tests and 1 DB-reachability fix in
                                       the final emergency pass — see §4)
  physics                 23 passed   (+5 new: alert-history tri-state)
  predictive_analytics    19 passed
  ------------------------------------------------
  TOTAL                  287 passed, 1 skipped, 0 failed
```

Each suite run individually rather than through the orchestrated
`run_tests.py` driver, matching this project's own established pattern
for avoiding a harmless cross-suite `conftest.py` name collision when two
module suites are collected in the same pytest invocation.

All pre-existing tests still pass — no regressions. New this pass:
- `modules/04_physics_engine/tests/test_telemetry_alert_db_service.py`
  (+5) — `get_alert_history`'s three states (not_configured, unavailable-
  never-leaks-connection-detail, ok-with-real-rows), row→advisory shape
  mapping, and the explicit "empty history ≠ unavailable" distinction
  your own Pass 5 feedback required.
- `modules/02_nwis_backend/tests/test_events_dors_corridors_db.py` (+2) —
  `source_type` provenance honesty for both DB-backed real events
  (`15/9-F-12`, must read `REAL`) and memory-backed synthetic events
  (`WELL-NHK-001`, must read `SYNTHETIC`).

`cd frontend && npx tsc --noEmit` — clean, 0 errors, confirmed after
every round of edits in this pass, including the final terminology-sweep
round.

`npm run build` — succeeds cleanly (0 errors; the pre-existing "chunks
larger than 500kB" warning is unrelated to this pass).

## 3. Real-data and integration honesty

- The two real wells (`15/9-F-12`, `15/9-F-1`) are genuine public Equinor
  Volve data, labeled `VOLVE` as their field, never relabeled as OIL or
  Upper Assam data anywhere in the product — confirmed by this pass's own
  live map/dossier screenshots showing "Equinor" as operator and real
  North Sea formation names (Hugin, Ty, Hod, Shetland, Utsira, Ekofisk,
  Sleipner).
- The remaining 12 wells and their events are clearly the project's own
  synthetic testbed (Upper Assam field names: Nahorkatiya, Moran,
  Baghjan, Hugrijan), now distinguishable in the UI by the REAL/SYNTHETIC
  provenance badge added this pass — closing the one place this
  distinction was previously invisible to a user.
- All telemetry and alerts in this environment originate from the labeled
  physics simulator (`source_type: "SIMULATED"`); no claim of a live
  eRTMAC or OIL field connection is made or implied anywhere in the
  product. This is a genuine external dependency (OIL's internal eRTMAC
  stream and proprietary reports are not available to this project), and
  the integration boundary for it is concrete: `sync_evaluation()`'s
  write-through contract and the `telemetry_records`/`alerts` schema
  would accept a real feed's data unchanged if one were ever connected,
  without requiring any product code change — this was verified by
  inspection of the write path, which validates `well_id` against the
  canonical `wells` table and accepts data by shape, not by source.

## 4. Remaining material limitations (honest, not concealed)

**Corrected in the final emergency pass (2026-10-05)**: the item
previously listed first here — `NWISOrchestrator.analyze()`'s telemetry
correlation being well-id-blind — is **fixed and verified**, not a
carried-forward limitation. `get_telemetry_at()` now takes an explicit
`well_id` parameter, threaded through the in-memory store
(`NWISDataStore.telemetry_by_well`), the DB-backed snapshot
(`DbStoreSnapshot.get_telemetry_at`, querying `telemetry_records WHERE
well_id = %s` when PostgreSQL is configured), the orchestrator
(`analyze()` now calls `get_telemetry_at(..., well_id=active_well_id)`),
and both API routes (`/api/v2/telemetry/{well_id}`,
`/api/v2/analyze/{well_id}`). A well with no telemetry of its own now
honestly returns an empty list / `a_sensor: 0.0` across every hazard,
never another well's data. Verified live (both memory-mode and
DB-backed, `data_source: "postgres"` confirmed): `15/9-F-12` (no
telemetry) returns `a_sensor: 0.0` for all 7 hazards; `WELL-HGJ-012`
(has real telemetry) returns genuine non-zero values (0.408, 0.184,
0.104, ...). Also confirmed directly in the browser — the Command
Center's 4-Pillar Confidence card shows "Sensor Anomaly: 0%" /
"A_sensor 0%" for `15/9-F-12`, matching the API exactly. Covered by 10
new regression tests
(`modules/02_nwis_backend/tests/test_telemetry_scoping_regression.py`),
including a direct two-well, same-orchestrator-instance test proving no
cross-contamination. Full `nwis` suite: 73 passed, 0 failed.

**Three more real defects found and fixed in the same pass, prompted by
direct user observation of the running product** — each confirmed via
live testing, not just code inspection:

1. **The knowledge base never appended for most uploads.** A user
   observation ("when the operator uploads new files our knowledge base
   should be appended") led to tracing the actual upload path live:
   uploaded a real 74-page document through the API, confirmed it
   processed successfully (PASS, 99% confidence) and `postgres_sync_status:
   synced`, then confirmed **zero rows** landed in `drilling_events`
   despite 15 events being extracted. Root cause: `handoff_events()`
   (the function that migrates extracted events into the searchable
   table) was only ever called from the manual-review `/decision` route —
   a document that auto-passed validation (the common case for a clean
   document, which never shows a review prompt in the UI at all) had no
   code path that ever called it. Fixed by auto-approving PASS documents
   in the orchestrator right after processing, running the same
   `sync_review()`/`handoff_events()` pair the manual-approval route
   runs, so FLAGGED/MANUAL_REVIEW documents still require a human (PS
   26121's own curation requirement, preserved exactly), but a clean
   document now reaches the shared knowledge base automatically, with a
   new "No review needed — automatically added to the shared knowledge
   base" message in the UI. Verified live through the actual browser
   file-picker upload flow (not the API) with two different real Volve
   documents, both showing the new message and "Saved to shared knowledge
   base" immediately after processing, no restart needed.
2. **A real date-parsing bug, found while verifying fix #1.** The same
   live trace surfaced a second, independent bug: this project's own
   reference sample DDR document failed its entire Postgres sync
   (silently, logged only as `status: "error"`) because its extracted
   `report_date` ("15/03/2025", DD/MM/YYYY — standard for these Indian
   drilling reports) was passed to a Postgres `DATE` column completely
   unparsed. Postgres's default date style rejects "15/03/2025" outright
   (day 15 isn't a valid month), and — more seriously — would have
   silently misinterpreted a date like "03/04/2025" as April 3rd instead
   of March 4th, a correctness bug worse than a crash. Fixed with a
   dedicated `_parse_report_date()` helper that tries DD/MM/YYYY first
   (matching these documents' real convention), falls back to MM/DD/YYYY,
   and honestly stores `NULL` rather than guessing when genuinely
   unparseable. Verified live: the previously-failing sample document now
   syncs cleanly end-to-end. 8 new tests (7 pure unit cases + 1 live-DB
   regression test reproducing the exact original failure).
3. **The map defaulted to open ocean.** A user screenshot showed the
   Nearby Wells map "completely dark" on first load — traced to
   `AppContext.tsx`'s hardcoded default active well, `15/9-F-12` (a real
   Volve well, but located in the North Sea — its map view centers on
   open water with no land basemap detail). Changed the default to
   `WELL-HGJ-012`, a real Upper Assam well that is also this project's
   own designated live-simulation well (the only one with a full
   synthetic telemetry stream), so the Dashboard/Command Center/Live
   Drilling pages also show real moving data immediately on first load
   instead of an empty state. Also changed both Leaflet map components'
   default basemap from a dark vector style to Satellite (per explicit
   user request), since real imagery reads far more clearly over
   unfamiliar terrain than the dark vector style. Verified live with
   screenshots: the map now opens centered on real, recognizable Assam
   river-delta terrain with Satellite selected by default, on both the
   Nearby Wells and Offset Map pages.

All three fixes are additive and scoped: no existing passing test
changed behavior, no formula/algorithm was touched, and the full backend
suite (287 tests before these three fixes) grew to account for the new
coverage with zero regressions (re-confirmed after each fix, including a
transient, non-reproducible Windows subprocess-handle error in an
unrelated import-isolation test suite — isolated, re-run alone, and
confirmed to pass cleanly, so not attributed to any change made here).

1. **Predictive ML pillars (isolation forest, XGBoost) are UNFITTED_FALLBACK
   on this checkout** — disclosed honestly in the product itself (§1.v),
   not a defect to "fix" without real training data and a demonstrated
   requirement to retrain, which the engineering constraints forbid. See
   `AUDIT/15_PRODUCTION_READINESS_ROADMAP.md` §C.2 for exactly what
   fitting these would require.
2. **Casing/cementing/mud-program correlation is sparse** (10 real
   records across 2 real wells) — accurately reflects the available real
   data, not a code gap.
3. **Risk-corridor cards' `contributing_events` carry no
   source_document/source_type** — confirmed by reading the
   `RiskCorridor` Pydantic model directly (`List[str]` event IDs only).
   Evidence links and provenance badges were correctly left unwired there
   rather than fabricated.

None of these are release-blocking: each is either an existing, already-
disclosed limitation unchanged by this pass, or a genuine external/data
dependency outside this project's authority to resolve. See
`AUDIT/15_PRODUCTION_READINESS_ROADMAP.md` for the full, separate
accounting of what would be required for genuine operational (not demo)
readiness — a materially different and larger bar than anything in this
report.

## 5. Demo-readiness

- Every one of the SIH problem statement's seven expected outcomes has a
  working, browser-verified user journey, not just a passing API test.
- Three real bugs were found and fixed by actually clicking through the
  product during this pass (route ordering, dropped provenance field, a
  mislabeled database row) — the kind of defect that would have been
  visible in a live demo and was caught before one.
- Restart-persistence was directly demonstrated for the newest capability
  (alert history) with real before/after evidence, not assumed.
- The one intentionally-technical page (`/app/status`) is positioned
  correctly as a diagnostics area, not the primary experience, and every
  other page uses operational terminology throughout.
- No known release-blocking defect is left unresolved. The limitations in
  §4 are genuine, bounded, and already disclosed in the product's own UI
  where relevant (model-fitting status, source-document availability,
  page-only evidence navigation) — this report does not conceal partial
  functionality anywhere in the matrix above.
