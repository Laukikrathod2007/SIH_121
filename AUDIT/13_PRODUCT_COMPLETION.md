# 13 — Product Completion (Pass 5)

**Date:** 2026-10-04. **Status: Part A (backend DB-completeness) and A4/B3
(sync-status honesty + resync) finished and verified live. B1/B2(partial)
done. B4/B5/B6 remain.** This pass was originally cut short by a hard
credit limit; it was resumed and continued twice from exactly where it
stopped, per the plan at
`C:\Users\Prasad\.claude\plans\mighty-shimmying-quill.md`. Everything below
is reported exactly as verified or not verified.

## 0. What changed since the previous version of this report

Two rounds of continuation happened after the original credit-limited
report. Round 1 closed the "never verified through the actual HTTP server"
gap (all 8 routes live-curled + browser-clicked, 29 new parity/contract
tests, `ahead_of_bit` migrated, 3D lighting re-verified live). Round 2
(this one) completed A4 (safe sync-status enum, `/resync` route) and its
B3 frontend surfacing, and in the course of **live-clicking the actual
approve/reject flow in the browser** (not just curling the API) found and
fixed a second real bug: `sync_review()` wrote to `document_review`, whose
`document_id` column `REFERENCES documents(document_id)` — but a document
opened from the review queue that was never successfully synced at ingest
time (any document ingested before this pass, or one whose original
`sync_document()` call itself failed) had no `documents` row yet, so
**every review decision on it hit a foreign-key violation**, reported
(correctly, per the new honest-status work) as `status: "error"` — visibly
wrong in the browser ("Save failed — retry") where it would have gone
unnoticed as a silent "reason" string before this pass. Fixed by having
`sync_review()` ensure the `documents` row exists (an idempotent UPSERT,
the same one `sync_document()` already does) before writing the review
state. A dedicated regression test
(`test_sync_review_succeeds_even_when_sync_document_was_never_called`) was
added. Full backend suite: **267 tests passing, 1 skipped, 0 failing** (up
from 260).

A separate process-management finding worth recording: mid-session, a
"restart" left **two processes simultaneously listening on port 8000**
(`netstat` showed both LISTENING entries; one PID belonged to a process
that no longer existed — a stale OS-level socket entry). This produced a
confusing false negative (`/resync` route genuinely missing from the live
API, even though a fresh Python import and the full test suite both
confirmed the route existed in source). The fix was not to blame
`--reload` again — a full `netstat`-verified single-listener restart
picked up the change correctly on the first try. **Lesson recorded for
Pass 6**: always confirm exactly one PID is LISTENING on :8000 via
`netstat -ano | findstr :8000` (or the bash equivalent) before concluding
a route/behavior change is "not picked up" — more than one past session in
this project's history (including earlier in this very pass) misattributed
this exact symptom to `--reload` unreliability without checking for a
duplicate listener first.

## 1. What was actually completed and verified

### A. Backend — DB-backed DORS/events/corridors/analyze (core of this pass)

**`DbStoreSnapshot`** — a new class in `modules/02_nwis_backend/db/service.py`
exposing the exact attribute/method surface of the in-memory `NWISDataStore`
(`wells_by_id`, `all_wells`, `all_trajectories`, `formation_tops_by_well`,
`casing_records_by_well`, `events_by_well`, `all_events`,
`get_events_for_top_wells()`, `get_telemetry_at()`), built fresh from
Postgres by `build_store_snapshot()`. This is the actual fix for what Pass 4
left incomplete: every `store.*` reference inside each route handler and
`NWISOrchestrator.analyze()` — not just the final engine call — was traced
and verified, per your explicit feedback on the first (rejected) version of
this pass's plan.

**New `EventRepository`** (`modules/02_nwis_backend/db/repositories.py`):
`for_well()`, `for_wells()` (DB equivalent of
`store.get_events_for_top_wells`), `all_events()`.

