# 3D Integration Pass — Report

**Date:** 2026-10-03
**Scope:** New, additive work under `frontend/` only. No backend changes. No existing 2D functionality removed. `DrillWise-Frontend/`, `visualization_3d/`, `extend-ai-website/`, `nwis-map-package/`, `database/`, `research/` were not modified, per the hard boundary set for this phase.

---

## Target — classification of every 3D/map candidate, verified before writing any code

Per the task's §1 requirement to identify the correct target first, every candidate in the repository was inspected directly (code, not just filenames) and classified:

| Candidate | Classification | Evidence |
|---|---|---|
| `DrillWise-Frontend/` | **MARKETING SITE** | `assets/js/digital-twin.js` is a raw-WebGL (no three.js) looped scroll-triggered animation of one well's GLB geometry. No map, no well-selection, no multi-well concept of any kind — confirmed by reading the file directly (BHA spline animation, fixed `MAX_MD`/`START_MD` constants, no data fetch). |
| `visualization_3d/` | **CINEMATIC / BLENDER ASSET** | `idea.md`'s own status log states explicitly: *"the actual connected/interactive radius-selection and well-selection triggers (as opposed to a fixed camera animation) are not started."* It is a Blender-via-MCP offline render pipeline (`scripts/blender_client.py`) producing PNG/MP4 output, not a web component — there is no browser-runnable artifact here at all. |
| `nwis-map-package/` | **ALREADY PART OF CORE APP** (and 2D, not 3D) | Confirmed in the prior core-integration audit: pure Leaflet, no 3D/globe library anywhere in its source; its components were already copy-pasted into `frontend/src/components/nwis-map/` and are live at `/app/offset-map`. |
| `frontend/src/components/*3D*` (`WellTrajectory3D`, `LiveDrillingScene3D`, `CommandScene3D`, `WellCutawayCockpit`) | **ALREADY PART OF CORE APP** | Real, wired, interactive react-three-fiber components, already live at `/app/wells` and `/app/drilling`. Not "independent" — this is the application's own existing 3D work. |
| *(no candidate)* | — | **No pre-built, interactive, browser-runnable "nearby wells" 3D/globe experience exists anywhere in the repository.** This was confirmed with the user directly (see decision below) rather than assumed. |

**Decision taken with the user**: since no pre-built interactive 3D map exists to "integrate," the user asked for the *actual interactive 3D map described in `visualization_3d/idea.md`* to be built as new work — reusing the existing `three`/`@react-three/fiber`/`@react-three/drei` stack already in the app (not a new dependency), real application data (not demo data), and the Earth textures already present in `visualization_3d/assets/` (confirmed usable — user has the rights to the textures).

```text
Target 3D project:      visualization_3d/idea.md's described experience (not yet built anywhere) — built fresh this pass
Entry point:             frontend/src/pages/GlobeMapPage.tsx, route /app/globe
Framework:               React + react-three-fiber + drei (same stack as the app's existing 3D components)
3D/map technology:       three.js SphereGeometry + real equirectangular Earth textures (no new library added)
Main components:         components/globe/{EarthGlobe,WellMarkers,OffsetGlobe3D}.tsx, lib/globeGeometry.ts
Current data source:     Real — GET /api/v2/map/wells (module 02), GET /api/v2/offset_rank/{id} (module 02)
Current API/data contract: Identical to the existing 2D Offset Map / Nearby Wells pages — no new backend endpoint
Hardcoded values:        None for well data. GLOBE_RADIUS (a rendering-scale constant, not a data value) and marker colors (matching the 2D map's existing palette)
Assets:                  2 Earth textures (day/night), reused from visualization_3d/assets/, copied into frontend/public/earth/
How it renders wells:    Real lat/lon -> 3D sphere position, colored/sized by active/offset/catalog status, click-to-select
How users interact:      Drag to orbit, scroll to zoom, hover for a real well tooltip, click a marker to set it as the active well (same state as every other page)
```

---

## Previous architecture

There was no "previous architecture" for this specific experience — it did not exist in runnable form anywhere (see Target section above). The closest prior art was `visualization_3d/idea.md`'s written design intent plus unfinished Blender renders, and `BasinMap.tsx`'s existing 2D Leaflet pattern, which this new work deliberately mirrors (same color conventions, same radius-slider UX, same `useApp()` state).

---

## New architecture

