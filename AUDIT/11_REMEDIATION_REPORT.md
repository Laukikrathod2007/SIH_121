# Remediation Report — SIH-26121 Priority Fix Pass

**Date:** 2026-10-04
**Scope:** `AUDIT/FINAL_AUDIT_SUMMARY.md`'s prioritized gap list, items 1-8, worked
in order per the remediation spec. This document is the running index;
Priority 1 (real-model wiring) and Priority 3 (risk architecture) have their
own dedicated documents (`11_MODEL_RUNTIME_STATUS.md`,
`11_RISK_ARCHITECTURE_DECISION.md`) per the spec's required file list — this
file covers Priorities 2, 4-8, plus a running checklist of the acceptance
criteria.

---

## Priority 2 — Backend radius contract (FIXED)

**Finding:** `GET /api/v2/map/wells` accepted no radius parameter at all and
always returned every well; `GET /api/v2/offset_rank/{id}`'s `radius_km` was
a DORS spatial-scoring decay divisor, not a hard exclusion filter — every
well was still ranked and returned regardless of its value. Both frontend
pages correctly compensated with their own client-side Haversine filter, but
the raw API contract was misleading to any direct caller (e.g. a judge
curling the API, or a future integration).

**Severity:** Medium. User-facing behavior was already correct (frontend
compensation worked); this was a contract-truthfulness and
future-integration-risk issue, not a live bug.

