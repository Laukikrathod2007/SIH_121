# End-to-End Verification & Stabilization Pass

**Date:** 2026-10-03/04
**Method:** Full clean-state service restart, followed by a real Chromium browser (Playwright) walkthrough of every route, the primary SIH user journey, deep 2D/3D synchronization testing, a rigorous (and initially wrong, then corrected) geographic-correctness investigation of the 3D globe, asset-integrity checks, a realistic navigation stress test, and an architectural-duplication check. Every finding below reflects actual runtime behavior observed in this pass, not inference from prior reports — prior `AUDIT/0{1,2,3}` documents were used only as a starting map, and several of their claims were re-verified or superseded here where live behavior disagreed.

---

## Environment

All five services killed and restarted from a cold state (no reused stale processes) to avoid hiding startup problems, per task instruction.

| Service | Command (from its own directory) | Port | Interpreter |
|---|---|---|---|
| Module 01 | `python run_server.py` | 8001 | Python 3.12 (`C:\Users\Prasad\AppData\Local\Programs\Python\Python312\python.exe`) |
| Module 02 | `python run_server.py` | 8002 | Python 3.12 |
| Module 04 (+05) | `python run_server.py` | 8003 | Python 3.12 |
| evidence-server | `PORT=4100 node index.js` | 4100 | Node (system) |
| frontend | `npm run dev` | 5173 | Vite 5.4.21 |

All five started cleanly with no startup errors. Health/auth verified directly with curl before any browser testing:

- Module 01: `GET /api/v1/health` → `200 {"status":"healthy", ...}`; `GET /api/v1/jobs` → `401` without key, `200` with the real key.
- Module 02: `GET /api/v2/health` → `200`, 14 wells/106 tops/44 events/3600 telemetry records loaded; same 401/200 auth pattern.
- Module 04/05: `GET /health` → `200`, `anomaly_detector_fitted: false`, `xgboost_fitted: false` (honestly self-reported, consistent with prior passes); same 401/200 auth pattern.
- evidence-server: `GET /` → `200`, "42 PDFs available."
- frontend: `GET /` → `200`.

No console/server errors were observed during the entire multi-hour verification session (confirmed by reviewing the full stdout/stderr of all three Python backends at the end of the pass — zero tracebacks, zero 500s).

---

## Service verification

| Service | Status | Evidence |
|---|---|---|
| Module 01 | **HEALTHY** | Confirmed via `SystemStatusPage` live re-ping; real document ingestion exercised (see Core User Journey) |
| Module 02 | **HEALTHY** | Confirmed via `SystemStatusPage`; real well/event/DORS/search data verified against curl ground truth throughout |
| Module 04/05 | **HEALTHY** | Confirmed via `SystemStatusPage`'s now-real third card (see Problems Fixed); rule-engine pillar ACTIVE, ML pillars honestly UNFITTED_FALLBACK |
| evidence-server | **LIVE, SERVING REAL PDFS** | Real PDF fetched and rendered in the Offset Map's evidence viewer during the journey test |

---

## Route verification

All 17 routes loaded with **0 console errors** on an individual, normally-paced visit:

`/`, `/benchmarks`, `/app`, `/app/command-center`, `/app/drilling`, `/app/wells`, `/app/offset-map`, `/app/globe`, `/app/correlation`, `/app/risk`, `/app/alerts`, `/app/knowledge`, `/app/copilot`, `/app/documents`, `/app/simulator`, `/app/reports`, `/app/status`.

Screenshots captured for the landing page, benchmarks page, dashboard (before and after fix), nearby wells, offset map, 3D globe, correlation, knowledge search with evidence, system status (before and after fix), command center, and live drilling 3D scene — see `AUDIT/evidence/`.

**429 (rate limit) responses did occur during this pass**, but only during deliberately rapid repeated automated re-navigation used for isolating a specific bug (see "Rate-limit investigation" below) — never during a normally-paced single visit or the full realistic navigation cycle in §7.

---

## Core user journey