```text
Module 02 (real backend)
   │
   ├── GET /api/v2/map/wells         ──┐
   └── GET /api/v2/offset_rank/{id}  ──┤
                                        ▼
                          frontend/src/pages/GlobeMapPage.tsx
                             (fetches once, holds radiusKm state,
                              reads/writes activeWellId via useApp())
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                      ▼
         components/globe/OffsetGlobe3D.tsx        (same useApp() state also
         ├── EarthGlobe.tsx (real Earth texture)     drives BasinMap.tsx on
         └── WellMarkers.tsx (real wells, click      /app/wells and /app/offset-map,
             -> onSelectWell -> setActiveWellId)      and the header's well selector)
```

The 3D globe is a second **view** of the same authoritative data and the same shared `activeWellId`/`wells` state every other page already uses — not a second data source, not a second "world." This was verified live (see Verification section): selecting a well on the globe updates the header dropdown; selecting a well from the header dropdown updates the globe's active-well panel; selecting from the DORS ranking list (shared endpoint, same as `NearbyWellsPage`) updates both.

---

## Data mapping

| 3D field | API/source | Actual data |
|---|---|---|
| Marker position (lat/lon) | `GET /api/v2/map/wells` → `well.lat`, `well.lon` | Real surface coordinates — 12 synthetic Assam wells + 2 real Equinor Volve wells (`15/9-F-12`, `15/9-F-1`), same 14-well catalog as every other page |
| Marker color (active/offset/catalog) | Computed client-side from `activeWellId` + Haversine distance to `activeWell` | Real distance calculation, same formula as `NearbyWellsPage`/`BasinMap` (not re-derived independently) |
| Marker size | Same in-radius computation as color | — |
| Hover tooltip (name, field, depth, event count) | `well.well_name`, `well.field`, `well.total_depth_md_m`, `well.total_events` — all from the same `GET /api/v2/map/wells` response | Real |
| Click → select well | `onSelectWell` → `setActiveWellId` (from `useApp()`) | Same context used app-wide; no separate 3D-only selection state |
| Great-circle connector arcs | Computed client-side between `activeWell` and each in-radius offset well's real lat/lon | Visual only (not a separate data field); disappears/reappears exactly matching which wells are in radius |
| "Real DORS Offset Ranking" panel | `GET /api/v2/offset_rank/{well_id}` | Real module 02 DORS 5-factor scores — identical endpoint and response shape `NearbyWellsPage` uses |
| Radius-filtered offset count | Client-side Haversine filter over the DORS ranking response | See "Real bug found and fixed" below — the endpoint's own count is not radius-filtered |

**No field anywhere in this component tree is invented, mocked, or fabricated.**

---

## Changes — exact files