**Root cause:** `/map/wells` was never designed to filter — it was written
as "return everything for the map to filter." `/offset_rank`'s `radius_km`
was designed from the start as a scoring parameter (feeds
`score_spatial()`'s `max(0, 1 - dist/radius_km)`), and was never intended as
an exclusion boundary — but nothing in the API surface stated this.

**Investigation before changing anything:**
- Traced every frontend consumer of both endpoints (`Dashboard`, `Command
  Center`, `Geological Correlation`, `Nearby Wells`, `Offset Map`, `3D
  Globe`, `Copilot`) via `useCommandCenterData.ts`, `api.ts`, and each page.
- Confirmed `CommandCenterPage`/`GeologicalCorrelationPage`/`DashboardPage`
  all depend on `offset_rank` returning the FULL ranked list (not a
  pre-filtered one) — they display `offset_rankings[0..n]` as "top offset
  wells by DORS score," not "wells within radius." Changing `radius_km` to a
  hard filter would have silently truncated these lists and changed what
  "top offset well" means for every existing page.
- Confirmed `NearbyWellsPage.tsx` and `GlobeMapPage.tsx` already apply their
  own Haversine filter on top of the full ranked/full well list — this
  pattern was preserved exactly, not touched.

**Files changed:**
- `modules/02_nwis_backend/server.py` (`get_map_wells`, `rank_offsets`)
- `frontend/src/services/api.ts` (`getMapWells`, `getOffsetRank` — comments
  + new optional params only)

**Implementation (smallest-change design, per the spec's own suggested
shape — DORS ranking stays ranking, filtering becomes an explicit separate
layer):**
1. `/map/wells` gained two **optional** query params, `center_well_id` and
   `radius_km`. Called with neither (every existing call site), behavior is
   byte-identical to before — confirmed live (14/14 wells, unfiltered).
   Called with both, it now applies a real `haversine_km()` hard filter
   (reusing `dors_engine.py`'s existing function, not a reimplementation)
   and excludes wells outside the radius. Each returned well also now
   carries a `distance_km` field (null when no center well was given).
2. `/offset_rank/{id}` keeps its existing `radius_km` parameter and
   ranking/scoring behavior **completely unchanged** — confirmed live
   (`radius_km=5` still returns all 10 ranked wells, exactly as before). Its
   docstring and response body now explicitly disclose
   `"radius_km_is_scoring_decay_not_a_filter": true`. A new, optional,
   additive `max_distance_km` parameter was added for callers that want a
   genuine hard exclusion — when omitted (every existing call site), nothing
   changes; when passed, rankings beyond that distance are removed from the
   response and `"hard_filter_applied": true` is reported.

**Why this approach:** Satisfies the spec's explicit instruction — "DO NOT
simply change the existing DORS ranking formula," "prefer the smallest
API-level improvement," "DORS ranking = ranking/scoring logic, radius
filtering = explicit filtering layer." No existing consumer's behavior
changes by default; a real filter now exists for any caller (frontend or
otherwise) that wants one.

**Regression risk:** Very low. Both changes are purely additive
(new-optional-parameter-gated); the default code path for every existing
caller is unmodified.

**Verification (live, this pass):**
```
GET /map/wells                                        → 14 wells (unchanged)
GET /map/wells?center_well_id=WELL-HGJ-012&radius_km=5 → 2 wells (HGJ-010 @ 1.56km, HGJ-012 @ 0km) — real filter confirmed
GET /offset_rank/WELL-HGJ-012?depth=2600&radius_km=5             → 10 ranked (unchanged scoring-decay behavior)
GET /offset_rank/WELL-HGJ-012?depth=2600&max_distance_km=5       → 1 ranked (HGJ-010 @ 1.56km) — new hard filter confirmed
```
Browser regression pass: `/app/correlation`, `/app/wells`, `/app/globe` all
loaded with 0 console errors after the backend change.

**Status: FIXED**

---

## Priority 4 — Misleading hardcoded live-looking values (FIXED)

**Finding:** `08_REAL_VS_SIMULATED.md` flagged `Header.tsx` and
`SimulatorPage.tsx` as having idle-telemetry fallback constants rendered in
the exact same visual styling as live data, with no way for a user to tell
the two apart.

**Severity:** Medium-high. This is exactly the kind of ambiguity that could
mislead a judge watching the dashboard into believing a static number is a
live reading.

**Investigation:**
- `Header.tsx` lines 79/85/92/95 (pre-fix): `telemetry?.measured_depth_m?.toFixed(1)
  ?? '2450.0'`, `?? '2315.6'`, `?? 'Barail Sand'`, `?? '0.250'` — all four
  rendered in identical bold cyan/slate/amber styling whether `telemetry`
  was real or `null`.
- `SimulatorPage.tsx`'s "INTERNAL COUPLED ODE STATE VARIABLES" panel
  (lines 256-277, pre-fix) had the same pattern embedded inside live
  derived-physics formulas (`(telemetry?.ecd_gcc || 1.29) * 9.81 * ...`),
  which is worse — even the *computed output* looked like a real physics
  result when telemetry was absent. One line
  (`telemetry?.measured_depth_m.toFixed(2)`) additionally had a **real latent
  crash bug**: optional chaining stops at `telemetry?.`, so if `telemetry`
  were `null` the following `.toFixed(2)` on `undefined` would throw —
  found by static inspection while fixing the ambiguity, not a cosmetic
  issue alone.

**Files changed:**
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/pages/SimulatorPage.tsx`

**Implementation:** No new UI system invented — reused the app's existing
idle/dimmed-text convention. Each of the 4 Header fields now renders either
the real bold-colored value, or a dimmed, italicized `--` placeholder with a
`title="No live telemetry connected"` tooltip, never both in the same
style. SimulatorPage's entire physics-state panel is now conditionally
rendered: real telemetry present → the exact same live panel as before (no
fallback constants anywhere in the formulas); no telemetry → a single
explicit dashed-border "IDLE — no live telemetry. Start the simulator to see
real solver state." panel, which also eliminates the `.toFixed`-on-undefined
crash path entirely (the real-value JSX branch only renders when
`telemetry` is truthy).

**Why this approach:** Satisfies the spec exactly — "the goal is not
necessarily to remove fallback behavior... make the state unambiguous,"
using the existing design language, no new large UI system.

**Regression risk:** Low. When telemetry is present (the common/demo state),
rendered output and values are identical to before. The only behavior change
is what renders when telemetry is absent — previously a misleading number,
now an explicit idle state.

**Verification:** Live-tested at `/app/simulator` with the simulator
running — all values render correctly from real telemetry (e.g. "317.4 bar"
hydrostatic head, "2502.13 m" bit MD, matching the Header's live readout),
0 console errors. The idle branch is structurally guaranteed by the
conditional render (no code path reaches `.toFixed` on a null telemetry
object anymore) rather than relying on a specific browser action to
reproduce the null case.

**Status: FIXED**

---

## Priority 5 — Fishing Operations event type (FIXED — narrower gap than originally audited)

**Finding (as originally stated in `08_REAL_VS_SIMULATED.md`/`10_DEMO_READINESS.md`):**
"Fishing operations... has no representation anywhere in the data model."

**Correction made during this fix (important — the original audit claim was
partially wrong, not just incomplete):** Module 01's `EventType` enum
**already had** a `FISHING_OPERATION` member, with a real (if
real-data-unverified) keyword-extraction list in
`tier3_entity_extractor.py` (`"fishing operation", "fishing job", "junk in
hole", "overshot", "fishing spear", ...`), added in an earlier session and
honestly commented as untested against real data (the 14-document Volve
pull has zero fishing narratives). The actual gap was narrower: **module
02's `HazardType` enum — the type `DrillingEvent.event_type` is hard-typed
to — had no equivalent member at all**, so a module-01-extracted fishing
event had nowhere to be stored in the live event store, and
`EVENT_TYPE_TO_HAZARD_TYPE`'s reconciliation dict had no entry for it
either (silently resolving to `None` via dict `.get()`, rather than an
explicit, reasoned mapping like every other entry in that dict).

**Investigation before implementing:**
- Confirmed `DrillingEvent.event_type: HazardType` — module 02's event
  schema has no separate "event category" enum; it reuses `HazardType`
  directly.
- Confirmed `HazardType` is iterated in three places:
  `ml/hazard_predictor.py`'s model-loading loop, `ml/train_hazard_models.py`'s
  training loop, and `risk_corridor_engine.py`'s zero-initialized score
  dict — all three would safely no-op on a hazard type with zero historical
  examples (the existing `MIN_POSITIVE_SAMPLES` gate), not crash.
- Confirmed `orchestrator.py`'s `ALL_HAZARDS` — the list that actually
  drives `analyze_well`'s 7 hazard cards — is a **separately, explicitly
  maintained list**, not `list(HazardType)`, specifically so a new enum
  member doesn't automatically appear as a hazard-prediction target. This
  was the key fact that made the fix safe: fishing is a remedial operation
  performed after an incident (e.g. following a stuck pipe), not a
  geological hazard a future offset well "has a risk of encountering," so
  it must NOT appear in `ALL_HAZARDS` — and it doesn't, by design.
- Confirmed `/events/search`'s facets are computed dynamically
  (`Counter(e.event_type.value for e in events)`), not a hardcoded list —
  so zero fishing events in the live data correctly means it never appears
  in facets, with no backend change needed for that honesty to hold.

**Files changed:**
- `modules/02_nwis_backend/models/schemas.py` (added `HazardType.FISHING_OPERATION`)
- `modules/01_document_intelligence/models/schemas.py` (added the explicit
  `EventType.FISHING_OPERATION: "FISHING_OPERATION"` mapping entry, replacing
  the previous silent omission)
- `frontend/src/pages/HistoricalIntelligencePage.tsx` (added "Fishing
  Operation" — and, incidentally, the pre-existing but previously
  not-exposed "Overpressure Zone" — to the hazard filter dropdown)

**Implementation:** Taxonomy-only change, exactly as the spec required
("add taxonomy support first... if the current dataset contains no actual
fishing events, the UI should honestly show zero results rather than
invent examples"). No training data, no synthetic events, no fabricated
examples were added anywhere.

**Why this approach:** Smallest-possible change across the
data-model → schema → search → UI chain. Explicitly does NOT add
`FISHING_OPERATION` to `ALL_HAZARDS` (would misrepresent a remedial
operation as a predictable geological hazard) and does NOT fabricate
historical fishing events to "demonstrate" the feature.

**Regression risk:** Very low. New enum member, additively mapped;
every existing iteration site either explicitly excludes it (`ALL_HAZARDS`)
or safely no-ops on zero historical examples (model training/loading).

**Verification (live, this pass):**
```
GET /api/v2/events?hazard_type=FISHING_OPERATION
  → HTTP 200, {"total":0,...,"events":[]}  (valid filter value, honest empty result, no 422/500)
GET /api/v2/analyze/WELL-HGJ-012?depth=2600
  → still exactly 7 hazard_assessments, unchanged (['MUD_LOSS','STUCK_PIPE','KICK',
    'WELLBORE_INSTABILITY','TORQUE_SPIKE','CEMENTING_FAILURE','OVERPRESSURE_ZONE']) — confirms
    FISHING_OPERATION correctly excluded from hazard-prediction cards
GET /api/v2/events/search?query=stuck pipe
  → facets/search still work unaffected, 0 regressions
```
Browser verification at `/app/knowledge`: "Fishing Operation" appears in the
Hazard dropdown; selecting it + searching returns "0 Candidate Events
Indexed" / "0 Events Returned" / "No events matched this query/filter
combination" — an honest empty state, not a fabricated example. 0 console
errors.

**Status: FIXED.** Note for any future phase: if real fishing-operation
narratives are ever added to the real-data pull, `tier3_entity_extractor.py`'s
existing (currently unverified) keyword list and this fix's storage/search
path should be re-validated together against that real text — tracked as a
known follow-up, not done here (would require real data this project does
not have).

---

## Priority 6 — Dead frontend API functions (ONE SURFACED, REST CLASSIFIED/DOCUMENTED)

**Investigation:** Re-confirmed each of the 8 originally-flagged functions
has zero callers anywhere outside `api.ts` itself (`listJobs`,
`getExtractionBenchmark`, `getReviewQueue`, `getReviewDetail`,
`annotateField`, `getTemplates`, `getWell`, `setOperatorInputs`), and
checked each backend route is real and responds live (not a stub).

| Function | Backend route | Real/working? | Decision | Reasoning |
|---|---|---|---|---|
| `getReviewQueue` | `GET /api/v1/review/queue` | Yes — live-tested, 10 real flagged documents from past sessions | **SURFACED** | Spec's own explicit hint ("a particularly notable candidate is the document review queue"); real backend + real pre-existing single-doc review UI pattern (`submitReviewDecision`, already wired) made this a small, additive, genuinely useful addition — not a new workflow invented from scratch |
| `getReviewDetail` | `GET /api/v1/review/{doc_id}` | Yes — live-tested | **SURFACED** (used by the new queue panel's "Review" button) | Needed to make the queue panel's rows clickable; reuses `DocumentExtractionResult`, the exact same type the upload flow already renders |
| `listJobs` | `GET /api/v1/jobs` | Yes — real route, lists in-memory job history | **DOCUMENTED, NOT SURFACED** | The existing per-upload job polling (`getJobStatus`) already covers the one live user journey (upload → poll → result); a full job-history view duplicates `listResults` for little marginal value this pass — legitimate future UI candidate, not added now to avoid scope creep |
| `getExtractionBenchmark` | `GET /api/v1/results/{doc_id}/benchmark` | Yes — real route | **DOCUMENTED, NOT SURFACED** | Per-document benchmark detail; `RiskPredictionPage.tsx`'s own code comments already explain the adjacent competitor-benchmark numbers were found to be fabricated in a prior branch and deliberately not ported — surfacing a different, real per-document benchmark here is legitimate but is a new UI surface, not a wiring fix; left as a documented future candidate |
| `annotateField` | `POST /api/v1/review/{doc_id}/annotate` | Yes — real route | **DOCUMENTED, NOT SURFACED** | Field-level correction notes are a natural extension of the review queue just added, but implementing an annotation UI (text input per field, note history) is a real new interaction pattern, not a small wiring addition — correctly out of scope for "wire an existing button," deferred |
| `getTemplates` | `GET /api/v1/templates` | Yes — real route, lists learned coordinate-fingerprint templates | **DOCUMENTED, NOT SURFACED** | Internal/diagnostic data (Layer 4's template cache) with no obvious end-user action attached to it — a legitimate future admin/debug view, not a user-facing gap |
| `getWell` (singular) | `GET /api/v2/wells/{well_id}` (module 02) | Yes — real route | **LEGACY, iN FAVOR OF EXISTING PATTERN** | Every real call site already uses `getWells()` (plural, list) + `getWellEvents()`; the singular single-well-detail fetch was superseded by that pattern and never adopted — safe to leave as unused rather than force a call site to exist artificially |
| `setOperatorInputs` | module 04/05 route | Yes — real route | **DOCUMENTED, NOT SURFACED** | Would let a user manually override WOB/RPM/flow/mud-weight mid-simulation; `SimulatorPage.tsx`'s existing scenario-injection buttons already cover the demoable "operator intervention" story for this project; a free-form manual-override panel is a real but separate feature, deferred |

**Files changed:**
- `frontend/src/pages/DocumentIngestionPage.tsx` (Review Queue panel — real
  feature addition, not cleanup)

**Why this approach:** The spec explicitly said "do not build a huge new
workflow unless the existing backend genuinely supports it" and "if a
function is legacy and clearly unnecessary, document that first." One
function (`getReviewQueue`/`getReviewDetail` together) met the bar for a
small, genuinely backend-supported, explicitly-hinted-at addition. The rest
are accurately documented with a specific reason each, per the spec's
required classification, rather than either deleted or built into unasked-for
UI.

**Regression risk:** None for the 6 undocumented-but-unwired functions (no
code path touched). The new Review Queue panel is purely additive to
`DocumentIngestionPage.tsx` — it does not alter the existing upload/poll/
result/approve/reject flow, confirmed by browser-testing both flows after
the change.

**Verification (live, this pass):**
```
GET /api/v1/review/queue → 10 real flagged documents (not fabricated — accumulated from past real test-ingestion runs in this project)
```
Browser: `/app/documents` renders the queue panel with all 10 real rows;
clicking "Review" on the first row loads the real `DOC-2642600AD7A8`
extraction result (19 real Hugin/Heather/Draupne/Tor/Ekofisk formation
tops, 3 real NPT events, 99% confidence, 2 physics violations) and shows the
real Approve/Reject controls scoped to that document's real ID. 0 console
errors. The original single-upload flow (drag-and-drop → poll → result →
review) was not touched and remains available below the queue panel.

**Status: PARTIALLY FIXED (1 of 8 surfaced as a real feature), REST DOCUMENTED.**

---

## Priority 7 — Consolidate duplicate Haversine logic

**Finding:** `frontend/src/lib/globeGeometry.ts`'s `haversineKm()` and an
inline duplicate inside `NearbyWellsPage.tsx` are mathematically identical.

**Files changed:**
- `frontend/src/pages/NearbyWellsPage.tsx`

**Implementation:** Removed the inline `haversineKm` function from
`NearbyWellsPage.tsx` and imported the canonical one from
`lib/globeGeometry.ts` instead. No behavior change — confirmed identical
formula (both compute the standard great-circle distance with the same
6371 km Earth radius constant) before removing either copy.

**Regression risk:** None — pure function, byte-identical math, single
import-path change.

**Status: FIXED** (see verification in the final runtime check, below).

---

## Priority 8 — Remaining technical correctness/documentation issues

| Issue | Decision | Action |
|---|---|---|
| Module 04 static `/health` `"status":"healthy"` field | DOCUMENT (not fixed this pass) | Confirmed still present; genuinely deriving it from a real liveness check (e.g. verifying the sim loop thread is alive, not just that the process is up) is a small but real behavior change to a health-check contract other tooling may depend on — left as a tracked gap rather than touched under time pressure in this same pass, to avoid a rushed health-check change. See `11_MODEL_RUNTIME_STATUS.md`/`FINAL_AUDIT_SUMMARY.md` for the original finding. |
| Stale API comments | FIXED (prior phase) | Already corrected in the Phase 3 core-integration pass (module 03 terminology, port numbers) — reconfirmed still accurate during this pass's own `server.py`/`api.ts` edits (Priority 1/2 changes added NEW accurate comments, did not reintroduce stale ones). |
| Dead production physics control path (`PhysicsController`/`LiveTelemetryStreamer`) | DOCUMENT, NOT REMOVED | Re-confirmed still dead-in-production, alive only in tests, per `09_ARCHITECTURE_AND_DEAD_CODE.md`. Not deleted — no evidence requirement in this pass's cleanup rules was met (deletion requires "why dead + reference search + runtime check + test impact" and an explicit decision to remove, not just document; the tests that exercise it are real and would need updating, which is out of scope for a priority-fix pass). |
| Misleading benchmark presentation | DOCUMENT, NOT TOUCHED | `RiskPredictionPage.tsx`'s illustrative feature-importance/AUC figures already carry an explicit in-code disclosure comment (confirmed present, unchanged) stating they are reference values, not measured — this was already honest before this pass; no further action needed. |

**Status: 1 documented-only tracked gap (module 04 health), 3 confirmed
already-adequate (no new action needed).**

---

## Remaining work in this remediation pass

Final runtime verification across all priorities (backend health, frontend
build, full browser route sweep, and the six required end-to-end Tests A-F)
is recorded in `AUDIT/11_FINAL_RUNTIME_VERIFICATION.md`.