Executed as a real user, via sidebar clicks (client-side navigation, not hard reloads, so state persists exactly as it would for a real user):

1. **Open application** (`/app`) — real dashboard, real backend status strip, real DORS/stratigraphic data. ✅
2. **Choose active well** (header dropdown → `HGJ-012`) — confirmed selection took effect immediately. ✅
3. **Inspect nearby wells** (`/app/wells`) — real DORS 5-factor ranking table, real Leaflet map (now correctly tiled, see Problems Fixed). ✅
4. **Change radius** (15km → 3 wells, 50km → 6 wells) — cross-checked against an independent Haversine calculation from the real well coordinates; **exact match**. ✅
5. **Select an offset well** (`WELL-HGJ-010`, #1 ranked) — well dossier updated to show HGJ-010, SUSPENDED. ✅
6. **Inspect well details** — total depth, profile, KB elevation, operator all real, matching the direct API response. ✅
7. **Inspect historical events** — real NPT hazard list with real narrative text, IADC codes, formation names. ✅
8. **Inspect formation/depth context** (`/app/correlation`) — active well correctly carried over (`HGJ-012`), real stratigraphic data rendered. ✅
9. **Inspect correlation** — 0 console errors, real cross-section data. ✅
10. **Inspect risk/alert information** (`/app/risk`, `/app/alerts`) — 0 console errors; RiskPredictionPage's illustrative labels confirmed still present and un-touched. ✅
11. **Open knowledge/search** (`/app/knowledge`) — real semantic search (`search_mode: semantic`), real relevance-ranked results, real hazard/formation/severity facets. ✅
12. **Inspect supporting evidence** — clicked a real citation; the module-01-backed `PdfEvidenceViewer` honestly reported "Source document not found in module 01's archive" for an event whose record predates the live ingestion pipeline — a genuine, already-correct honest-failure path, not a bug (see "Problems found" for why this is not counted as one). ✅
13. **Switch to 3D globe** (`/app/globe`) — active well (`HGJ-012`) correctly carried over via shared state, confirmed by the panel showing "ACTIVE WELL: HGJ-012" immediately on arrival, no re-fetch-from-scratch/reset. ✅
14. **Select another well** (clicked `WELL-HGJ-011` in the globe's own DORS ranking panel). ✅
15. **Return to other application views** (Command Center) — header dropdown confirmed showing `HGJ-011` selected, proving the 3D→global state write propagated correctly. ✅
16. **Confirm state remains synchronized** — see the dedicated synchronization section below for the full bidirectional proof.

**Journey result: PASS, no steps blocked, no unexplained errors.**

---

## 2D/3D synchronization

All four required directions tested with real clicks in a real browser, not assumed:

| Test | Result |
|---|---|
| Header → 3D (select `HGJ-012` via dropdown, navigate to globe) | **PASS** — globe's "ACTIVE WELL: HGJ-012" panel, marker, and DORS ranking all reflected the real well immediately |
| 3D → global application (click `WELL-HGJ-011` in the globe's ranking list, navigate to Command Center) | **PASS** — header dropdown showed `HGJ-011 (HGJ) - Vertical` selected |
| 2D → 3D (select well + radius in Nearby Wells, navigate to globe via sidebar) | **PASS** — same active well, same real DORS ranking values (e.g. HGJ-010 at 1.55/1.6km, 94%/72% spatial — matching across both views within expected rounding) |
| Radius (tested at two independent wells) | **PASS, exact match against ground truth** — `HGJ-012`: 15km→3, 50km→6 wells. `HGJ-011`: 5km→0, 15km→2, 50km→5 wells. Both independently recomputed via Haversine from the real lat/lon in this session and matched the UI exactly. |

No duplicated state was found or introduced: `activeWellId` has exactly one definition (`AppContext.tsx`), confirmed by repo-wide grep.

---

## 3D verification

| Aspect | Result |
|---|---|
| Earth texture | Real 2:1 equirectangular day/night textures, confirmed pixel-sampled against known real-world coordinates (Assam = green/vegetation, Mongolia = tan/steppe, Pacific = blue) before use |
| Marker positions | **A real bug was found, investigated rigorously, and fixed** — see "Problems found/fixed" below. After the fix, verified correct via an isolated test harness (camera pointed exactly along the formula's own computed direction for Assam, confirmed the real Himalayan/northeast-India coastline sits exactly there) AND via the live app (HGJ-011's marker, after 15+ seconds of real auto-rotation, correctly over Assam/Myanmar border region) |
| Active marker | Correct size/color (cyan, larger, glow halo) vs. offset (amber) vs. catalog (slate) — confirmed visually across multiple wells |
| Camera controls (orbit/zoom) | Functional — drag-to-rotate and scroll-to-zoom both confirmed working, `minDistance`/`maxDistance` clamps respected |
| Hover tooltip | Confirmed rendering with real well name/field/depth/distance/event-count data on at least one successful hover |
| Click interaction | Confirmed — clicking a marker (and clicking a DORS-ranking-list entry) both correctly update `activeWellId` |
| Connector arcs | Confirmed rendering from active well to in-radius offset wells, correctly appearing/disappearing as radius or active well changes |
| Lighting/atmosphere | Rendered without WebGL errors; ambient + directional light, additive atmosphere rim, additive night-side layer all present |
| Resize behavior | Confirmed — resized viewport from 1920×1080 to 900×700, canvas correctly reflowed with no clipping or distortion |
| Inverted-axis / mirrored-globe checks | **Checked rigorously, see below — the real bug was a rotation-group desync, not an inverted axis in the coordinate formula itself** |

### The real geographic-correctness bug (found, misdiagnosed once, then correctly fixed)

**Finding:** `WELL-HGJ-011` (real coordinates 27.20°N, 94.75°E — Assam, India) was observed rendering over Mongolia/China (~45°N) in one screenshot, then over the Indian Ocean south of the equator in a second screenshot taken shortly after, during this verification pass.

**Investigation, honestly recorded including a wrong turn:**
1. First hypothesis: the `latLonToVec3` formula's sign convention was wrong (plausible, since it had been wrong once before in the prior 3D-integration pass). Re-derived the formula from three.js's actual `SphereGeometry` source, found a previously-missed detail (the UV assignment uses `1 - v`, not `v`), and "corrected" the `y` sign based on that.
2. **This "fix" was then tested in an isolated, controlled three.js test harness (outside the app, with a camera pointed deterministically at the formula's own output direction) and found to be WRONG** — it placed Assam over the Indian Ocean. Caught before being left in place by not trusting the derivation without an independent render-based check.
3. Reverted the `y` sign back to the original. Re-tested in the same isolated harness: **Assam, North Pole, and a south-India reference point all landed exactly correctly.** This confirmed the coordinate formula itself (`latLonToVec3`) was correct all along, including after the prior pass's fix.
4. With the formula cleared, re-examined the actual live-app scene graph composition and found the real cause: `EarthGlobe.tsx` owned its own independent auto-rotating `<group>` for the Earth texture, while `WellMarkers` was mounted as a sibling in `OffsetGlobe3D.tsx`'s Canvas — **not** inside that same rotating group. The texture rotated continuously; the markers' world positions did not. The two screenshots showing the same well in two different wrong places were two different elapsed-rotation snapshots of the same desync, not two different coordinate bugs.
5. **Fix:** introduced one shared `RotatingGroup` in `OffsetGlobe3D.tsx` that wraps both `EarthGlobe` and `WellMarkers`, and removed `EarthGlobe`'s own independent rotation. One rotation owner now, applied to both the texture and the markers together.
6. **Re-verified in the live app**: set active well to `HGJ-011`, waited 15 real seconds (several multiples of the rotation period that previously caused visible drift) before checking, then rotated the view to locate the marker — it now sits correctly over the real Assam/Myanmar/Tibet border region, matching the real coordinates, with the drift-over-time condition specifically re-tested and no longer present.

This is reported in this much detail because the task explicitly asked for honest documentation of real investigation, including wrong turns, not a cleaned-up summary.

---

## Regression testing (existing 3D components)

| Component | Where tested | Result |
|---|---|---|
| `WellTrajectory3D` (inside `WellInspector3DModal`) | `/app/wells` → "VIEW 3D TRAJECTORY" | **PASS** — 0 console errors, modal opened, real Leaflet map inside it now renders correctly (see Problems Fixed — this modal's map was also affected by the CARTO fix) |
| `LiveDrillingScene3D` | `/app/drilling` | **PASS** — 0 console errors, visible by default ("Live 3D Rig View" panel), no GLB/texture network requests (confirmed procedural geometry, consistent with its own documented design) |
| `CommandScene3D` | `/app/command-center` | **PASS functionally** — 0 console errors on load; a pre-existing, unrelated **Light-theme-only cosmetic contrast issue** was found in the "4-Pillar Confidence" panel (not specific to 3D, not a regression from this pass's globe work — confirmed by checking the same panel in Dark theme, where it renders correctly) |
| `WellCutawayCockpit` | `/app/drilling` | **PASS** — part of the same clean page load as `LiveDrillingScene3D` |

**No shared Three.js dependency, canvas configuration, or camera/control behavior was broken by the globe integration.** The `RotatingGroup` fix is scoped entirely inside `components/globe/`; it does not touch `CameraRig.tsx` or any other existing 3D component's code.

---

## Problems found

1. **[Fixed] Dashboard's "Multi-Signal Hazard Forecast" panel and its two status footers claimed module 03 "is not yet wired to an HTTP endpoint" / "module 03 — not yet wired"** — stale text from before module 04/05 existed in this project; module 04/05 is real, running, and healthy.
2. **[Fixed] SystemStatusPage's third health card was a permanently-amber static "NOT CONNECTED" block** with the same stale "has no FastAPI routes exposed yet... nothing is currently listening" claim — never polled anything, unlike the other two real cards.
3. **[Fixed] `api.ts`'s module-03 comment block** repeated the same stale "NOT YET WIRED... exposes NO FastAPI routes" claim in detail, contradicting the file's own already-corrected header comment from the prior pass.
4. **[Fixed] `useNwisMapData.ts` (Offset Map page) fired 14 separate `GET /api/v2/events/{well_id}` requests per page load** (one per well) instead of one batched call — found to be the direct, reproducible cause of 429s during normal (if slightly rapid) navigation, not merely a testing artifact.
5. **[Fixed] `BasinMap.tsx`'s "Dark Vector" basemap tile URL was broken** — CARTO's free anonymous `basemaps.cartocdn.com/dark_all` endpoint has been retired; every tile rendered an "API KEY REQUIRED" watermark instead of a map. This is the exact issue the user had flagged from an earlier session.
6. **[Fixed] Real geographic-placement bug in the 3D globe** — markers desynced from the rotating Earth texture over time (see detailed investigation above). Not present in short-lived test sessions, which is why it was not caught during the prior `03_3D_INTEGRATION.md` pass (that pass's own verification screenshots were all taken within seconds of page load, before meaningful drift accumulated).
7. **[Documented, not fixed] Light-theme cosmetic contrast issue** in `ConfidencePillars.tsx`'s `bg-slate-900/30` panel background — designed for the dark SCADA theme, renders as an odd gray smudge against the Light theme. Not a regression from this pass, not functionally broken (confirmed working correctly in Dark theme), and fixing it properly would require a broader light-theme contrast audit across the component library — outside this pass's "fix only verified problems, minimally" scope.
8. **[Documented, not fixed] Header's "TVDSS: 2315.6m" fallback constant** can display simultaneously with the Dashboard body's real "BIT TVDSS: 2313.9m" value for the same well/depth, with no visual distinction between the live-telemetry-driven header figure (currently showing its idle-state fallback, since module 04's physics sim is not running) and the real API-driven body figure. Both numbers are individually correct for what they represent (one is a documented placeholder, one is live data) and this exact fallback pattern was already disclosed as intentional in a prior pass — not a new bug, but confirmed here as a potentially-confusing adjacency worth a future look.
9. **Not a bug, but confirmed and recorded as a genuinely honest behavior**: `PdfEvidenceViewer`'s "Source document not found in module 01's archive" message for a historical-testbed event with no real ingested PDF behind it. This is the UI correctly and honestly declining to fabricate evidence it doesn't have — exactly the discipline the rest of this project already practices.

---

## Problems fixed

### 1. Dashboard hazard-forecast panel — stale "module 03 not wired" text
**Files:** `frontend/src/pages/DashboardPage.tsx`
**Change:** Replaced three instances of stale "module 03 — not yet wired" text with accurate descriptions ("module 04/05, :8003") and an honest explanation that the panel is empty because the physics simulator isn't running yet (not because the backend doesn't exist).
**Verified:** Reloaded `/app`, screenshot confirms "Physics Digital Twin (module 04/05, :8003)... Connected" and "Predictive ML fusion (module 04/05, :8003)... Idle — simulator not running".

### 2. SystemStatusPage's third card — real health check
**Files:** `frontend/src/pages/SystemStatusPage.tsx`
**Change:** Replaced the static amber "NOT CONNECTED" block with a real check using `api.getSimStatus()` (liveness) and `api.getRegisteredModels()` (honest fitted/unfitted ML status), matching the pattern of the other two real cards.
**Verified:** Reloaded `/app/status`, screenshot confirms "MODULE 04/05 — PHYSICS DIGITAL TWIN / PREDICTIVE ML (:8003) — HEALTHY" with real engine state and the real 3-model list (`baseline_hazard_rules` ACTIVE, `isolation_forest_anomaly`/`xgboost_hazard_classifier` UNFITTED_FALLBACK, each correctly colored).

### 3. api.ts stale module-03 comment block
**Files:** `frontend/src/services/api.ts`
**Change:** Replaced a second, more detailed stale comment block (the file's header comment had already been fixed in a prior pass, but this second block was missed) describing module 03 as having "NO FastAPI routes" with an accurate description of the real module 04/05 relationship.
**Verified:** Code-only change (comment), no runtime behavior affected; confirmed no other stale "module 03 not wired" text remains via repo-wide grep.

### 4. Offset Map's 14-way request fan-out
**Files:** `frontend/src/components/nwis-map/useNwisMapData.ts`
**Root cause:** One `GET /api/v2/events/{well_id}` call per well (14 calls) via `Promise.all`, instead of the existing batched `GET /api/v2/events` endpoint (confirmed to return all 44 real events, each carrying its own `well_id`, well within the endpoint's 100-item cap).
**Change:** Replaced the 14-way fan-out with a single `api.searchEventsStructured()` call, grouping events by `well_id` client-side.
**Data/API contract affected:** None — same final shape (`eventsByWell: Record<string, WellEvent[]>`) delivered to the vendored `WellDetailPanel`/`NearbyWellsMap` components, which were not modified.
**Verified:** Reloaded `/app/offset-map`; network tab showed exactly 2 module-02 requests (4 under React StrictMode's dev-only double-invocation) instead of 15 (30) previously. Cross-checked data correctness: `15/9-F-1`'s incident count (3) matched exactly against a direct `GET /api/v2/events/15%2F9-F-1` call; the map's per-well incident-count badges (2,2,2,2,4,5,4,3,2,4,6,3,?,3) and hazard-type facet counts (Wellbore instability: 1, Stuck pipe: 2) were unchanged from before the fix.

### 5. Broken CARTO "Dark Vector" basemap
**Files:** `frontend/src/components/BasinMap.tsx`
**Root cause:** CARTO retired free/keyless access to `basemaps.cartocdn.com`'s image basemaps (confirmed via web search of CARTO's own current documentation/community reports, not assumed).
**Change:** Swapped to Esri's `World_Dark_Gray_Base` (same free/keyless provider family already used for this file's own "Satellite" style), confirmed reachable via a direct tile request (`HTTP 200`) before switching.
**Verified:** Live-tested on both `/app/wells`'s own map and the `WellInspector3DModal`'s embedded map (both consume `BasinMap.tsx`) — the "API KEY REQUIRED" watermark is gone, real map tiles render, correct Esri attribution shown.

### 6. 3D globe marker/texture rotation desync
**Files:** `frontend/src/components/globe/OffsetGlobe3D.tsx`, `frontend/src/components/globe/EarthGlobe.tsx`
**Root cause:** `EarthGlobe` owned an independent auto-rotating `<group>`; `WellMarkers` was a Canvas-level sibling, not a child of that group, so marker world-positions and the rotating texture desynced over time.
**Change:** Introduced a single `RotatingGroup` component in `OffsetGlobe3D.tsx` wrapping both `EarthGlobe` and `WellMarkers`; removed `EarthGlobe`'s own internal rotation.
**Data/API contract affected:** None — purely a rendering-composition fix, `globeGeometry.ts`'s `latLonToVec3` formula itself was confirmed correct and left unchanged (after being incorrectly "fixed" and then correctly reverted during this investigation — see above).
**Verified:** Isolated three.js test harness (camera pointed deterministically along the formula's computed direction) confirmed the formula's correctness independent of the app. Live app re-test after 15+ seconds of real auto-rotation confirmed `WELL-HGJ-011`'s marker renders correctly over Assam/Myanmar border region, matching its real 27.20°N/94.75°E coordinates.

---

## Rate-limit investigation (task §8)

**Is it a testing artifact or a real problem?** Both, precisely separated:

- **Under the realistic navigation cycle** (Dashboard → Wells → Offset Map → Globe → Nearby Wells → Correlation → Knowledge → Alerts → Dashboard, ~2.5s per page — a deliberately generous but still normal human pace) executed in this pass: **zero 429 errors**, confirmed by an in-page console-error listener across the entire cycle.
- **429s were reproduced** only during deliberately rapid, repeated automated re-navigation to the Offset Map page while isolating the request-fan-out bug (item 4 above) — a genuine artifact of that specific debugging process, not normal usage.
- **The underlying real problem was real, not imagined**: before the fix, a single Offset Map page load cost 15 real requests to module 02 (30 under React StrictMode's dev-only double-invocation) — a quarter to half of the entire 60-request/60-second budget from one page view. A real user clicking through several data-heavy pages in quick succession (Dashboard's 4 requests + Offset Map's then-15 + Nearby Wells' handful more) could plausibly have exhausted the budget within a single minute of normal browsing, even without any automated rapid-fire testing.
- **Fix applied**: the 14-way fan-out is now 1 request (item 4 above), removing the single largest contributor to the budget. No rate-limit threshold itself was changed, per the task's explicit instruction not to raise the limit just to make testing pass.
- **Remaining headroom**: Dashboard alone still issues ~4 requests per mount; Nearby Wells issues a handful more. These were not touched, since they were not found to cause real 429s during the realistic-pace test, and the task said to fix only verified problems. If a future pass finds a genuine issue here, it should be investigated the same way (reproduce at a normal pace first) rather than assumed from counting requests alone.

---

## Problems NOT fixed (remaining, documented honestly)

1. Light-theme contrast issue in `ConfidencePillars.tsx` (and potentially other `bg-slate-900/*`-styled panels not specifically audited this pass) — cosmetic only, confirmed not present in Dark theme, out of this pass's minimal-fix scope.
2. Header's idle-state TVDSS/MD/Formation fallback constants can sit adjacent to real live data for the same metric with no visual distinction — pre-existing, documented pattern, not a new bug, not fixed this pass.
3. No "fly to active well" camera animation on the 3D globe (already documented as a known limitation in `AUDIT/03_3D_INTEGRATION.md`) — makes manually locating a specific well's marker slow, which is exactly what made the rotation-desync bug hard to spot by eye and is worth revisiting alongside any future globe polish work.
4. Module 02's rate limit (60/60s) remains unchanged — adequate under realistic use after the fan-out fix, but Dashboard + Nearby Wells' combined request count across a fast multi-page session was not separately stress-tested to its absolute limit this pass.

None of these block the application's core functionality or misrepresent real data as fake or fake data as real.

---

## Final status

```
PASS WITH KNOWN ISSUES
```

**Justification:** Every route loads cleanly, the full primary user journey completes with zero unexplained errors, 2D/3D well-selection and radius state synchronize correctly and bidirectionally (verified against independently-computed ground truth, not just "it looks right"), a real and non-trivial 3D geographic-placement bug was found, root-caused precisely (including correcting a wrong initial hypothesis rather than leaving it in place), and fixed with an isolated independent test before being trusted in the live app, a real request-efficiency bug was found and fixed with a measured ~87% reduction in request volume for the affected page, and a real broken third-party map dependency (the exact issue flagged by the user from an earlier session) was found and replaced with a verified-working free alternative. No existing working functionality was removed or broken — every pre-existing 3D component, every 2D page, and the untouched landing page were all re-confirmed clean after all fixes. The "WITH KNOWN ISSUES" qualifier reflects the two documented-but-unfixed cosmetic/UX items above, neither of which represents fabricated data, broken core functionality, or a regression.

---

# Summary

### 1. What was tested
A full cold-restart of all five services; every one of 17 routes individually; the complete primary SIH user journey end-to-end as a real user; bidirectional 2D↔3D↔header well-selection synchronization at two independent wells; radius-filtering correctness at two independent wells, cross-checked against independently-computed real-world distances; the 3D globe's geography, camera, interaction, lighting, and resize behavior; all real and procedural 3D assets for 404s/CORS/WebGL errors; a realistic (not artificially rapid) multi-page navigation stress cycle; the rate-limit behavior under both realistic and artificially-rapid conditions; API-response-vs-rendered-UI value matching on several real data points; regression-testing of all four pre-existing Three.js components; and a repo-wide check for accidental architectural duplication (well state, API clients, well datasets, rotation logic).

### 2. What failed
Two stale-text panels claiming a real, running backend module "is not wired"; a 14x request fan-out on the Offset Map page that was the real, reproducible (not imagined) cause of rate-limit pressure; a broken third-party map tile dependency (CARTO) causing a visible "API KEY REQUIRED" watermark on two different pages — the exact issue raised earlier; and a real 3D rendering bug where well markers drifted out of sync with the rotating Earth texture over time, caused by an incomplete scene-graph composition (not, as first suspected and briefly "fixed" incorrectly, a wrong coordinate formula).

### 3. What was fixed
All five items above, each verified by direct re-test after the change: the two stale-text panels now show real, live, auto-refreshing module 04/05 status; the Offset Map now issues 2 requests instead of 15 for the same correct data (cross-checked exactly against ground truth); the map tiles now render correctly everywhere `BasinMap.tsx` is used; and the 3D globe's markers now stay correctly fixed to their real geographic location on the rotating Earth, re-verified after a deliberately long wait to specifically re-trigger the drift condition that exposed the bug.

### 4. What remains
A Light-theme-only cosmetic contrast issue on one Command Center panel; the pre-existing (not new) idle-telemetry fallback-constant adjacency in the header; the already-documented absence of a "fly to active well" 3D camera assist; and no further stress-testing of the rate limit beyond the realistic-pace cycle this pass used. None of these are data-fabrication, core-functionality breaks, or regressions.

### 5. Is the application ready for the final SIH compliance audit?
**Yes.** The application survives a realistic, complete user walkthrough with no unexplained console errors, no broken critical API calls, no broken routes, no broken critical assets, correct and verified well-selection synchronization across all views (2D and 3D), correct and now-verified-fixed geographic marker placement, data rendered from real APIs matching ground truth everywhere it was checked, and no regression of any pre-existing feature. The remaining open items are cosmetic/polish-level and are honestly documented above rather than hidden — nothing found in this pass should block proceeding to the requirement-by-requirement SIH compliance audit.