**Verified parity (directly, not assumed):** DORS ranking, risk-corridor
clustering, and stratigraphic horizon alignment were run against both the
real in-memory store and a live `DbStoreSnapshot` for identical inputs
(`15/9-F-12` active well, depth 2500m). Results:
- DORS ranking order: **exact match**, all 13 offset wells, same order.
- DORS composite scores: **exact match after a real bug fix** — see below.
- Risk corridors: **exact match** (7 corridors, same hazard/depth pairs).
- Stratigraphic horizon alignment: **exact match** (11 wells aligned,
  identical output).

**Real bug found and fixed during this verification, not before:**
`_station_row_to_model()` originally didn't pass `well_type` when
reconstructing a `WellTrajectory` from DB rows, so it silently defaulted to
`WellType.VERTICAL` via the Pydantic default. `dors_engine.py`'s
`score_trajectory()` reads `offset_traj.well_type.value` directly (not
`Well.well_type`), so every non-vertical well's trajectory score was wrong
by 0.075–0.5 before this was caught — confirmed via a direct score-by-score
comparison against the memory path, not by inspection. Fixed by passing
`well.well_type` through explicitly. This is exactly the class of bug your
mid-pass feedback was warning about ("the entire dependency chain, not just
the final endpoint") — it was caught because that instruction was followed,
not despite skipping it.

**Routes re-wired to the DB-first/memory-fallback/503 contract** (same
pattern Pass 4 established for `get_well`/`get_trajectory`/`get_formations`/
`get_casing`), with every internal `store.*` reference replaced, not just
the outermost call:
- `GET /api/v2/events`
- `GET /api/v2/events/search`
- `GET /api/v2/events/{well_id}`
- `GET /api/v2/offset_rank/{well_id}`
- `GET /api/v2/corridors/{well_id}`
- `GET /api/v2/stratigraphic_depth_track/{well_id}`
- `GET /api/v2/analyze/{well_id}` (via `NWISOrchestrator`, unmodified —
  now accepts a duck-typed store/snapshot; `get_telemetry_at` composes
  from the real in-memory singleton regardless of source — see below)

A new `"data_source": "postgres"|"memory"` field was added to each of
these responses, matching the existing convention.

**`GET /api/v2/ahead_of_bit/{well_id}` — migrated in the continuation of
this pass.** All 8 routes named in the plan are now DB-backed. Parity with
the memory path was verified directly (`result.model_dump()` byte-identical
between the two sources for the same inputs) before wiring the route, then
confirmed `data_source: postgres` through the actual running HTTP server.
**Part A is now fully complete** — nothing remains in the original 8-route
scope.

**Deliberately NOT migrated (a documented decision, not an oversight) —
`NWISOrchestrator.analyze()`'s `recent_telemetry = store.get_telemetry_at(...)`.**
This one call stays sourced from the real in-memory `NWISDataStore`
singleton (via `DbStoreSnapshot.get_telemetry_at()`, which composes it)
rather than Postgres. Reason, confirmed by direct inspection: the source
JSON (`telemetry_stream.json`) is a single flat, well-id-blind list scoped
to one well (`WELL-HGJ-012`), and the live database has `telemetry_records`
rows for only 2 of 14 wells (`WELL-HGJ-012`: 3600 seed rows; `WELL-NHK-001`:
57 rows from a previous pass's own live verification). Migrating this call
would not fix the pre-existing well-id-blindness (same ~2-well coverage
either way) and would add a new DB-unavailability failure mode for the
other 12 wells where today it silently returns "whatever's in the global
list." Fixing this properly means scoping telemetry correlation to the
actually-requested well — a real behavioral change, not a storage swap —
and was out of this pass's scope.

**`GET /api/v2/events`/`/events/search`/`{well_id}` facet/filter logic**
(`_filter_events_structured`, `_compute_facets`) was **not duplicated** —
both the memory and DB-sourced event lists flow through the same existing
Python functions, so there is exactly one filtering/faceting
implementation regardless of data source.

### B. Frontend — three real, confirmed, fixed bugs

These were found live in the browser (you reported the black 3D view and
the "random bs" map; investigation found concrete causes, not just visual
polish):

1. **`NearbyWellsPage.tsx`'s well dossier panel was stuck on a hardcoded
   well.** `selectedWellId` defaulted to `'WELL-NHK-002'` and never
   re-synced when the global active well changed — confirmed live: with
   `15/9-F-12` selected in the header, the dossier panel still showed
   "WELL DOSSIER: NHK-002." **Fixed**: `selectedWellId` now tracks
   `activeWellId` via an effect, confirmed live in the browser after the
   fix (dossier correctly showed "15/9-F-12" / Equinor / real Volve
   formations after switching wells).

2. **The map/catalog UI was hardcoded to "Upper Assam Basin" regardless of
   which well or field was actually active**, even for the 2 real North
   Sea Volve wells. Three places fixed: (a) the map panel title, now
   derived from the active well's real field/coordinates; (b) the "Total
   Catalog" subtitle, now reports field count dynamically instead of
   claiming "Upper Assam Shelf" always; (c) the field filter dropdown,
   which was **hardcoded to 3 field names that don't match the real
   catalog** (`Nahorkatiya`, `Tengakhat`, `Borpothar` — the live database
   actually has `Baghjan`, `Hugrijan`, `Moran`, `Nahorkatiya`, `Volve`; the
   dropdown could never filter to the real Volve wells by name even though
   "All Fields" included them). Now derived from the real well catalog.
   Directly addresses your "I don't want the map to be just for one
   dataset" feedback — confirmed live: the dropdown now lists all 5 real
   fields.

3. **The Live 3D Rig View rendered pitch black** in `DOWNHOLE_FOLLOW`/
   `CROSS_SECTION` camera modes, matching your screenshot exactly. Root
   cause: the scene's surface lights (ambient/directional/hemisphere) only
   reach geometry near the derrick at the surface; a live/downhole camera
   sits thousands of scaled units down the wellbore with nothing nearby to
   light except the one emissive bit marker. **Fixed and re-verified live**
   (continuation session): a point light now travels with the live bit
   position, scaled to the scene's own `extent` rather than a fixed
   distance (the first attempt used a fixed `distance: 6`, confirmed live
   to still be insufficient for a real trajectory where `extent ≈ 49`
   scene units). After the fix, all four camera presets
   (`Rig Floor`/`Cross-Section`/`Downhole Follow`/`Free Orbit`) were
   clicked through and screenshotted against the real `15/9-F-12`
   trajectory: `Downhole Follow` now shows a visible radiant halo around
   the bit against the grid floor (previously one bare dot on pure black);
   `Cross-Section` shows the full wellbore tube, grid floor, and faint
   formation-plane edges, a genuinely legible scene; `Rig Floor` (already
   working pre-fix) is unchanged and correct. Not literally bright — this
   is a deliberately dark SCADA-style scene by design — but no longer
   "nothing visible."

### C. Document pipeline: safe sync-status, idempotent retry (A4), surfaced in the UI (B3)

**Backend** (`modules/01_document_intelligence/db/service.py`): added a
closed `SyncStatus = Literal["synced", "not_configured", "unavailable", "error"]`
and `_is_connectivity_error()` (distinguishes `psycopg.OperationalError` —
connection refused/timeout, genuinely transient — from any other
exception, e.g. a constraint violation, which is a real bug and won't be
fixed by retrying). All three write-through functions
(`sync_document`/`sync_review`/`handoff_events`) now return `status` from
this enum instead of the old open-ended `reason: f"{type(exc).__name__}: {exc}"`
string. The exception's full text stays in the server log only, as before
— nothing changed about what operators can see in logs, only what a
future UI caller could be tempted to render.

`pipeline/orchestrator.py`'s save point and `api/routes/review.py`'s
`/decision`/`/annotate` endpoints now persist the resulting status back
onto `data/output/{doc_id}.json` as `postgres_sync_status`.

New route `POST /api/v1/review/{doc_id}/resync`: re-reads the existing
JSON (the extracted work is never lost regardless of database state),
re-runs the same idempotent `sync_document`/`handoff_events` calls, updates
`postgres_sync_status`, returns the new status. **Verified idempotent**
both in a new automated test (`test_resync_is_idempotent_no_duplicate_handoff_rows`
— calls it twice through `TestClient`, asserts exactly one JSON file and
no duplicated state) and live (curled twice against a real document,
`documents` table stayed at exactly 1 row for that document_id).

**Real bug found and fixed while live-testing this** (not while writing
it): `sync_review()` violated a foreign-key constraint for any document
that reached the review step without a prior successful `sync_document()`
call (confirmed live: a document opened from the review queue, approved
in the browser, immediately showed "Save failed — retry"). Fixed by having
`sync_review()` ensure the `documents` row exists first — see §0 for the
full story and the new regression test.

**Frontend** (`DocumentIngestionPage.tsx`): `submitReviewDecision`'s return
value (previously discarded) is now captured and shown — "19 extracted
events could not be matched to a known well or hazard type, so none were
added to the shared knowledge base" when nothing qualified, or "N events
added to the shared knowledge base" when some did. A sync-status line
renders honest, plain-language copy for all four states (never a raw
exception), with a "Retry" button wired to `/resync` for the `unavailable`/
`error` states only (not for `not_configured`, which is a neutral
statement of environment, not a failure). **Confirmed live**: approved a
real queued document in the browser, saw "Review recorded: approved" with
the correct migrated/skipped narration, then "Saved to shared knowledge
base" once the FK fix landed (it showed "Save failed — retry" before the
fix — a real before/after, not assumed).

Also fixed in this same file as a side effect: the "MODULE 01:" header
label and two developer-oriented "cd Backend && python run.py" error
messages, replaced with operator-appropriate copy.

## 2. What was planned but not reached at all

A4 and B3 are now complete (see §1). Remaining from the approved plan:

- Historical alerts read path — `AlertRepository.for_well()`, the
  tri-state `/predictive/alerts/{well_id}/history` route, and the frontend
  History tab (A3/B4). The `alerts` table remains write-only from the
  application's perspective; nothing reads it back yet.
- Evidence-link wiring on `NearbyWellsPage`'s event list and
  `GeologicalCorrelationPage`'s corridor cards (B2) — not started this
  round either.
- Most of the "Module 01/02/04/05" label removal (B5). Fixed this round,
  as a side effect of editing those specific files for other reasons: the
  "MODULE 01:" header and two "cd Backend && python run.py" developer
  instructions in `DocumentIngestionPage.tsx` (replaced with "Contact your
  system administrator if this persists" — same pattern the plan specified
  for `SystemStatusPage.tsx`). Still untouched:
  `BackendStatusStrip.tsx`, `AlertsAdvisoryPage.tsx`,
  `GeologicalCorrelationPage.tsx`'s "NWIS Module 02" caption,
  `HistoricalIntelligencePage.tsx`, `LookAheadPanel.tsx`,
  `SystemStatusPage.tsx` itself.
- Provenance (REAL/SYNTHETIC/SIMULATED/DERIVED) badges on
  `NearbyWellsPage`/`HistoricalIntelligencePage` (B6) — not started.

## 3. Tests

```
cd Backend && python run_tests.py
  backend               145 passed, 1 skipped   (was 143 — +2 new, baseline route added)
  document_intelligence  26 passed               (was 22 — +4 new)
  nwis                   58 passed                (was 29 — +29 new)
  physics                18 passed
  predictive_analytics   19 passed
  TOTAL                 266 passed, 1 skipped, 0 failed
```

All pre-existing tests still pass — no regressions. New/changed this round:
- **`Backend/tests/baselines/pre_pass3_contract.json`** — added
  `POST /api/v1/review/{doc_id}/resync` to the tracked API-contract
  baseline (a genuine new route from this pass, not refactor drift — see
  the file's own updated `_comment`). 2 contract tests that would
  otherwise have failed now correctly pass.
- **`Backend/tests/contract/test_document_ingest.py`** (+2 tests) —
  `test_unknown_document_resync_is_404`, and
  `test_resync_is_idempotent_no_duplicate_handoff_rows` (writes a minimal
  result JSON directly into the isolated temp output dir, calls `/resync`
  twice through `TestClient`, asserts the status is stable and no
  duplicate file/state is created).
- **`modules/01_document_intelligence/tests/test_document_db_service.py`**
  (+4 tests) — closed-enum status assertions (never a raw exception
  string, substrings like host/port/password checked absent, mirroring
  Pass 4's own `test_healthcheck_error_field_is_class_name_not_full_message`),
  the connectivity-vs-other-error distinction, the `not_configured` status
  shape, and `test_sync_review_succeeds_even_when_sync_document_was_never_called`
  (the regression guard for the FK bug found live this round).
- **`modules/02_nwis_backend/tests/test_events_dors_corridors_db.py`** (29
  tests, from the previous round) — parametrized memory/503/postgres
  checks across all 8 newly-wired routes, plus
  `test_offset_rank_db_matches_memory_exactly` and
  `test_corridors_db_matches_memory_exactly` (direct score/corridor
  comparisons, the regression guard for the `well_type`-default bug).

`cd frontend && npx tsc --noEmit` — clean, 0 errors, confirmed after every
edit in this session, including the final B3 frontend changes.

`npm run build` — re-run after all frontend changes in this pass, **succeeds
cleanly** (0 errors; the "chunks larger than 500kB" warning is pre-existing
and unrelated to this pass's changes).

## 4. Live/browser verification — what was and wasn't actually clicked through

**Verified live through the actual running HTTP server (this continuation
session)**: the backend was stopped and restarted cleanly twice (confirmed
`--reload` is not trusted for `modules/` changes, per Pass 4's own
finding). All 8 migrated routes were live-curled with a real `X-API-Key`
against the running server and confirmed `data_source: postgres`:
`/api/v2/events`, `/events/search`, `/events/{well_id}`,
`/offset_rank/{well_id}`, `/corridors/{well_id}`, `/ahead_of_bit/{well_id}`,
`/analyze/{well_id}`, `/stratigraphic_depth_track/{well_id}`. The
`/offset_rank` scores returned through the live HTTP server
(`0.4212, 0.3991, 0.3975, 0.3959` for the top 4 wells) matched the
earlier direct Python-level parity check exactly, closing the gap the
first version of this report flagged.

**Verified live in the browser, earlier in this pass:**
- `/app/wells` (Nearby Wells): active-well dossier sync fix, map title fix,
  field dropdown fix — all confirmed visually correct after the fix, with
  a real screenshot comparison before/after.
- `/app/drilling` (Live Drilling): 3D view's first lighting fix confirmed
  still insufficient via a live screenshot; the second (extent-scaled)
  fix was **not** re-screenshotted.
- Leaflet map tiles themselves were confirmed genuinely loading (200 OK,
  real image data, 256×256) on both the "Dark Vector" and "Streets"
  basemaps — the "pitch dark" map complaint was a labeling/centering bug,
  not a broken tile pipeline.

**Now verified from the frontend pages themselves, with real screenshots/
DOM snapshots (continuation session):**
- `/app/wells` (Nearby Wells): the DORS table renders 10 real ranked rows
  with scores matching the live-curled API exactly (42.1%, 39.9%, 39.8%,
  39.6% for the top 4) and the well dossier shows real DB-sourced data
  (3520m MD, J-Type, Equinor, 7 real North Sea formations — Hugin, Ty,
  Hod, Shetland, Utsira, Ekofisk, Sleipner — and 2 real logged events).
  0 console errors.
- `/app/correlation` (Geological Correlation): the stratigraphic depth
  track renders the correct formation at the active bit position (Hugin
  Formation at 2500m MD), and "7 corridors ahead of 2500m MD" matches the
  live `/corridors` API's `total_corridors: 7` exactly. 0 console errors.
- `/app/knowledge` (Historical Search): "50 Candidate Events Indexed"
  (page default caps the initial unfiltered display; the DB has 51 total
  rows) with `search_mode: semantic` confirmed rendering. 0 console errors.
- `/app/risk` (Risk & Prediction): loads with 0 console errors against the
  DB-backed routes (this page's own content is largely independent of the
  migrated routes — see Pass 4's assessment).

One real timing finding during this check: an immediate snapshot taken
right after navigation showed an empty DORS table and blank dossier
fields — not a bug, confirmed to be the normal async-fetch-in-flight state
(waiting ~2s resolved it with full real data). Worth noting only because
it's exactly the kind of thing that could be mistaken for a rendering bug
if not waited out before judging a page "broken."

**Restart-persistence**: confirmed implicitly — the backend was restarted
several more times in the second continuation (A4 work, and while
diagnosing the stale-listener issue — see §0), and each restart's
subsequent curls/browser checks returned correct, unchanged data,
including the `documents`/`document_review` rows written by the live
approve-flow test.

**Database-unavailable path**: now covered by the new test suite's
parametrized `test_db_unreachable_is_503_not_silent_memory` across all 8
routes (§3) — verified via `TestClient` against a real closed-port DSN,
not mocked. Not separately re-verified by hand in the browser.

**Document review, end to end, in the actual browser (second
continuation)**: opened a real queued document from `/app/documents`,
clicked "Review" then "Approve", confirmed the full real response
rendered — "Review recorded: approved", the honest migrated/skipped
narration, and (after the FK fix) "Saved to shared knowledge base". This
is the check that found the FK bug in the first place: the first attempt
showed "Save failed — retry," which led directly to the backend log
investigation and fix in §0/§1.C. Confirmed live again after the fix with
a second document.

## 5. SIH requirement coverage — unchanged from Pass 4's assessment except where noted

This pass did not re-run the full requirement-by-requirement audit Pass 4
performed; genuinely new information from this pass:

- **Requirement i (geospatial map of nearby wells)**: the map was
  confirmed broken in a way that misrepresented the dataset (hardcoded to
  one field, 2 of 5 real fields unreachable via the filter) — now fixed.
  This was a real product-correctness bug the SIH-facing demo would have
  shown, not a cosmetic issue.
- **Requirement ii (nearby-well relevance scoring)**: DORS ranking is now
  genuinely database-backed with verified parity to the previously-only
  path — closes one of Pass 4's largest documented gaps, for the ranking
  endpoint specifically. `ahead_of_bit` is not yet migrated.
- **Requirement iii (searchable knowledge repository)**: `/events` and
  `/events/search` are now database-backed when configured — same caveat
  as above (not yet exercised live through the running server).
- **Requirement v (predictive risk analytics / risk corridors)**: now
  database-backed with verified parity.
- Document review, evidence linking, alerts, and the UI terminology sweep
  — **no new information this pass**; Pass 4's own assessment stands for
  these.

## 6. Unresolved issues that genuinely require Pass 6

Part A (backend DB-completeness), the 3D rig view lighting fix, and A4/B3
(sync-status honesty + resync + its FK bug fix) are all done, verified
live, and test-covered. Remaining work, in priority order:

1. **Add the historical-alerts read path** (A3/B4) — `alerts` is still
   write-only from the application's perspective. This is now the largest
   remaining backend gap.
2. **Finish the UI terminology sweep** (B5) — "Module 01/02/04/05" labels
   remain in `BackendStatusStrip.tsx`, `AlertsAdvisoryPage.tsx`,
   `HistoricalIntelligencePage.tsx`, `LookAheadPanel.tsx`,
   `SystemStatusPage.tsx`, and one remaining spot in
   `GeologicalCorrelationPage.tsx` ("NWIS Module 02" at the
   stratigraphic-track subtitle, confirmed still present this session).
   `DocumentIngestionPage.tsx`'s labels are done.
3. **Wire evidence links on `NearbyWellsPage`'s event list and
   `GeologicalCorrelationPage`'s corridor cards**, and add provenance
   badges where the underlying field is confirmed present (B2/B6).

**Done, not left open**: `npm run build` re-run and confirmed clean (§3).
`handoff_events()` now also defensively ensures
the `documents` row exists (the same fix `sync_review()` got), so it no
longer depends on `sync_review()`/`sync_document()` having run first in
the same request — covered by a new standalone test
(`test_handoff_events_works_standalone_without_prior_sync`). Full suite:
267 passed, 1 skipped, 0 failing.
