# 13 — Product Completion (Pass 5, partial — stopped early on credit limit)

**Date:** 2026-10-04. **Status: INCOMPLETE.** This pass was cut short by a
hard credit limit mid-implementation. Everything below is reported exactly
as verified or not verified — nothing here should be read as "done" unless
explicitly marked verified. The remaining plan (saved at
`C:\Users\Prasad\.claude\plans\mighty-shimmying-quill.md` on the machine
this ran on) is the source of truth for what Pass 6 should pick up.

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

**Deliberately NOT migrated — `GET /api/v2/ahead_of_bit/{well_id}`.** The
plan called for this route too; it was not reached before the credit
limit. It still works exactly as before (pure in-memory), just not yet
DB-backed. This is the single concrete incomplete item from Part A.

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
   light except the one emissive bit marker. **Partially fixed**: added a
   point light that travels with the live bit position. **First attempt
   verified live and found still insufficient** — a fixed `distance: 6`
   light couldn't reach the camera's own position for a real trajectory
   (`extent ≈ 49` scene units for `15/9-F-12`). **Revised to scale the
   light's range and intensity with the scene's own `extent`** — this
   second version was written but **not re-verified live before the credit
   limit hit**. TypeScript compiles cleanly; the actual visual result in
   `DOWNHOLE_FOLLOW` mode was not re-screenshotted after the fix. Treat
   this one as unverified, not done.

**None of Part B's remaining items** (evidence-link wiring on
NearbyWells/corridors, sync-status UI, alert-history UI, the "Module
01/02/04/05" label removal sweep, provenance badges) were started.

## 2. What was planned but not reached at all

From the approved plan, the following received zero implementation work:

- `GET /api/v2/ahead_of_bit/{well_id}` DB migration (A2, last item).
- Historical alerts read path — `AlertRepository.for_well()`, the
  tri-state `/predictive/alerts/{well_id}/history` route, and the frontend
  History tab (A3/B4). The `alerts` table remains write-only from the
  application's perspective; nothing reads it back yet.
- Document pipeline safe sync-status enum, `/resync` route, and the
  frontend sync-status badge / migrated-events display (A4/B3). The raw-
  exception leak in `sync_document()`'s `reason` field (flagged in your
  feedback on the plan) is **still present** — `f"{type(exc).__name__}: {exc}"`
  is still what gets returned/logged; it was never routed into a
  user-facing field in Pass 4 or this pass, so the leak's blast radius is
  currently "internal log line only," not "visible to an end user" — but
  the closed-enum fix itself was not implemented.
- Evidence-link wiring on `NearbyWellsPage`'s event list and
  `GeologicalCorrelationPage`'s corridor cards (B2).
- All of the "Module 01/02/04/05" label removal across
  `BackendStatusStrip.tsx`, `AlertsAdvisoryPage.tsx`,
  `GeologicalCorrelationPage.tsx` (the one caption, not the page I already
  touched), `HistoricalIntelligencePage.tsx`, `LookAheadPanel.tsx`,
  `SystemStatusPage.tsx` (B5). I did remove "MODULE 2:" from
  `NearbyWellsPage.tsx` as a side effect of editing that file for the
  dossier-sync fix, but every other confirmed location from the original
  Explore sweep is untouched.
- Provenance (REAL/SYNTHETIC/SIMULATED/DERIVED) badges on
  `NearbyWellsPage`/`HistoricalIntelligencePage` (B6).

## 3. Tests

```
cd Backend && python run_tests.py
  backend               143 passed, 1 skipped
  document_intelligence  22 passed
  nwis                   29 passed
  physics                18 passed
  predictive_analytics   19 passed
```

All pre-existing tests still pass — no regressions from today's backend
changes. **No new automated tests were added for the newly-wired DB-backed
routes** (events/search/offset_rank/corridors/stratigraphic_depth_track/
analyze) — the plan called for `make_client`-pattern tests mirroring
`test_api_well_endpoints.py`'s existing memory/503/postgres-provenance
triad, plus a DORS ranking-parity regression test. None of that was
written; the parity verification that *was* done (§1.A) was ad hoc,
interactive, run-once-and-discarded Python, not a committed test file. **A
genuine gap**: there is currently no regression protection against the
exact class of bug (`well_type` defaulting silently) that was just found
and fixed — if it regressed, nothing would catch it automatically.

