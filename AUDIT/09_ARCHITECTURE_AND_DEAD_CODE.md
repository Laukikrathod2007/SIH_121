# Architecture, Dead Code, API Contracts, Database, and Security Audit

**Date:** 2026-10-04

---

## 1. Module 02 vs Module 05 risk architecture — intentional parallel, unresolved reconciliation gap

**Verdict: INDEPENDENT, parallel, frontend-split — not duplicated, not dead, not accidentally disconnected.**

- Grepped both modules for cross-references: module 02 → module 05 = **zero hits**. Module 05 → module 02 = **one hit, a code comment only** (a stylistic precedent reference, not an import/call).
- They run as two separate FastAPI processes (ports 8002/8003), each with its own `.env`/key, confirmed live.
- **Different hazard taxonomies entirely**: module 02 has `MUD_LOSS/STUCK_PIPE/KICK/WELLBORE_INSTABILITY/TORQUE_SPIKE/CEMENTING_FAILURE/OVERPRESSURE_ZONE`; module 05 has `lost_circulation/stuck_pipe/kick/torque_drag/washout/cementing` — **no WELLBORE_INSTABILITY or OVERPRESSURE_ZONE in module 05 at all**.
- **Different score formulas**: module 02's `R_H = 0.45·P_history + 0.35·A_sensor + 0.20·M_ml`; module 05's 4-pillar fusion with its own weights.
- **Frontend consumption is cleanly split, never reconciled**: Command Center consumes module 02's `analyzeWell()` exclusively; `AlertsAdvisoryPage.tsx` consumes module 05's alerts exclusively. **No page shows both side-by-side or cross-validates them.** A user viewing "15/9-F-12" on Command Center sees module 02's STUCK_PIPE score; the same well's module-05-derived alert (if any) uses a structurally different fusion formula and the user has no way to see both numbers together or understand they diverge.

**This is intentional architecture by construction** (two modules, two owners, two numbered API versions, documented independently in code comments) **but an unresolved reconciliation gap in practice** — nothing merges or cross-displays the two engines' views of the same named hazard. Not solved in this audit per the task's explicit "do not redesign it yet" instruction.

---

## 2. Physics/digital-twin engineering audit

### Equations actually implemented (file:function, confirmed from source)
| Subsystem | Physics |
|---|---|
| `mechanics.py:calculate_rop` | Empirical ROP model with soft saturation via `tanh` |
| `mechanics.py:calculate_torque_and_hookload` | Coulomb friction torque/drag, buoyed string weight |
| `mechanics.py:calculate_mse` | Mechanical Specific Energy |
| `mechanics.py:calculate_d_exponent` | **Real Jordan & Shirley d-exponent** (named explicitly in the docstring), pore-pressure-corrected |
| `hydraulics.py:solve_hydraulics` | Hydrostatic pressure, bit nozzle pressure drop, SPP/BHP/ECD, pore/fracture margins. **Correction to a prior assumption**: friction losses use **fixed empirical friction-factor constants** (0.018 pipe, 0.024 annulus), NOT a Reynolds-number-derived Fanning/Moody correlation — this should not be overstated as more sophisticated than it is |
| `mass_balance.py:solve_mass_balance` | Lost-circulation (`Q_loss ∝ (BHP-P_frac)^0.85`), kick influx (productivity-index model), pit-volume ODE |
| `torsional_dynamics.py:step` | Real 2nd-order torsional oscillator with nonlinear Stribeck stick-slip friction, sub-stepped for stability |

### Integration method
Explicit (forward) Euler for the main state, `dt` per `engine.step(dt_s)` call; torsional subsystem additionally sub-steps at 0.02s for stability. `_sim_loop()` ticks at `dt_s/speed_multiplier`, clamped to [0.02, 1.0]s wall-clock.

### Dead second control path — confirmed STILL dead
`grep "PhysicsController\|LiveTelemetryStreamer" modules/04_physics_engine/api/server.py` → **zero matches**. The live server imports and uses only `DrillingPhysicsEngine` directly via its own `_sim_loop()`. `PhysicsController`/`LiveTelemetryStreamer` exist on disk, imported **only** by the test suite (`tests/test_physics_and_pipeline.py`). **Confirmed unchanged from the prior audit — still dead in production, alive only in tests.**