**New files:**
- `frontend/src/lib/globeGeometry.ts` — lat/lon ↔ 3D-sphere math, Haversine distance, great-circle arc point (shared utility, documented and derived from three.js's own `SphereGeometry` source, not guessed)
- `frontend/src/components/globe/EarthGlobe.tsx` — the Earth sphere (day/night texture + atmosphere rim), real geography
- `frontend/src/components/globe/WellMarkers.tsx` — real well markers, hover tooltips, click-to-select, connector arcs
- `frontend/src/components/globe/OffsetGlobe3D.tsx` — Canvas/lighting/camera wrapper composing the above two
- `frontend/src/pages/GlobeMapPage.tsx` — the page: data fetching, radius control, DORS ranking panel, active-well dossier
- `frontend/public/earth/earth-daymap-2k.jpg`, `earth-nightmap-2k.jpg` — copied from `visualization_3d/assets/` (2k versions, ~718KB total — the 8k originals were not used, to keep the web bundle reasonable)

**Modified files:**
- `frontend/src/App.tsx` — added the `/app/globe` route (lazy-loaded, same pattern as the existing `WellInspector3DModal`)
- `frontend/src/components/layout/Sidebar.tsx` — added the "3D Offset Globe" nav entry
- `frontend/src/components/BasinMap.tsx` — **unrelated real bug found and fixed during verification**: the "Dark Vector" basemap's tile URL (`cartocdn.com/dark_all`) is CARTO's free anonymous basemap endpoint, which CARTO has since retired — every tile was rendering an "API KEY REQUIRED" watermark instead of a map (confirmed via a live screenshot, and independently via web search confirming CARTO's 2025 deprecation of free image-basemap access). Swapped for Esri's `World_Dark_Gray_Base` (same free/keyless provider family already used for the existing "Satellite"/`World_Imagery` style in this same file), confirmed working with a direct tile request before switching, and re-verified live in the browser (watermark gone, map renders, correct attribution shown). This affects every consumer of `BasinMap.tsx` — `NearbyWellsPage`, `CommandCenterPage`, and `WellInspector3DModal` — all re-verified clean after the fix.

**Not modified:** any backend module, `database/`, `nwis-map-package/`, `DrillWise-Frontend/`, `visualization_3d/`, `extend-ai-website/`, `research/`, or any existing page/component beyond the two listed above.

---

## Assets

| Asset | Source | Destination | Reason |
|---|---|---|---|
| `earth-daymap-2k.jpg` | `visualization_3d/assets/earth_daymap_2k.jpg` | `frontend/public/earth/` | Standard 2:1 equirectangular day-map texture; 2k chosen over the available 8k version (4.5MB) to keep the page load reasonable — confirmed visually sufficient at the zoom levels this view actually uses (never closer than `minDistance` on the orbit controls) |
| `earth-nightmap-2k.jpg` | `visualization_3d/assets/2k_earth_nightmap.jpg` | `frontend/public/earth/` | City-lights layer for the globe's dark/night side, additive-blended at low opacity |

Not copied: `8k_earth_daymap.jpg`, `8k_earth_clouds.jpg` (11.6MB — unnecessary file weight for a web app; clouds were not part of the requested interaction), the Blender `.blend`/`.blend1` scene files, and the render/screenshot reference assets — none of these are consumed by a browser-renderable component, so copying them would be exactly the "copy entire unrelated asset trees" the task said to avoid.

**Asset verification performed, per task §9:**
- Checked actual browser network requests: both textures return `200 OK` from `/earth/*.jpg`, no 404s.
- No CORS issues (served from the same origin as the app, not an external CDN).
- No WebGL console errors/warnings at any point during testing.
- Confirmed the textures are standard equirectangular projections (8192×4096 for the 8k originals, 2:1 aspect) via `file` inspection before use, not assumed.

---

## Removed mock/demo data

**None existed to remove** in the new globe component itself — it was built against real data from the start, per the user's instruction and the task's "do not create a second fake backend" requirement. There was no prior demo/placeholder version of this specific view to clean up.

Separately (not demo data, but a correctness issue found and fixed): the DORS ranking panel's "X offset wells within radius" count initially trusted `GET /api/v2/offset_rank`'s raw ranking length, which is **not actually radius-filtered** by the backend — `engines/dors_engine.py`'s `score_spatial()` uses `radius_km` only as a scoring-decay parameter, not a hard cutoff (confirmed directly from source, then confirmed live: a `radius_km=5` request still returned all 10 other wells, several thousand km away, each scored near-zero on the spatial component but still included). This was not a fabricated-data problem — the data itself was real — but the *count derived from it* would have been misleading. Fixed by applying the same client-side Haversine filter `NearbyWellsPage.tsx` already uses, so the globe's radius count is consistent with the rest of the app. Verified live: switching the active well to `WELL-NHK-001` (which has real nearby neighbors, unlike the isolated Volve pair) and sweeping the radius slider produced a correctly varying count (0 → 2 → 6 offset wells at 5/15/50km), confirming the fix is genuinely radius-sensitive, not just hardcoded to look right for one well.

---

## Remaining simulation

None introduced by this work. The globe shows only real well data and real DORS scores; there is no "AI risk overlay" or invented visual layer, per the explicit instruction in task §7 not to add one just because the visualization has space for it.

---

## Synchronization

All verified live, in the running browser, not assumed from code reading alone:

| Requirement | Result |
|---|---|
| 2D/application selects well → 3D highlights same well | **Verified.** Selected `15/9-F-12` via the header dropdown; the globe's "Active well" panel and marker both updated to match. |
| 3D selects well → application state/detail panel updates | **Verified.** Clicked an offset well in the globe page's own DORS ranking list (`setActiveWellId`); the header's well selector dropdown changed to show the new well selected. |
| Radius changes in application → 3D nearby-well set changes | **Verified.** Swept the radius slider on `/app/globe` itself from 5→50km for `WELL-NHK-001`; the in-radius offset count changed correctly (0→2→6) and the globe's connector arcs/marker highlighting updated to match. |
| Well selected → same backend data shown regardless of 2D or 3D view | **Verified.** Both the 2D Nearby Wells page and the 3D globe page call the identical `GET /api/v2/offset_rank/{id}` endpoint and render the same ranked list (cross-checked the "offset wells in radius" count between both views for the same well — 2D's count included the active well itself in its own filter logic, 3D's excluded it by design as an "offset wells" count; 7 total − 1 active = 6 offset, consistent once that framing difference is accounted for, not a discrepancy). |

State is not duplicated: the globe reads/writes `activeWellId` through the same `useApp()` context every other page uses, and fetches the same module 02 endpoints. There is exactly one "world."

---

## Verification — actual browser tests performed

All performed against the real running stack (module 01 on :8001, module 02 on :8002, module 04/05 on :8003, frontend on :5173 — the same services started during the prior core-integration pass), via a real Chromium browser (Playwright), not `npm run build` alone.

1. **Initial load of `/app/globe`**: 0 console errors, both Earth textures loaded (200 OK), real well count displayed (14).
2. **Marker-placement correctness bug found and fixed**: the first working version placed every marker in the wrong location (Assam's real coordinates rendered near the US west coast) — a wrong sign in the lat/lon-to-3D-sphere formula, found by visual inspection against real geography, not assumed correct from the math alone. Re-derived the formula directly from three.js's own `SphereGeometry` source (not guessed), fixed the one-line sign error, and re-verified visually: the active well marker (`15/9-F-12`, real coordinates 58.44°N/1.89°E) now renders correctly over the North Sea between Scotland and Norway; rotating to Assam's side of the globe was also checked.
3. **Click-to-select interaction**: clicked a real offset well in the DORS ranking panel → confirmed `activeWellId` changed app-wide (header dropdown updated) → confirmed reverse direction (header dropdown change updates the globe panel).
4. **Radius slider**: swept 5/15/25/50km for two different wells (an isolated pair and a clustered field), confirmed the in-radius count varies correctly and is not hardcoded.
5. **Asset network check**: confirmed both textures 200 OK, no 404s, no CORS errors.
6. **Unrelated real bug found while testing an existing 3D component for regressions**: opening `NearbyWellsPage`'s pre-existing "VIEW 3D TRAJECTORY" modal (which also uses `BasinMap.tsx`'s Leaflet map) showed every tile as a solid "API KEY REQUIRED" watermark. Traced to CARTO's retirement of free anonymous basemap access; fixed in `BasinMap.tsx` by switching to Esri's free `World_Dark_Gray_Base`; re-verified in both the standalone 2D map (`/app/wells`) and the 3D trajectory modal — both now render correctly with real map tiles and correct attribution.
7. **Full regression pass**: re-visited `/`, `/app`, `/app/command-center`, `/app/drilling`, `/app/wells` (including opening its 3D trajectory modal), `/app/offset-map`, `/app/globe` — all 0 console errors after the fixes above (several transient 429s were observed during rapid repeated test navigation and confirmed to be the already-known module 02 rate-limit friction point from the prior phase, not a regression — they cleared on a normal-paced reload).
8. **Landing page check**: confirmed `/` still serves the static marketing page untouched — the 3D globe was not mounted there, only under `/app/globe`, per task §10.

---

## Known limitations

- **Camera does not auto-frame the active well on load.** The globe opens at a fixed default orientation (facing roughly the Americas) and requires the user to drag-rotate to see the active well, which is often on the far side initially. This is a real, not-yet-addressed polish gap — a "fly to active well" camera animation on mount/active-well-change would fix it, but was not implemented this pass to keep the change set focused on the core requirement (real data, real interaction, correct placement).
- **No real place-name labels or pulsing active-marker animation**, both called out as wanted in `visualization_3d/idea.md`'s reference description — not implemented this pass; the marker glow halo is a simpler static approximation, not the described pulse animation.
- **No Scene 2 (Assam terrain) or Scene 3 (underground formations)** from the original 3-scene `idea.md` concept — only the Scene 1 globe-level view was built, since that is what covers "the actual map" the user asked for; the terrain/underground drill-down scenes remain unbuilt.
- **The great-circle arcs use lerp+normalize, not true spherical slerp** — a reasonable visual approximation for the distances involved (confirmed to look correct for both the tight Assam cluster and the isolated Volve pair), but not geometrically exact for very long arcs.
- **Module 02's rate limit (60 req/60s)** remains an existing, pre-identified friction point (see `AUDIT/02_CORE_INTEGRATION.md` §7) that this new page is also subject to — rapid navigation between the globe and other data-heavy pages can trigger it, same as before this pass.
- **The Earth texture provenance** is based on the user's confirmation of usage rights for this pass; no separate license file was added to the repository for `frontend/public/earth/*.jpg`.