`cd frontend && npx tsc --noEmit` — clean, 0 errors, confirmed after every
edit in this session.

`npm run build` was **not** re-run after the final round of frontend edits
in this session (it was run successfully earlier in this conversation,
before the NearbyWellsPage/3D-lighting fixes).

## 4. Live/browser verification — what was and wasn't actually clicked through

**Verified live in the browser, this session:**
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

**Not verified live at all this session** (only Python-level engine/data
checks, described in §1.A): the 7 newly re-wired `/api/v2/...` routes were
never hit through an actual HTTP request against the running server, and
never exercised from the frontend pages that call them
(`NearbyWellsPage`'s DORS table, `GeologicalCorrelationPage`,
`HistoricalIntelligencePage`'s structured filters, `RiskPredictionPage`'s
corridor data). The backend process running on :8000 during this session
was started before these route changes and was not restarted before the
credit limit hit — `--reload` was separately confirmed unreliable for
picking up changes under `modules/` in Pass 4, so there is **no
confirmation these routes behave correctly through the actual running
HTTP server**, only that the underlying Python functions produce correct
results when called directly.

**Restart-persistence**: not tested this pass (nothing new was persisted
to the database this pass — all the work was on read paths).

**Database-unavailable path**: not tested this pass for the newly-wired
routes (`_get_data_source()`'s 503 branch was written following the exact
pattern Pass 4's tests already cover for `get_well` etc., but no dedicated
test or live check confirmed it for the new routes specifically).

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

In priority order:

1. **Live-verify the 7 newly-wired routes through the actual running HTTP
   server and from the real frontend pages that call them.** This is the
   single most important item — everything in §1.A was verified at the
   Python-function level, never through an actual request. Restart the
   backend cleanly (confirmed in Pass 4 that `--reload` cannot be trusted
   for `modules/` changes), then exercise `/app/wells`'s DORS table,
   `/app/correlation`, `/app/knowledge`'s structured filters, and
   `/app/risk`'s corridor data against both DB-configured and
   DB-unconfigured modes.
2. **Write the regression tests the plan called for** —
   `make_client`-pattern memory/503/postgres tests for all 7 routes, plus
   a committed DORS-parity test (not just the ad hoc verification already
   done) so the `well_type`-default class of bug can't silently regress.
3. **Finish `GET /api/v2/ahead_of_bit/{well_id}`'s DB migration** — the one
   remaining Part A route, same pattern as the other 7.
4. **Re-verify the 3D rig view's lighting fix live** — the extent-scaled
   version was written and compiles but was never re-screenshotted;
   confirm `DOWNHOLE_FOLLOW`/`CROSS_SECTION` actually render visible
   geometry now, for a real (not just synthetic-flat) trajectory.
5. **Fix the raw-exception leak in `sync_document()`'s `reason` field**
   (flagged explicitly, not yet addressed) and build the rest of A4/B3
   (safe sync-status enum, `/resync` route, frontend status badge,
   migrated-events display).
6. **Add the historical-alerts read path** (A3/B4) — `alerts` is still
   write-only from the application's perspective.
7. **Finish the UI terminology sweep** (B5) — "Module 01/02/04/05" labels
   remain in `BackendStatusStrip.tsx`, `AlertsAdvisoryPage.tsx`,
   `HistoricalIntelligencePage.tsx`, `LookAheadPanel.tsx`,
   `SystemStatusPage.tsx`, and one remaining spot in
   `GeologicalCorrelationPage.tsx`.
8. **Wire evidence links on `NearbyWellsPage`'s event list and
   `GeologicalCorrelationPage`'s corridor cards**, and add provenance
   badges where the underlying field is confirmed present (B2/B6).
9. **Re-run `npm run build`** after all frontend changes land together —
   it was not re-run after the final edits in this session.