### Live verification: the simulation genuinely advances
Started the simulator via `POST /api/v3/physics/start`, checked `GET /api/v3/physics/status` immediately and again 5 real seconds later:
- Immediately after start: `sim_time_s=18.0, md_m=2500.02`
- After 5s: **`sim_time_s=29.8, md_m=2500.03`** — real wall-clock-driven advancement, confirmed, not a static response.
- `GET /api/v3/physics/historian?limit=3` returned 3 sequential records with strictly increasing timestamps and internally-consistent, varying physics channels (MSE, d-exponent, ECD) — not static placeholders.

### WebSocket trace
`server.py` exposes `/api/v3/physics/stream`, broadcasting the same `TelemetryEnvelope` every tick to all connected clients (`"ws_clients":1` observed live during this audit). Frontend `AppContext.tsx`/`LiveDrillingScene3D.tsx` consume this stream directly.

---

## 3. 3D globe — engineering audit (not just visual)

Traced: well data → coordinate conversion → globe geometry → marker placement → filtering → interaction → `activeWellId` → global state.

- **Coordinate conversion**: `frontend/src/lib/globeGeometry.ts`'s `latLonToVec3()` — real spherical-to-Cartesian math, independently re-derived this session from three.js's own `SphereGeometry` source (not guessed), and verified correct via an isolated test harness (camera pointed deterministically at the formula's own computed direction, confirmed landing on real Assam/northeast-India coastline).
- **A real rendering bug was found and fixed during the prior verification pass** (not re-litigated here, but relevant to this audit's "is the 3D system real" question): well markers had desynced from the rotating Earth texture over time due to an incomplete scene-graph composition (two independent rotation owners). Fixed by unifying rotation under one shared group. Confirmed correct after a 15-second real-time drift re-test.
- **Haversine filtering**: real, and consistent with module 02's own DORS spatial-factor formula and the 2D map's inline copy (duplicated, not shared — see §5 below).
- **Active well / global state**: confirmed single source of truth (`AppContext.tsx`'s one `activeWellId` definition), confirmed bidirectionally synchronized between the globe, the 2D map, and the header dropdown via real browser testing in the prior pass.
- **Arcs**: real great-circle approximation (lerp + normalize + sine bulge) — a reasonable visual approximation, not geometrically exact for very long arcs, honestly not claimed to be more.
- **Asset loading**: real 2:1 equirectangular Earth textures (day/night), confirmed via pixel-sampling against known real-world coordinates before use; no GLB/GLTF files are loaded by the globe (pure procedural sphere geometry).

### Known limitations (confirmed still true, not re-litigated as new findings)
- No "fly to active well" camera animation — manual rotation required to locate a specific well.
- No Scene 2 (Assam terrain) or Scene 3 (underground formations) from the original `visualization_3d/idea.md` concept — only the Scene 1 globe-level view was built.
- No real place-name labels on the globe.
- Great-circle arcs are a lerp-based approximation, not true spherical slerp.

**None of these are treated as "planned functionality" in this audit — they are explicitly unbuilt, and this document records them as such, not as partial credit.**

---

## 4. Radius parameter contract gap (new finding from this audit)

`GET /api/v2/map/wells` declares **zero query parameters** — a passed `radius_km` is silently accepted by the HTTP layer and ignored by the handler. `GET /api/v2/offset_rank/{id}?radius_km=` **does** accept the parameter, but live-confirmed it functions only as a spatial-score decay divisor (`score = max(0, 1-dist/r_max)`), not a hard filter — a well 58km away still appears in the ranked results with a near-zero spatial sub-score rather than being excluded.

**The user-facing feature works correctly** because the frontend re-filters client-side with real Haversine distance (openly documented in code comments as a deliberate compensation). But the raw backend API contract does not implement "radius" the way its name and the PS wording imply. This matters if the API is ever consumed directly (e.g., a future real eRTMAC integration) rather than only through this specific frontend.

---

## 5. API and data-contract audit

### Unused frontend API functions (defined in `api.ts`, never called from any page/component)
Confirmed via exhaustive grep: `listJobs`, `getExtractionBenchmark`, `getReviewQueue`, `getReviewDetail`, `annotateField`, `getTemplates`, `getWell`, `setOperatorInputs`. Each is backed by a real, working backend route — these are **dead frontend wiring**, not broken backends. Notably, `getReviewQueue`/`getReviewDetail` mean the backend has a full human-review-queue API that the frontend never surfaces as a queue view (only one-off approve/reject on whatever document is currently open via `submitReviewDecision`, which IS used).

### Duplicated implementation
`haversineKm` exists in two places — `frontend/src/lib/globeGeometry.ts` (canonical, with a comment claiming it's "kept consistent") and a separate inline copy in `frontend/src/pages/NearbyWellsPage.tsx`. Mathematically identical, but not actually shared. Unintentional duplication, not a correctness bug (both are correct), flagged for future consolidation — not fixed this pass.

### Stale comments (already corrected in prior passes, re-confirmed not regressed)
Module 03-is-not-wired language was fully removed from `api.ts`, `DashboardPage.tsx`, and `SystemStatusPage.tsx` in the prior core-integration pass — re-confirmed absent in this audit.

---

## 6. Dependency and dead-code audit

| Item | Classification |
|---|---|
| `recharts` (npm) | **DEAD IN PRODUCTION** — declared in `package.json`, zero imports anywhere in `frontend/src` |
| All other npm dependencies (`@react-three/*`, `axios`, `leaflet`/`react-leaflet`, `lucide-react`, `pdfjs-dist`, `react-router-dom`, `three`) | **ACTUALLY USED** — confirmed by import-count grep |
| `PhysicsController`/`LiveTelemetryStreamer` (module 04) | **DEAD IN PRODUCTION / USED IN TESTS** — see §2 |
| `nwis-map-package/` | **INTENTIONALLY VENDORED (superseded)** — zero live imports from it; its components were copy-pasted into `frontend/src/components/nwis-map/`, confirmed by grep (only comment-string hits documenting provenance, no actual import statements) |
| `real_data/real_trained_models/*.joblib` | **UNCERTAIN → resolved to ORPHANED** — see `06_ML_AND_MODEL_AUDIT.md` |
| `database/` | **BUILT + SEEDED (once) but NOT RUNTIME-CONNECTED** — see `08_REAL_VS_SIMULATED.md` |

---

## 7. Database audit

| Aspect | Finding |
|---|---|
| Schema | Real, hand-written 3-tier PPDM/WITSML/OSDU-aligned DDL (`database/schema.sql`), confirmed substantial (~30KB) |
| Extensions | PostGIS, pgvector, TimescaleDB — confirmed in `docker-compose.yml`/`Dockerfile` |
| Seed/migration | `migrate_seed.py` is a real, working one-way loader — confirmed run at least once historically (dated README claim: "2026-09-28... all 12 wells / 1245 trajectory stations / 97 formation tops / 39 events / 3600 telemetry records loaded" — this is the **synthetic** testbed only, not the real Volve additions) |
| **Runtime connection** | **CONFIRMED NOT CONNECTED** — exhaustive repo-wide grep for `psycopg`/`sqlalchemy`/`asyncpg` outside `database/` itself returns zero matches. **The Docker container is not even running on this machine at the time of this audit** (`docker ps` fails to reach the daemon). |

**Precise distinction, as the task demanded**: BUILT = yes. SEEDED = yes, once, historically. RUNTIME-CONNECTED = **no**, with certainty. This is not "the application's production database" — it is a verified-working, disconnected standalone layer.

---

## 8. Security/configuration audit (no secret values printed)

| Found | Location | Type | Tracked by git? | Used at runtime? | Action required |
|---|---|---|---|---|---|
| Y | `modules/01_document_intelligence/.env` | `NWIS_API_KEY` | N (gitignored, confirmed) | Y (`auth.py`) | None |
| Y | `modules/01_document_intelligence/.env` | `NWIS_REDUCTO_API_KEY` | N | Y, and **currently active** (cloud fallback is armed on this checkout) | Confirm this is intended — documents can leave the air-gapped boundary when confidence is below 0.75 |
| Y | `modules/01_document_intelligence/.env` | `NWIS_EXTEND_API_KEY` | N | Y, same as above | Same |
| Y | `modules/02_nwis_backend/.env` | `NWIS_API_KEY` | N | Y | None |
| Y | `modules/04_physics_engine/.env` | `NWIS_API_KEY` | N | Y | None |
| Y | `frontend/.env` | `VITE_M01/M02/M03_API_KEY` | N | Y (bundled into client JS at build time — standard SPA exposure, not a bug, but worth knowing) | None |

**Auth**: enabled on all three backends currently (non-empty keys present). **CORS**: locked to explicit localhost origins + env-extensible list on all three, no wildcard found — module 02's own comment notes this replaced a prior wide-open `"*"` policy. **Module 04 sets `allow_credentials=True`** while modules 01/02 do not — an inconsistency worth a deliberate review. **Rate limiting**: enabled by default on all three (20/60/600 req per 60s respectively). **Debug flags**: `reload=True` is correctly gated behind a non-production environment check in all three modules — not a finding.

No credential was rotated, printed, or invalidated during this audit, per instruction.
