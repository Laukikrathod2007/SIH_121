# NWIS BACKEND REVERSE-ENGINEERING REPORT
# (Audit for the planned standalone 2D/3D Offset Well Intelligence Visualization module)

> **ADDENDUM (2026-10-01, same day, after a branch merge)** — This audit ran
> against the `backend-working` branch in isolation. The repo has since been
> merged into a new `fully-working` branch (`laukik` + `backend-working`,
> zero commits missing either direction — confirmed via `git log A..B` both
> ways). That merge changes several findings below materially, and the merge
> itself introduced one real regression that was found and fixed the same
> day:
>
> 1. **Regression found: the backend could not start at all.** The merge
>    left `engines/risk_corridor_engine.py`'s `HazardRiskAssessment(...)`
>    call with `m_ml_source=m_ml_source` passed twice (a hard Python
>    `SyntaxError`, not a logic bug — the whole module failed to import).
>    Fixed by removing the duplicate keyword argument. Every `.py` file in
>    both Module 01 and Module 02 was then compile-checked
>    (`py_compile.compile(..., doraise=True)`) to confirm no other merge
>    artifacts of this kind exist — none found.
>
> 2. **§9/§17/§18/§21's "casing data does not exist" finding is now WRONG**
>    for this merged branch. The `laukik` branch's real-data work (logger
>    Steps 20-23) brought in `data_store.py` loading real casing records
>    from `real_data/real_casing_records_all.json` — confirmed live at
>    startup: `10 real casing records (2 real wells)`. The data was loading
>    into memory correctly, but, consistent with this audit's own prior
>    finding about `/api/v2/trajectory` once being internal-only, **nothing
>    exposed it via the API**. Added `GET /api/v2/casing/{well_id}` and
>    `GET /api/v2/casing` (mirroring the existing formations-endpoint
>    pattern exactly) — both now RUNTIME VERIFIED working.
>
> 3. **A second, more serious regression/pre-existing bug was found while
>    verifying the casing fix: every single-well endpoint in this API was
>    unreachable for both real wells.** Well IDs `15/9-F-12` and `15/9-F-1`
>    contain a literal `/`. FastAPI's default `{well_id}` path-parameter
>    type does not match a slash even when URL-encoded as `%2F` (Starlette
>    decodes it before routing) — so `GET /api/v2/wells/15%2F9-F-12` and
>    every other `{well_id}`-shaped route 404'd for real wells. This was
>    confirmed against routes that pre-date this audit entirely
>    (`/wells/{id}`, `/formations/{id}`) — it is not something introduced
>    by the merge or by the casing fix, it is a latent bug that nothing had
>    exercised through the live API before (the PS compliance audit
>    separately noted real-well verification had only ever been done via
>    standalone scripts, never the live app — this is very likely why).
>    **Fixed for all 12 affected routes** (`wells`, `trajectory`,
>    `formations`, `casing`, `events`, `telemetry`,
>    `stratigraphic_depth_track`, `offset_rank`, `analyze`, `corridors`,
>    `ahead_of_bit`, `live/replay`) by changing the path parameter type from
>    `{well_id}` to `{well_id:path}`. RUNTIME VERIFIED: `wells`, `casing`,
>    `trajectory`, and `analyze` all now return real 200 responses for
>    `15/9-F-12`, including a full `analyze()` run that correctly offset-
>    ranks it against the other real well, `15/9-F-1`. The
>    `/events/search`-before-`/events/{well_id:path}` registration-order
>    protection documented in §14/§16 still holds — re-verified live,
>    `/events/search` still resolves to the search handler, not a
>    well-lookup with `well_id="search"`.
>
> 4. **Wells/events/formation-top counts in this merged branch are now
>    higher than §3/§6/§7 state**: `/api/v2/health` now reports **14 wells,
>    106 formation tops, 44 events** (vs. the audited branch's 12/97/39) —
>    the 2 additional wells are the real Volve wells above; the extra
>    tops/events are their real, extracted data (deduped against
>    repeats — see `data_store.py`'s own startup log line: "Deduped 5 real
>    events repeated across source documents"). The per-well tables in §3,
>    §7, §19 below reflect the pre-merge 12-well state and should be read
>    as "the synthetic baseline," not the full current picture.
>
> Everything else in this report — the DORS formula, the radius-doesn't-
> filter behavior, the no-shared-coordinate-frame finding, the telemetry
> scope, the `events/search` cold-start latency bug — was not re-verified
> after the merge but has no reason to have changed (none of that code was
> touched by either the merge or these fixes).

Scope audited: `C:\Users\LAUKIK\Desktop\SIH121\modules\02_nwis_backend` (Module 02 only). Module 01 (`modules/01_document_intelligence`, port 8001) and Modules 04/05 were only touched where needed to confirm Module 02 has zero runtime dependency on them. Both source code and live runtime were inspected. Every claim below is tagged with how it was established.

---

## 1. Executive Summary

Module 02 is a self-contained FastAPI service that computes drilling-intelligence analytics (offset-well ranking, stratigraphic correlation, risk corridors, confidence scoring) **entirely from one synthetically-generated, in-memory dataset** (`data/synthetic/*.json`, produced by `data/synthetic/generate_testbed.py` with a fixed `random.seed(42)`). There is no real Oil India / OIL India Limited well data anywhere in this module. Field names, approximate field-center coordinates, and the stratigraphic column (Assam-Arakan formations) are drawn from real regional geology/nomenclature, but every well, trajectory, formation top, drilling event, and telemetry record is procedurally generated — **DEMO / SYNTHETIC**, not real wells.

Separately, elsewhere in the repository (`C:\Users\LAUKIK\Desktop\SIH121\real_data\`), there **is** a set of genuinely real WITSML directional-survey files and parsed JSON for the public Equinor/Statoil **Volve field** (North Sea wells `15/9-F-1`, `15/9-F-12`, etc.). This real dataset is schema-compatible with Module 02's `WellTrajectory`/`SurveyStation` model and is used by **standalone validation scripts** (`real_data/validate_m2_m4_trajectory.py`) to sanity-check Module 02's math — but it is **NOT loaded by `data_store.py` and NOT reachable through any Module 02 API route**. This is the single most important fact for the visualization module about to be built: real trajectory data compatible with this backend's schema exists in the repo, but is currently disconnected from the live API.

Runtime verification also surfaced an important discrepancy: **two stale server processes were already running** (ports 8002 and 8012) serving code that does **not** match what's currently on disk in `server.py` (one was missing the `/api/v2/trajectory` endpoint; the other — port 8012, the port the top-level `README.md` documents as canonical — was serving 14 wells and a `/api/v2/casing` endpoint that do not exist anywhere in the current source tree). The audit agent could not stop those pre-existing processes (blocked by sandbox policy), so it started a **fresh, disposable instance on port 8099** to get ground-truth runtime behavior that actually matches the current source.

---

## 2. Backend Architecture

| Item | Value | Source |
|---|---|---|
| Framework | FastAPI 2.0.0 (app title "NWIS Backend Intelligence API") | `server.py:77-89` — RUNTIME VERIFIED (installed FastAPI 0.115.0, uvicorn 0.30.6) |
| Language | Python 3.11 | `python --version` → 3.11.0, RUNTIME VERIFIED |
| Entrypoint | `run_server.py` (imports `server:app`) | `run_server.py:184-193` |
| Server command (as coded) | `python run_server.py` → `uvicorn.run("server:app", ...)`. Flags: `--gen` (regenerate synthetic data), `--train-ml` (train hazard models), `--validate` (smoke-test pipeline) | `run_server.py:21-110` |
| Server command (as documented at repo root, NOT matching code defaults) | `cd modules/02_nwis_backend && NWIS_PORT=8012 python run_server.py` — top-level `README.md:58` says this was "moved from 8002 — orphaned-socket issue on this machine" | `README.md:43,58` — **NOT VERIFIED as a design requirement**, just a documented workaround |
| Default port (code) | **8002** (`NWIS_PORT` env var, default `"8002"`) | `run_server.py:170` |
| Host | `0.0.0.0` default (`NWIS_HOST`) | `run_server.py:169` |
| API versioning | All routes under `/api/v2/...`; no `/api/v1` exists; `/docs` via FastAPI's own OpenAPI | `server.py` route decorators |
| Dev vs prod | `NWIS_ENV=production` disables `reload=True`; default is dev w/ autoreload | `run_server.py:163-193` |
| Major modules | `server.py` (routes), `data_store.py` (singleton in-memory store), `orchestrator.py` (pipeline), `engines/` (dors_engine, stratigraphic_correlator, risk_corridor_engine, trajectory_engine), `ml/` (feature_engineering, hazard_predictor, train_hazard_models), `live/replay_engine.py` (SSE replay), `search/knowledge_search.py` (semantic/keyword search), `models/schemas.py` (Pydantic models), `auth.py` | File tree, SOURCE-CODE VERIFIED |
| Database technology | **None.** No SQL/NoSQL database is used by this module. All data lives in flat JSON files loaded once into Python objects in RAM by a singleton (`NWISDataStore.__new__` pattern). | `data_store.py:28-39` |
| "Database" location | `data/synthetic/{wells,trajectories,formation_tops,drilling_events,telemetry_stream}.json` | `data_store.py:41-51` |
| ORM | None — raw `json.load` + Pydantic model construction | `data_store.py` |
| Migrations | None applicable (no DB) | — |
| Seed / data-generation script | `data/synthetic/generate_testbed.py` (`generate_all()`), invoked via `run_server.py --gen` or automatically on first run if `wells.json` is missing | `run_server.py:21-27,153-159` |
| Data import scripts | None — no importer for real OIL India/WITSML/CSV data exists in this module | Confirmed by `find`/`grep`, no such script present |
| Background workers/jobs | None persistent. The only background-like behavior is the SSE live-replay generator (`live/replay_engine.py`), which runs only while a client is connected to `GET /api/v2/live/replay/{well_id}` | `live/replay_engine.py` |
| External services | **None.** No outbound HTTP calls, no cloud APIs, no other module's API is called. Confirmed via `grep` for `requests`/`httpx`/module-04/05 imports — zero matches. The only "external" dependency is the optional `sentence_transformers` package, which (if usable) loads a local/cached HF model — see §16 for a real failure mode found at runtime. | SOURCE-CODE VERIFIED |
| Storage systems | Local filesystem only (JSON input files, rotating log files under `data/logs/`, `joblib` model files under `data/models/`) | `data_store.py`, `server.py:45-56`, `ml/hazard_predictor.py:32` |
| Postgres (`database/` at repo root) | Exists (docker-compose, schema.sql) but is **explicitly not consumed** by Module 02 — confirmed no `psycopg2`/`sqlalchemy` in `requirements.txt`, and top-level README states "not yet consumed by 01/02" | `database/docker-compose.yml`, `README.md:61` |
| Config files | `.env` (only `NWIS_API_KEY` currently set — confirmed by reading `.env` keys, not values), `requirements.txt` | — |
| Environment variables (all optional, coded defaults shown) | `NWIS_API_KEY` (auth secret; unset = auth disabled), `NWIS_RATE_LIMIT_ENABLED` (default true), `NWIS_RATE_LIMIT_MAX_REQUESTS` (default 60), `NWIS_RATE_LIMIT_WINDOW_SECONDS` (default 60), `NWIS_CORS_ORIGINS` (extra allowed origins, comma-separated), `NWIS_ENV` (dev/production), `NWIS_HOST`, `NWIS_PORT` | `auth.py:29-32`, `server.py:95-96`, `run_server.py:169-170` |
| Authentication | Single shared **API key** via `X-API-Key` header, compared with `secrets.compare_digest`. Auto-generated into `.env` on first run if absent (`run_server.py:_ensure_api_key`). Auth is applied per-route via `Depends(require_api_key)` on every data/analysis endpoint; `/`, `/api/v2/health`, `/docs` are intentionally open. **If `NWIS_API_KEY` is unset/empty, auth is silently OFF** (`auth_enabled()` returns `bool(API_KEY)`). | `auth.py:29-43`; RUNTIME VERIFIED: a request to `/api/v2/wells` with no key returned HTTP 401; with the correct key from `.env` it returned 200. |
| Authorization | None beyond the single key — no roles, no per-well/per-user scoping. "Single-operator internal tool" by the code's own description. | `auth.py` module docstring |
| Rate limiting | In-memory sliding window per API key (or per client IP if no key), default 60 req/60s, returns HTTP 429 when exceeded | `auth.py:46-67` |
| CORS | Restricted allowlist: `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:5173` + anything in `NWIS_CORS_ORIGINS` (comma-separated). NOT wide-open (code comment explicitly says it used to be `"*"` and was tightened). | `server.py:91-102` |
| API key requirement | Yes, on every `/api/v2/*` route except `/api/v2/health`; `.env` currently has a 43-character key set, so **auth is currently ENABLED** in the checked-out `.env`. | RUNTIME VERIFIED |
| Is it currently running? | **Yes — three separate processes**, in three different states of staleness. See §14. | RUNTIME VERIFIED |

---

## 3. Complete Well Inventory

**Source of truth**: `data/synthetic/wells.json` (static JSON, loaded by `data_store.py` into `Well` Pydantic objects, exposed via `GET /api/v2/wells`). RUNTIME VERIFIED to match the JSON file exactly (12 wells, same IDs, same field values).

All wells are **DEMO / SYNTHETIC** — generated by `data/synthetic/generate_testbed.py` with `random.seed(42)`. Field center coordinates (`FIELDS` list — Nahorkatiya, Moran, Baghjan, Hugrijan, Rajapukhuri) are labeled in the generator's comment as "real coordinates approx" for actual OIL India operational areas in Assam, but each well's actual `surface_lat`/`surface_lon` is `field_center ± random.uniform(-0.08, 0.08)` degrees — i.e., **scattered randomly around a real area, not a real wellhead location**. Operator field is also randomized (85% OIL_INDIA_LIMITED / 15% ONGC per `generate_testbed.py:416`) — not sourced from any real asset register.

Note: `generate_testbed.py`'s own module docstring claims "15 realistic wells" but the code only emits **3 wells × 4 fields = 12** (the 5th field, Rajapukhuri/RPK, is coded to get `wells_in_field = 0`). This 15-vs-12 docstring mismatch is itself evidence the generator script was edited after being written and nobody updated the comment — a small but real internal inconsistency.

### Full well table (RUNTIME VERIFIED against `GET /api/v2/wells/{id}`, `/api/v2/trajectory/{id}`, `/api/v2/formations/{id}`, `/api/v2/events/{id}`)

| Well ID | Well Name | Field | Lat | Lon | Coord. System | Surface X/Y | Total Depth (m MD) | Current Depth | Status | Trajectory? | Formation Data? | Events? | Hazards? | Casing? | Telemetry? | DORS? | Source | Verified? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WELL-NHK-001 | NHK-001 | Nahorkatiya | 27.149183 | 95.292326 | WGS84 lat/lon only | None (no UTM/projected X/Y stored) | 2820.0 | N/A (not drilling) | PRODUCING | Yes (94 stations) | Yes (7 tops) | Yes (2) | Derivable from events | No | No | Yes (as offset) | DEMO/SYNTHETIC | RUNTIME VERIFIED |
| WELL-NHK-002 | NHK-002 | Nahorkatiya | 27.260229 | 95.291487 | WGS84 | None | 3244.0 | N/A | COMPLETED | Yes (109) | Yes (9) | Yes (2) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-NHK-003 | NHK-003 | Nahorkatiya | 27.152943 | 95.406274 | WGS84 | None | 3461.0 | N/A | SUSPENDED | Yes (116) | Yes (9) | Yes (2) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-MRN-004 | MRN-004 | Moran | 27.037065 | 94.981018 | WGS84 | None | 3108.0 | N/A | ABANDONED | Yes (104) | Yes (8) | Yes (2) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-MRN-005 | MRN-005 | Moran | 27.088685 | 94.984708 | WGS84 | None | 3490.0 | N/A | SUSPENDED | Yes (117) | Yes (9) | Yes (4) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-MRN-006 | MRN-006 | Moran | 27.078776 | 95.047567 | WGS84 | None | 2949.0 | N/A | COMPLETED | Yes (99) | Yes (7) | Yes (5) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-BGJ-007 | BGJ-007 | Baghjan | 27.486087 | 95.393323 | WGS84 | None | 3064.0 | N/A | COMPLETED | Yes (103) | Yes (8) | Yes (4) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-BGJ-008 | BGJ-008 | Baghjan | 27.600434 | 95.312772 | WGS84 | None | 3296.0 | N/A | ABANDONED | Yes (110) | Yes (8) | Yes (3) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-BGJ-009 | BGJ-009 | Baghjan | 27.607952 | 95.283917 | WGS84 | None | 3160.0 | N/A | SUSPENDED (operator: ONGC) | Yes (106) | Yes (8) | Yes (2) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-HGJ-010 | HGJ-010 | Hugrijan | 27.277859 | 94.738453 | WGS84 | None | 2882.0 | N/A | SUSPENDED | Yes (97) | Yes (8) | Yes (4) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| WELL-HGJ-011 | HGJ-011 | Hugrijan | 27.202888 | 94.750397 | WGS84 | None | 2843.0 | N/A | ABANDONED | Yes (95) | Yes (8) | Yes (6) | Derivable | No | No | Yes | SYNTHETIC | VERIFIED |
| **WELL-HGJ-012** | HGJ-012 | Hugrijan | 27.274571 | 94.723159 | WGS84 | None | 2838.0 | **ACTIVE WELL — see §12** | COMPLETED | Yes (95) | Yes (8) | Yes (3) | Derivable | No | **Yes — the only well with telemetry (3600 records, 8m window)** | Yes | SYNTHETIC | VERIFIED |

Totals (RUNTIME VERIFIED via `/api/v2/health`, `/api/v2/formations`, `/api/v2/events`): **12 wells, 97 formation tops, 39 drilling events, 3,600 telemetry records (all for one well)**.

**Aliases**: No well-ID aliasing/dedup logic exists anywhere in Module 02's code (`grep -i alias` only matches an HTTP header alias and an unrelated function-name alias — confirmed, not well-name logic). Well IDs, names, and field codes are 1:1 and consistent; there is no risk of e.g. "F-12" vs "WELL-F-012" collision inside this module's own data. (That style of alias *does* exist in the separate, unconnected `real_data/` Volve dataset — e.g. `15/9-F-12` vs `WELL-15_9-F-12` — but those are not wells known to Module 02 at all.)

---

## 4. Spatial / Coordinate System

**What exists, verified from `models/schemas.py` and `engines/`:**

- `Well.surface_lat` / `Well.surface_lon` — WGS84-style decimal degrees, one pair per well (surface/wellhead location only — no separate "rig site" coordinate).
- `Well.kb_elevation_m` — a single elevation reference per well (90–130m range in this dataset), used as the sole "RKB"-equivalent datum. There is no separate ground-level elevation vs. RKB vs. MSL distinction — one field does triple duty.
- `SurveyStation.ns_m` / `ew_m` — cumulative North/East offset **in meters, relative to that well's own wellhead (local origin = (0,0) at surface)**. This is NOT a shared project/field coordinate system — each well's NS/EW is self-referential.
- `SurveyStation.tvd_m`, `tvdss_m` — True Vertical Depth and TVD-Subsea; `tvdss_m = tvd_m - kb_elevation_m` (`stratigraphic_correlator.py:162-168`).
- No UTM/projected X,Y field exists anywhere in the schema or data files. No EPSG code is referenced anywhere in the codebase (confirmed by grep — zero matches for "EPSG" or "UTM" in `modules/02_nwis_backend`).
- `dors_engine.haversine_km()` computes great-circle distance between two wells' `surface_lat/lon` (`engines/dors_engine.py:52-59`) — this is the **only** geospatial transform in the module, and it is a distance scalar, not a coordinate projection. It is used for DORS's spatial score and nowhere else.

**Can you safely visualize multiple real well trajectories together in 3D? → PARTIALLY.**

Why:
- Each well's **subsurface shape** (inclination/azimuth/TVD/NS/EW) is internally self-consistent and computed with a real SPE/API minimum-curvature implementation (`engines/trajectory_engine.py`) — verified correct (see §5).
- Each well **does** have a real, distinct geographic surface location (lat/lon) — verified distinct per well, not placeholder zeros.
- **However, nothing in the backend converts lat/lon into a shared Cartesian scene origin and adds each well's own NS/EW on top of it.** `align_horizons_across_wells` and the DORS engine only ever compare wells via scalar distance (haversine) or depth-domain alignment (TVD/formation), never via a merged XY scene coordinate. If you render well A's trajectory using A's own NS/EW as (0,0)-relative and well B's using B's own NS/EW as its own (0,0)-relative, and then also want their wellheads correctly offset from each other on a map, the new visualization module will need to do that transform itself — e.g., pick a field-center lat/lon origin, project each well's surface_lat/lon into local meters (equirectangular approximation is fine at this scale, or proper UTM Zone 46N for Assam), and add that per-well offset to each well's own NS/EW before plotting. This is a well-defined, low-risk transform using only real, already-present fields (`surface_lat`, `surface_lon`, `ns_m`, `ew_m`) — **it requires new code, but zero fabricated data**.
- No coordinate transform code currently exists in the repo to copy for this — the closest precedent is the haversine function (`dors_engine.py:52-59`), which is distance-only, not a projection.

---

## 5. Trajectory / Directional Survey Data

**Source of truth**: `data/synthetic/trajectories.json`, generated by `generate_trajectory_stations()` in `generate_testbed.py` using **actual minimum-curvature math** (not a toy approximation) — survey stations every 30m MD, built-angle profiles differentiated by well type (Vertical/J-Type/S-Type), inclination/azimuth integrated via the standard dogleg/ratio-factor formulas also implemented independently in `engines/trajectory_engine.py` (ported from a teammate's module, SPE/API Minimum Curvature Method, Sawaryn & Thorogood 2005).

| Field | Verified detail |
|---|---|
| Stations per well | 94–117 (varies by TD; ~30m spacing) — RUNTIME VERIFIED per-well via `/api/v2/trajectory/{id}` |
| Station fields | `md_m, inclination_deg, azimuth_deg, tvd_m, ns_m, ew_m, tvdss_m` | `models/schemas.py:59-66` |
| Units | Meters, degrees | consistent throughout |
| NS/EW — source or calculated? | **Calculated** at data-generation time using minimum curvature (not raw survey input — there is no raw MD/Inc/Azi-only input file; the generator computes NS/EW/TVD directly as it builds stations) |
| TVD/TVDSS — source or calculated? | TVD is calculated the same way at generation time. At **query time**, `tvd_at_md()` in `engines/stratigraphic_correlator.py` re-derives TVD at arbitrary (non-station) MDs using a real minimum-curvature sub-interval interpolation + tangential extrapolation beyond the last station (not flat/linear clamping — this was specifically verified against real logic in `trajectory_engine.py`). |
| Real / synthetic | **100% synthetic** — procedurally generated, not from any logged survey |
| API endpoint | `GET /api/v2/trajectory/{well_id}` (auth required) — returns `well_id, well_name, method, well_type, stations[]`. **This endpoint's own code comment explicitly documents that it was previously internal-only** — a prior audit had flagged this as IMPLEMENTED INTERNALLY / NOT EXPOSED, and it has since been exposed. Confirmed present and working in the current source (`server.py:204-229`), RUNTIME VERIFIED returning 95 real stations for `WELL-HGJ-012` (first station MD=30, last MD=2838/TVD=2655.33). |

### Per-well trajectory table

| Well ID | Stations | Source | Real/Synthetic | API endpoint | Verified |
|---|---|---|---|---|---|
| All 12 wells | 94–117 each | `data/synthetic/trajectories.json` | SYNTHETIC | `GET /api/v2/trajectory/{well_id}` | RUNTIME VERIFIED |

**Separately, real trajectory data exists but is disconnected** (see §1, §16): `real_data\real_trajectories_witsml.json` and `real_data\real_trajectories.json` contain **22 real Volve-field wells** (e.g. `WELL-15_9-F-1`, 100 stations; `WELL-15_9-F-12`, 210 stations) in the **exact same `WellTrajectory`/`SurveyStation` JSON shape** Module 02 uses — confirmed by directly loading one into the `WellTrajectory` Pydantic model from `models/schemas.py` (`real_data/validate_m2_m4_trajectory.py:23,28` does exactly this). `data_store.py` never reads this path. There is no code anywhere that would need to change in `models/schemas.py` to ingest it — only `data_store.py`'s `load()` would need a second input path, and that is new work not done here (audit only).

---

## 6. Formation Data

**Source of truth**: `data/synthetic/formation_tops.json`, generated from a hard-coded `ASSAM_STRATIGRAPHY` table in `generate_testbed.py:25-37` (10 named formations: Alluvium, Dihing, Tipam Sandstone, Girujan Clay, Barail Sandstone, Barail Coal-Shale, Kopili, Sylhet Limestone, Langpar, Basement) — these are **real, named Assam-Arakan Basin formations** (standard regional nomenclature), but each well's **top/base depths are randomly perturbed (±12%) from a shared base-case profile**, not independently logged per well. So: formation *names and typical depth order* reflect real regional geology; the *specific numeric top/base MD for any one well* is synthetic.

| Field | Detail |
|---|---|
| Schema | `well_id, well_name, formation_name, top_md_m, top_tvd_m, base_md_m, thickness_m, pore_pressure_gradient_ppg, lithology, confidence (0-1)` | `models/schemas.py:121-131` |
| Per-well count | 7–9 tops per well (97 total across 12 wells) — RUNTIME VERIFIED |
| Units | Meters (MD and TVD); ppg for pore pressure gradient |
| Source | DEMO/SYNTHETIC — `formation_tops_for_well()` in `generate_testbed.py:178-213` |
| Cross-well correlation possible? | **Yes, and it's actually implemented** — `engines/stratigraphic_correlator.py`'s `formation_at_depth`, `stratigraphic_depth` (d_strat = TVD − Top_TVD), and `align_horizons_across_wells` genuinely align different wells at the *same geological horizon* rather than the same MD (specifically built to defeat the "Trajectory Trap" of comparing MD between a vertical and a deviated well). Exposed via `GET /api/v2/stratigraphic_depth_track/{well_id}` — RUNTIME VERIFIED: for `WELL-HGJ-012` at 2000m MD ("Barail Sandstone"), it correctly aligned 4 offset wells to the same `d_strat_m=409.7` and returned each one's equivalent MD/TVD. |
| Formation surfaces / interpolation | **Not implemented.** The backend has per-well top/base depths (enough to draw formation *bands* per well, e.g., as horizontal slabs on a 2D/3D log track) but there is no areal/3D surface-fitting (e.g., kriging a formation top across (x,y) into a continuous surface). Building full 3D formation surfaces from this data is possible (12 wells × 7-9 points per named formation is a legitimate, if sparse, input to a real interpolator) but is genuinely new work, not something to fabricate. |

`GET /api/v2/formations/{well_id}` and `GET /api/v2/formations` (all-wells, filterable by name) — both RUNTIME VERIFIED working (200 OK, real data returned).

---

## 7. Drilling Events / Historical Events

**Source of truth**: `data/synthetic/drilling_events.json`, generated by `generate_incidents_for_well()` (`generate_testbed.py:216-309`) — 2–6 events per well, **depth-indexed to specific formations** (not generic placeholder text), using a real IADC-NPT-code mapping and a template library per hazard type (MUD_LOSS, STUCK_PIPE, KICK, WELLBORE_INSTABILITY) with randomized realistic parameters (loss rate, pit gain, SICP/SIDPP, mud-weight deltas) plugged into natural-language narrative templates.

**Exact schema** (`models/schemas.py:138-154`):
```
event_id, well_id, event_type (enum), severity (LOW/MEDIUM/HIGH/CRITICAL),
depth_start_md_m, depth_end_md_m, formation, raw_narrative, npt_hours,
iadc_npt_code, loss_rate_bbl_hr, mitigation_description, outcome,
confidence (0-1), source_document, source_page
```

Each event carries a **fabricated-looking but structurally real** `source_document` (e.g., `"DDR_WELL-HGJ-012_1396m.pdf"`) and `source_page` — these are **synthetic filenames that do not correspond to any actual PDF on disk**; they exist purely to exercise the "GROUNDED"/"PARTIAL" audit-status field in the 4-Pillar Confidence model. Do not mistake these for real document provenance.

**This IS real depth-indexed structured data** (not free text alone) — `depth_start_md_m`/`depth_end_md_m` are genuine numeric fields used by the risk-corridor clustering and DORS hazard scoring, not just mentioned inside the narrative string.

### Per-well summary (RUNTIME VERIFIED via `/api/v2/events/{well_id}`)

| Well | Event count | Source | Verified? |
|---|---|---|---|
| WELL-NHK-001 | 2 | SYNTHETIC | RUNTIME VERIFIED |
| WELL-NHK-002 | 2 | SYNTHETIC | VERIFIED |
| WELL-NHK-003 | 2 | SYNTHETIC | VERIFIED |
| WELL-MRN-004 | 2 | SYNTHETIC | VERIFIED |
| WELL-MRN-005 | 4 | SYNTHETIC | VERIFIED |
| WELL-MRN-006 | 5 | SYNTHETIC | VERIFIED |
| WELL-BGJ-007 | 4 | SYNTHETIC | VERIFIED |
| WELL-BGJ-008 | 3 | SYNTHETIC | VERIFIED |
| WELL-BGJ-009 | 2 | SYNTHETIC | VERIFIED |
| WELL-HGJ-010 | 4 | SYNTHETIC | VERIFIED |
| WELL-HGJ-011 | 6 | SYNTHETIC | VERIFIED |
| WELL-HGJ-012 | 3 | SYNTHETIC | VERIFIED |
| **Total** | **39** | | matches `/api/v2/health` |

Both structured filtering (`GET /api/v2/events?hazard_type=&formation=&min_severity=&depth_min=&depth_max=`) and free-text search (`GET /api/v2/events/search?query=...`) are implemented — see §16 for a real operational bug found in the search path at runtime.

---

## 8. Hazards / Risk Corridors

There is **no standalone "hazard" or "RiskCorridor" static dataset** — risk corridors are **computed on demand** by clustering the drilling-events data above. `engines/risk_corridor_engine.identify_risk_corridors()` groups same-hazard-type events within a 100m depth window (`cluster_window_m`) into a `RiskCorridor`, requiring ≥2 events (or 1 CRITICAL/HIGH event alone).

**Exact `RiskCorridor` schema** (`models/schemas.py:218-244`):
```
corridor_id, hazard_type, depth_start_m, depth_end_m, contributing_wells[],
contributing_events[], event_count, avg_npt_hours, max_severity,
historical_frequency, lead_distance_m, proximity_risk_level, recommended_action, formation
```

RUNTIME VERIFIED (`GET /api/v2/corridors/WELL-HGJ-012?depth=2000` → 6 corridors returned, e.g. a STUCK_PIPE corridor at 1907.5–1994.8m built from BGJ-009's one HIGH-severity event, `proximity_risk_level: HIGH` because the bit depth (2000m) is already past the corridor start).

**Provenance verdict: MIXED, but honestly so — DERIVED FROM SYNTHETIC, not independently labeled "real hazards."** Corridors are a deterministic function of the synthetic events above — they are real *computations* over fabricated *inputs*. The clustering/scoring/early-warning logic itself (depth window, Gaussian severity smoothing, proximity states) is genuine, reusable engineering; the hazard *occurrences* it's clustering are fabricated.

An **ahead-of-bit lookahead** variant also exists and was RUNTIME VERIFIED: `GET /api/v2/ahead_of_bit/{well_id}?depth=&max_lookahead_m=&step_m=` projects 0–200m ahead in configurable steps, mapping each projected MD into offset wells via the same stratigraphic alignment used in §6, returning a Gaussian-smoothed per-hazard-type risk density at each step (`engines/risk_corridor_engine.py:469-598`).

---

## 9. Casing Data

**IMPLEMENTED: NOT AT ALL in the current source tree.** There is no `Casing` model in `models/schemas.py`, no casing data file, no casing engine logic, no casing endpoint anywhere in `server.py` as it exists on disk today. Confirmed by grepping the entire module for "casing" (only hits are the word appearing inside synthetic event *narrative text*, e.g. `"...cased off interval"` and `"...pumped casing cement to seal"` — plain English inside a fabricated string, not structured data).

**Important runtime discrepancy**: a **stale, already-running process on port 8012** (the port the top-level README documents as canonical) DOES expose `GET /api/v2/casing/{well_id}` and `GET /api/v2/casing` in its live OpenAPI schema. That process is running **older code that is no longer on disk** (it also reports 14 wells, not the current 12, and is missing newer routes like `/events/search` and `/stratigraphic_depth_track`). This means: **casing support existed in this codebase at some earlier point and was since removed/refactored out**, but a stale process is still answering for it. Do not build against that port's current behavior — it does not reflect the checked-out source. See §14/§16 for full detail.

Conclusion: **CASING DATA IS NOT AVAILABLE** (not even internally) in the current Module 02 source. If needed, it must be added fresh (new schema + new data + new endpoint) — there is nothing to "expose" that already exists internally.

---

## 10. Telemetry / Real-Time Data

**Source of truth**: `data/synthetic/telemetry_stream.json` — a single bundle (not per-well), generated by `generate_telemetry_stream()` (`generate_testbed.py:312-378`).

| Field | Detail |
|---|---|
| Telemetry source | Synthetic 1 Hz stream with a **deliberately injected anomaly** (a simulated mud-loss signature at ~70% through the depth range: `flow_out` drops, `pit_volume` drops, SPP dips) | `generate_testbed.py:333,352-355` |
| Scope | **Only ONE well has telemetry**: the "active well" `WELL-HGJ-012`, covering an 8-metre MD window (2128.5–2136.0m) over 1 simulated hour, 3,600 records total | `telemetry_stream.json` top-level `active_well_id`, `start_depth_m`, `end_depth_m` — RUNTIME VERIFIED via `/api/v2/health` (`telemetry_records: 3600`) and `/api/v2/telemetry/WELL-HGJ-012?depth=2130` (5 records returned, realistic field values e.g. `rop_m_hr: 5.93, wob_klbs: 30.86, standpipe_pressure_psi: 2840.1`) |
| Fields | `well_id, timestamp, depth_m, rop_m_hr, wob_klbs, rpm, torque_kn_m, standpipe_pressure_psi, flow_in_lpm, flow_out_lpm, pit_volume_bbl, mud_weight_ppg, d_exponent` | `models/schemas.py:161-174` |
| Live / historical / simulated | **Simulated, pre-generated, static** — not a live feed, not a replay of a real logged stream. Code's own docstring in `live/replay_engine.py:9-25` is explicit: "the depth progression is driven by the well's full TRAJECTORY ... not the telemetry stream" and "sensor-anomaly scoring only has genuine telemetry to work with while the simulated depth is inside that same 2128.5–2136.0m window." |
| Query outside that 8m window | RUNTIME VERIFIED: `GET /api/v2/telemetry/WELL-HGJ-012?depth=500` returns `records_returned: 0, latest: null` — confirmed, not silently faked. |
| API | `GET /api/v2/telemetry/{well_id}?depth=&window=` — RUNTIME VERIFIED, 200 OK with real-shaped values inside the window, empty outside it |
| Relation to bit depth | Caller supplies `depth` explicitly; the endpoint returns the nearest-preceding records up to that depth (`data_store.get_telemetry_at`) — there is no server-side "current bit position" state that telemetry tracks automatically; see §12. |

**Conclusion: telemetry readiness for the visualization module is effectively zero** beyond one well's narrow depth window — it is not representative "live drilling data" for a general-purpose viewer.

---

## 11. DORS / Offset Ranking

**Fully reverse-engineered from `engines/dors_engine.py` and cross-checked against live output.**

### Exact formula (code-defined, `engines/dors_engine.py:23-29,292-357`)

```
DORS(offset, active, d_t) =
    0.20 · S_spatial
  + 0.30 · S_formation
  + 0.20 · S_depth
  + 0.15 · S_trajectory
  + 0.15 · S_hazard
```
then, **as a separate post-hoc multiplicative gate (NOT part of the 1.0-summing weights)**: if a "structural fault boundary" heuristic fires (same formation's top sits at an implausible TVDSS offset between the two wells given their lateral distance and an assumed 6° regional dip + 150m throw margin), the total is multiplied by `FAULT_PENALTY_FACTOR = 0.20`.

Sub-score definitions, all SOURCE-CODE VERIFIED:
- **S_spatial** = `max(0, 1 - haversine_km(active, offset) / r_max_km)` — `score_spatial()`, line 66-76. `r_max_km` defaults to 25km, caller-adjustable via `radius_km` query param.
- **S_formation**: 1.0 if the active formation is penetrated by the offset well at the *same* depth window; 0.75 if same formation but different depth window; 0.6 if a *different* formation but same regional stratigraphic group (`ASSAM_FORMATION_GROUPS`); 0.1 otherwise; 0.3 if no active-formation info at all. `score_formation()`, line 97-126.
- **S_depth**: overlap fraction between the offset well's drilled MD range and a `[d_t − 50m, d_t + 100m]` lookahead window (150m total). `score_depth()`, line 133-157.
- **S_trajectory**: a Hausdorff-style comparison of inclination/azimuth *profiles* sampled at 10 points across the overlapping MD range (mean + max distance blend), plus a 0.5 penalty if well types differ. Deliberately NOT a single average-inclination scalar — explicitly designed (per in-code citation of a Schlumberger patent) to catch two wells with the same average angle but different build shapes. `score_trajectory()`, line 175-223.
- **S_hazard** = `min(1, Σ Severity(e) · exp(−(d_e − d_t)² / (2·25²)))` summed over the offset well's events — a Gaussian-smoothed hazard-proximity density, σ=25m. `score_hazard()`, line 230-248.

### What inputs are real vs. missing/fallback
- Spatial (lat/lon) — real per-well values present, SYNTHETIC provenance (§3).
- Formation — real per-well structured tops, SYNTHETIC provenance (§6).
- Depth overlap — real per-well trajectory MD ranges, SYNTHETIC provenance (§5).
- Trajectory shape — real per-well inclination/azimuth profiles, SYNTHETIC provenance (§5).
- Hazard — real per-well structured events, SYNTHETIC provenance (§7).
- **Nothing in DORS silently defaults/fakes a missing input** — e.g., if a well has no trajectory at all it is simply excluded from ranking (`rank_offset_wells`, line 392-394: `if offset_traj is None: continue`).

### Live, ranked output for the actual active well (RUNTIME VERIFIED: `GET /api/v2/offset_rank/WELL-HGJ-012?depth=2000&radius_km=25&top_n=5`, response is real, not approximated)

| Rank | Well ID | Distance (km) | DORS total | Spatial | Formation | Depth | Trajectory | Hazard | Structural flag |
|---|---|---|---|---|---|---|---|---|---|
| 1 | WELL-HGJ-010 | 1.555 | 0.7270 | 0.9689 | 1.0 | 1.0 | 0.2215 | 0.0 | SAME_FAULT_BLOCK |
| 2 | WELL-HGJ-011 | 8.413 | 0.7245 | 0.8317 | 1.0 | 1.0 | 0.3876 | 0.0 | SAME_FAULT_BLOCK |
| 3 | WELL-NHK-001 | 57.985 | 0.6446 | 0.0 | 1.0 | 1.0 | 0.9642 | 0.0 | SAME_FAULT_BLOCK |
| 4 | WELL-MRN-005 | 33.114 | 0.6021 | 0.3377 | 1.0 | 1.0 | 0.2307 | 0.0 | SAME_FAULT_BLOCK |
| 5 | WELL-MRN-004 | 36.719 | 0.5949 | 0.2656 | 1.0 | 1.0 | 0.2786 | 0.0 | SAME_FAULT_BLOCK |

`dors_formula` string is literally echoed back in the API response for self-documentation: `"DORS = 0.20·S_spatial + 0.30·S_formation + 0.20·S_depth + 0.15·S_trajectory + 0.15·S_hazard"`.

---

## 12. Nearby / Radius Search

- Parameter: `radius_km` (float, km), default **25.0**, supplied by the caller on `GET /api/v2/offset_rank/{well_id}` and `GET /api/v2/analyze/{well_id}` (and reused internally by `/corridors`, `/ahead_of_bit`, `/stratigraphic_depth_track`, each with their own hardcoded or caller-set radius).
- Distance calc: haversine great-circle on `surface_lat/surface_lon`, server-side (`dors_engine.haversine_km`).
- **Critical, RUNTIME-VERIFIED behavior**: `radius_km` is **NOT a hard inclusion/exclusion filter**. Testing `radius_km = 1, 3, 5, 10` against the same well/depth returned **the same 11 offset wells back every time** (every well except the active one) — only their `distance_km` and resulting `spatial`/`total` DORS scores changed (because `S_spatial = max(0, 1 - dist/r_max_km)` just clamps to 0 once a well is beyond the radius, it doesn't remove the well from the ranked list). So "radius" in this backend is a **scoring normalization parameter**, not a spatial filter. A visualization module that wants an actual "only show wells within N km" hard filter (e.g., for an "8–12 nearby wells" field mode) will need to filter the returned `rankings[]` by `distance_km <= N` itself — the backend will happily hand back a well 70km away with a `total` DORS score if asked for `radius_km=1`.
- All filtering is server-side computation, but **inclusion is never actually restricted by radius** — only re-scored.
- All wells share the same lat/lon reference system (plain WGS84 degrees), so the same haversine logic could drive radius search for both 2D map view and a 3D "offset candidates" picker — but the hard-radius cutoff must be implemented client/caller-side, since the backend doesn't.

---

## 13. Current Active Well

- **Active well ID: `WELL-HGJ-012`** — RUNTIME VERIFIED via `GET /api/v2/health` → `"active_well_id": "WELL-HGJ-012"`, and via `GET /api/v2/map/wells` → `"active_well_id": "WELL-HGJ-012"`, `is_active: true` flag set on that one well's map entry.
- How it's determined: **hardcoded by the data generator**, not computed at runtime. `generate_testbed.py:455`: `active_well = wells[-1]` — literally "whichever well is generated last" (deterministic only because `random.seed(42)` is fixed). It is persisted into `telemetry_stream.json`'s `active_well_id` field and read back by `data_store.load()` (`data_store.py:132`).
- There is **no "set active well" endpoint** — it is a fixed property of the loaded dataset, not a live/mutable server concept. Every endpoint that needs "the active well" takes `well_id` as a path/query parameter from the caller instead — i.e., *any* well can be treated as "active" for `/analyze`, `/offset_rank`, etc.; `store.active_well_id` is only actually consulted by the telemetry endpoint (to validate the well_id) and by `generate_testbed.py` at data-build time (to decide which well gets the one telemetry stream).
- Current depth / current formation / current operation state: **not tracked server-side as live state.** The caller always supplies `depth` as a query parameter to every analysis endpoint; nothing in the backend maintains an evolving "current bit position" between requests (the live-replay SSE endpoint simulates this by looping through depths within one connection, but that state dies with the connection).

---

## 14. Complete API Inventory

All 18 routes below are from the **current source** (`server.py`), confirmed via `GET /openapi.json` against a freshly-started instance (port 8099, started for this audit, running the actual checked-out code — see runtime note). All except `/`, `/api/v2/health` require `X-API-Key`.

| Method | Path | Group | Purpose | Status |
|---|---|---|---|---|
| GET | `/` | Other | Root/liveness | WORKING |
| GET | `/api/v2/health` | Other | Health + engine/auth/rate-limit status | WORKING |
| GET | `/api/v2/wells` | Wells | List all wells (filter by field/status) | WORKING |
| GET | `/api/v2/wells/{well_id}` | Wells | Single well + summary counts | WORKING |
| GET | `/api/v2/trajectory/{well_id}` | Trajectory | Full survey-station list | WORKING (recently exposed — see §5) |
| GET | `/api/v2/formations/{well_id}` | Formations | Formation tops for one well | WORKING |
| GET | `/api/v2/formations` | Formations | All formation tops, filterable | WORKING |
| GET | `/api/v2/stratigraphic_depth_track/{well_id}` | Formations | Cross-well horizon alignment at active depth | WORKING |
| GET | `/api/v2/events/search` | Events | Free-text/semantic search over narratives | WORKING, but **first call after process start has a severe latency bug** — see §21 |
| GET | `/api/v2/events/{well_id}` | Events | All events for one well | WORKING |
| GET | `/api/v2/events` | Events | Structured filter across all wells (capped at 100) | WORKING |
| GET | `/api/v2/corridors/{well_id}` | Hazards/Corridors | Risk corridors ahead of bit | WORKING |
| GET | `/api/v2/ahead_of_bit/{well_id}` | Hazards/Corridors | 0–200m projected lookahead risk density | WORKING |
| — | `/api/v2/casing*` | Casing | — | **NOT IMPLEMENTED** in current source (present only in a stale process — see §9) |
| GET | `/api/v2/telemetry/{well_id}` | Telemetry | Telemetry near a given depth | WORKING (empty outside the one well's 8m window — correct, not a bug) |
| GET | `/api/v2/offset_rank/{well_id}` | DORS | 5-factor DORS ranking | WORKING |
| GET | `/api/v2/analyze/{well_id}` | DORS/Risk | Full pipeline: DORS → Strat → Corridors → 4-Pillar | WORKING |
| GET | `/api/v2/map/wells` | Map | All wells with lat/lon + status for GIS map | WORKING |
| GET | `/api/v2/live/replay/{well_id}` | Other (SSE) | Simulated real-time alert stream | IMPLEMENTED, not individually load-tested (SSE), but `replay_engine.py` reuses the already-verified `analyze()` pipeline internally so it is very likely WORKING; code docstring flags its own limitation around browser `EventSource` + custom auth headers as an open integration gap |

No `/api/v3`, no AI/LLM routes, no "reports" or "knowledge-graph" endpoints exist in this module (those belong to Module 01/05 per the top-level README, out of scope here and confirmed absent by route listing).

---

## 15. Actual Runtime Verification

**SOURCE-CODE VERIFIED vs RUNTIME VERIFIED is called out explicitly below.** Three processes were found bound to relevant ports at audit time:

| Port | What it is | Match to current source? |
|---|---|---|
| 8001 | Module 01 (Document Intelligence) — out of scope, confirmed via root response `"service":"NWIS Document Intelligence API"` | N/A |
| 8002 | **Stale Module 02 process** (3 listener entries — likely a reload-mode parent+worker pair from an earlier session). `GET /openapi.json` shows 17 routes, **missing `/api/v2/trajectory/{well_id}`** which exists in current `server.py`. Wells=12 (matches current data). | Close, but NOT an exact match — predates the trajectory-endpoint addition |
| 8012 | **Stale Module 02 process**, and notably the port the top-level repo README documents as the canonical run command. `GET /api/v2/health` response is **missing the entire `"auth"` block** the current `server.py` always includes, and `GET /openapi.json` shows **16 routes including `/api/v2/casing/{well_id}` and `/api/v2/casing`**, which do not exist anywhere in the current source tree, and 14 wells (current `wells.json` has 12). | **Does not match current source at all** — running meaningfully older code |
| 8099 | **Instance started fresh for this audit** (`NWIS_PORT=8099 NWIS_ENV=production python run_server.py`), confirmed via `/openapi.json` to expose the full, current 18-route set and 12 wells. | Exact match to current `server.py` — this is what all RUNTIME VERIFIED results above were captured against |

The audit agent was blocked by sandbox workload-protection policy from stopping the pre-existing 8002/8012 processes, so it left them running untouched and instead stood up the disposable 8099 instance to get accurate runtime evidence. **Recommendation: manually restart whatever is on 8012 (and 8002) before relying on them** — right now a frontend pointed at port 8012 (the documented default) would see a casing endpoint that no longer exists in source and would be missing the newer trajectory/search/ahead-of-bit/live-replay routes.

Representative verified request/response pairs are included inline above in §5, §9–§13. Auth was explicitly confirmed: no-key request → **401**; keyed request → **200**, same key as stored in `.env` (`NWIS_API_KEY`, never printed in full in this report — only its presence/length was checked).

---

## 16. Database Schema

There is no relational/document database — restating §2's finding in schema terms, the "tables" are really JSON files + their in-memory Pydantic representations:

| "Table" (JSON file / in-memory dict) | Model | Key | FK-equivalent | Columns | Row count (VERIFIED) |
|---|---|---|---|---|---|
| `wells.json` → `store.all_wells` / `wells_by_id` | `Well` | `well_id` | — | well_id, well_name, field, field_code, operator, surface_lat, surface_lon, kb_elevation_m, total_depth_md_m, well_type, spud_date, completion_date, status, witsml_uid | **12** |
| `trajectories.json` → `store.all_trajectories` | `WellTrajectory` (contains `SurveyStation[]`) | `well_id` | `well_id → Well` | well_id, well_name, method, well_type, stations[md_m, inclination_deg, azimuth_deg, tvd_m, ns_m, ew_m, tvdss_m] | **12 wells, 94–117 stations each** (total ~1,245) |
| `formation_tops.json` → `store.formation_tops_by_well` | `FormationTop` | — (no synthetic PK; `(well_id, formation_name)` is effectively unique) | `well_id → Well` | well_id, well_name, formation_name, top_md_m, top_tvd_m, base_md_m, thickness_m, pore_pressure_gradient_ppg, lithology, confidence | **97** |
| `drilling_events.json` → `store.events_by_well` / `all_events` | `DrillingEvent` | `event_id` | `well_id → Well` | event_id, well_id, event_type, severity, depth_start_md_m, depth_end_md_m, formation, raw_narrative, npt_hours, iadc_npt_code, loss_rate_bbl_hr, mitigation_description, outcome, confidence, source_document, source_page | **39** |
| `telemetry_stream.json` → `store.telemetry_records` | `TelemetryRecord` | — (timestamp+well_id is effectively unique) | `well_id → Well` | well_id, timestamp, depth_m, rop_m_hr, wob_klbs, rpm, torque_kn_m, standpipe_pressure_psi, flow_in_lpm, flow_out_lpm, pit_volume_bbl, mud_weight_ppg, d_exponent | **3,600 (one well only)** |
| `data/models/*.joblib` | scikit-learn classifiers (not a "table") | hazard-type filename | — | — | **3 files**: `kick_model.joblib`, `stuck_pipe_model.joblib`, `wellbore_instability_model.joblib`. **No `mud_loss_model.joblib` or `torque_spike_model.joblib`/`cementing_failure_model.joblib` exist** — confirmed via `ml/train_hazard_models.py`'s `MIN_POSITIVE_SAMPLES = 8` gate (`ml/feature_engineering.py:44`): those hazard types don't have ≥8 positive synthetic examples, so training was skipped and they fall back to the hand-coded heuristic (`ml/hazard_predictor.py`). RUNTIME VERIFIED: `analyze()` output showed `MUD_LOSS: m_ml_source=heuristic_fallback`, `STUCK_PIPE/KICK/WELLBORE_INSTABILITY: m_ml_source=trained_model`. |

Computed-only objects with no backing file (built per-request): `OffsetWellRanking`/`DORSComponentScores` (DORS), `RiskCorridor`/`HazardRiskAssessment`/`FourPillarConfidence` (risk), `AheadOfBitCorridor`/`AheadOfBitCorridorPoint`.

---

## 17. Data Provenance

| Category | Status | Why |
|---|---|---|
| Well locations | **DEMO / SYNTHETIC** | `surface_lat/lon = field_center ± random.uniform(-0.08,0.08)`; field centers are labeled "approx" real OIL India areas, individual wellheads are not — `generate_testbed.py:407-409` |
| Trajectories | **DEMO / SYNTHETIC** | Procedurally built per well type with randomized build rates; real minimum-curvature math applied to fake inputs — `generate_testbed.py:107-175` |
| Formations | **DEMO / SYNTHETIC** (names are real regional geology, numeric depths are not) | `ASSAM_STRATIGRAPHY` base-case table + ±12% random variance per well — `generate_testbed.py:25-37,178-213` |
| Events | **DEMO / SYNTHETIC** | Narrative templates with randomized parameters; fabricated `source_document` filenames that reference no real PDF — `generate_testbed.py:216-309` |
| Hazards / corridors | **DERIVED FROM SYNTHETIC** | Deterministic clustering computation over the synthetic events above — the clustering *algorithm* is real; its *inputs* are not |
| Casing | **NOT AVAILABLE** | No schema, no data, no engine, no endpoint anywhere in current source |
| Telemetry | **DEMO / SYNTHETIC** | Gaussian-noise random walk + one deliberately injected anomaly signature; 1 well, 8m depth window only — `generate_testbed.py:312-378` |
| DORS inputs | **DERIVED FROM SYNTHETIC** | Real scoring math (haversine, Gaussian smoothing, Hausdorff-style profile comparison) applied to the synthetic well/trajectory/formation/event data above |
| Risk data (4-Pillar Confidence) | **DERIVED FROM SYNTHETIC**, with one **REALITY/PROVENANCE NOT VERIFIED** sub-component | The ML term (`m_ml`) for STUCK_PIPE/KICK/WELLBORE_INSTABILITY comes from scikit-learn classifiers *genuinely trained* (`ml/train_hazard_models.py`) — that training process is real — but trained on the synthetic event data, so its "evidence" is synthetic at the root even though the training pipeline itself is legitimate ML engineering, not a hardcoded number |
| **Separately**: `real_data/real_trajectories*.json` | **VERIFIED REAL SOURCE** (Equinor/Statoil Volve open dataset, North Sea) | Real WITSML XML survey files under `real_data/witsml/Norway-Statoil*` parsed by `real_data/parse_witsml_trajectories.py` into the same schema Module 02 uses — but **not loaded by Module 02's `data_store.py` and not reachable via any Module 02 API route** |

No "real" label was inferred from values merely looking plausible anywhere above — every SYNTHETIC label is backed by finding the actual generator code that produced the number, with a fixed random seed.

---

## 18. 2D/3D Visualization Readiness

| Feature | Status | What's missing |
|---|---|---|
| A. Global globe — real well locations | **PARTIALLY AVAILABLE** | 12 wells have real-looking, internally-consistent (but SYNTHETIC) lat/lon via `/api/v2/map/wells`. Fine for demoing a globe; not fine for claiming "real OIL India wells" to a judge/stakeholder without disclosure. |
| B. Field/spatial mode — 8-12 nearby wells, radius search, distance, DORS ranking | **AVAILABLE NOW** (with one caveat) | All 12 wells ARE within whatever radius is requested from `/offset_rank`, because — per §12 — radius doesn't actually filter, it only rescales the spatial score. A hard-cutoff filter (`distance_km <= radius`) must be added client-side or by filtering the engine's already-returned list; the distance values themselves are real, computed haversine numbers. |
| C. Subsurface 3D — 1 active well + up to 4 offsets, real trajectories | **AVAILABLE NOW for shape, REQUIRES NEW BACKEND/FRONTEND WORK for a shared scene frame** | Each well's own trajectory (TVD/NS/EW relative to its own wellhead) is real, minimum-curvature-correct data, exposed via `/api/v2/trajectory/{id}`. But there is no shared XY scene origin merging wellhead lat/lon with each well's local NS/EW (§4) — must be built; needs no fabricated data, only a lat/lon→local-meters projection. |
| D. Geological context — formations, surfaces/interpolation | **PARTIALLY AVAILABLE** | Per-well formation bands: available now, real structured data (§6). Cross-well formation *surfaces* (areal interpolation): REQUIRES NEW WORK — the raw point data (97 tops across 12 wells) is a legitimate but sparse input; no interpolator exists. |
| E. Historical intelligence — events, hazards, depth proximity | **AVAILABLE NOW** | Real, structured, depth-indexed; corridor clustering and ahead-of-bit lookahead both work and were runtime-verified. Underlying events are SYNTHETIC (§17). |
| F. Engineering context — casing | **NOT POSSIBLE WITH CURRENT DATA** | Confirmed zero casing data/schema/endpoint anywhere in current source (§9). Must be built from scratch — nothing to "expose." |
| G. Live context — current bit, current depth, telemetry | **NOT POSSIBLE AS "LIVE"** | No server-side live bit-position state exists (§13) — every analysis call requires the caller to pass `depth` explicitly. Telemetry is real-shaped but confined to 1 well / 8m window (§10); treat any "live telemetry" demo claim as simulated, not live. |

---

## 19. Verified Data-Complete Well Set

Every one of the 12 wells has **exactly the same categories populated** (trajectory + formations + events; no well has casing or telemetry except the one exception below) — there is no genuine "best" subset by data completeness except for telemetry, because the generator applies identical logic to all 12.

| Well | Location | Trajectory | Formation | Events | Hazards (derived) | Casing | Telemetry | DORS | Verified categories (of 7) |
|---|---|---|---|---|---|---|---|---|---|
| WELL-NHK-001 | ✓ | ✓ (94) | ✓ (7) | ✓ (2) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-NHK-002 | ✓ | ✓ (109) | ✓ (9) | ✓ (2) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-NHK-003 | ✓ | ✓ (116) | ✓ (9) | ✓ (2) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-MRN-004 | ✓ | ✓ (104) | ✓ (8) | ✓ (2) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-MRN-005 | ✓ | ✓ (117) | ✓ (9) | ✓ (4) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-MRN-006 | ✓ | ✓ (99) | ✓ (7) | ✓ (5) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-BGJ-007 | ✓ | ✓ (103) | ✓ (8) | ✓ (4) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-BGJ-008 | ✓ | ✓ (110) | ✓ (8) | ✓ (3) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-BGJ-009 | ✓ | ✓ (106) | ✓ (8) | ✓ (2) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-HGJ-010 | ✓ | ✓ (97) | ✓ (8) | ✓ (4) | ✓ | ✗ | ✗ | ✓ | 5 |
| WELL-HGJ-011 | ✓ | ✓ (95) | ✓ (8) | ✓ (6, richest events) | ✓ | ✗ | ✗ | ✓ | 5 |
| **WELL-HGJ-012** | ✓ | ✓ (95) | ✓ (8) | ✓ (3) | ✓ | ✗ | **✓ (only one)** | ✓ | **6 — richest overall, and the active well** |

**Conclusions:**
- All 12 wells have verified trajectories — none fabricated beyond the already-disclosed synthetic generation.
- **No well has verified common-coordinate positioning** without new transform work (§4) — treat this as a backend/frontend gap, not a per-well data gap.
- WELL-HGJ-011 has the richest event/hazard record (6 events); WELL-HGJ-012 is the only well with any telemetry and is the designated active well, making it the natural anchor for any demo combining live-context with offset comparison.
- Any 2–5 wells from the Hugrijan field (HGJ-010/011/012) are geographically closest to each other (1.5–8.4 km apart per the DORS output in §11) and share the same regional formation sequence — the most visually coherent "nearby offset wells" cluster to demo, modulo the shared-coordinate-frame caveat in §4.

---

## 20. Recommended Normalized Frontend Contract

Proposed only — **not implemented**. Field-by-field, mapped to what's actually verified to exist.

```ts
interface WellSpatialData {
  wellId: string;            // string, required, source: Well.well_id — VERIFIED
  wellName: string;           // string, required — VERIFIED
  field: string;               // string, required — VERIFIED
  surfaceLat: number;          // deg WGS84, required, source: Well.surface_lat — VERIFIED present, SYNTHETIC value
  surfaceLon: number;          // deg WGS84, required, source: Well.surface_lon — VERIFIED present, SYNTHETIC value
  kbElevationM: number;        // meters, required, source: Well.kb_elevation_m — VERIFIED
  localOriginXY: {x:number,y:number} | null; // meters, projected from lat/lon — NOT PRESENT IN BACKEND, must be computed client-side (§4)
  totalDepthMdM: number;       // meters, required — VERIFIED
  wellType: "Vertical"|"J-Type"|"S-Type"|"Horizontal"; // required — VERIFIED
  status: "PRODUCING"|"COMPLETED"|"ABANDONED"|"SUSPENDED"|"DRILLING"; // required — VERIFIED
  operator: string;            // required — VERIFIED
}

interface SurveyStation {
  mdM: number;          // required — VERIFIED (GET /api/v2/trajectory/{id})
  inclinationDeg: number; // required — VERIFIED
  azimuthDeg: number;     // required — VERIFIED
  tvdM: number;            // required — VERIFIED
  tvdssM: number;          // required — VERIFIED
  nsM: number;             // required, LOCAL to this well's own wellhead — VERIFIED
  ewM: number;             // required, LOCAL — VERIFIED
}

interface Trajectory {
  wellId: string;         // required — VERIFIED
  method: string;          // "MINIMUM_CURVATURE" — VERIFIED
  wellType: string;         // VERIFIED
  stations: SurveyStation[]; // required — VERIFIED, source endpoint: GET /api/v2/trajectory/{well_id}
}

interface FormationInterval {
  wellId: string;            // required — VERIFIED
  formationName: string;      // required — VERIFIED
  topMdM: number;              // required — VERIFIED
  baseMdM: number;             // required — VERIFIED
  topTvdM: number;              // required — VERIFIED
  thicknessM: number;           // required — VERIFIED
  porePressureGradientPpg: number; // required — VERIFIED
  lithology: string | null;     // optional — VERIFIED present but sometimes null
  confidence: number;            // 0-1, required — VERIFIED; NOTE this is a SYNTHETIC randomized confidence, not a measurement uncertainty
  // source: GET /api/v2/formations/{well_id}
}

interface DrillingEvent {
  eventId: string;           // required — VERIFIED
  wellId: string;             // required — VERIFIED
  eventType: "MUD_LOSS"|"STUCK_PIPE"|"KICK"|"WELLBORE_INSTABILITY"|"TORQUE_SPIKE"|"CEMENTING_FAILURE"; // required — VERIFIED
  severity: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL"; // required — VERIFIED
  depthStartMdM: number;         // required — VERIFIED
  depthEndMdM: number | null;     // optional — VERIFIED
  formation: string | null;        // optional — VERIFIED
  narrative: string;                 // required — VERIFIED, SYNTHETIC text
  nptHours: number;                   // required — VERIFIED
  sourceDocument: string | null;       // optional — VERIFIED present but points to a NON-EXISTENT fabricated filename; do not surface as a real citation
  // source: GET /api/v2/events/{well_id} or /api/v2/events/search
}

interface HazardInterval { // = RiskCorridor
  corridorId: string;       // required — VERIFIED
  hazardType: string;        // required — VERIFIED
  depthStartM: number;        // required — VERIFIED
  depthEndM: number;           // required — VERIFIED
  contributingWells: string[]; // required — VERIFIED
  eventCount: number;            // required — VERIFIED
  historicalFrequency: number;    // 0-1, required — VERIFIED
  proximityRiskLevel: "LOW"|"MODERATE"|"HIGH"|"CRITICAL"; // required — VERIFIED
  leadDistanceM: number | null;    // optional — VERIFIED
  // source: GET /api/v2/corridors/{well_id} or /api/v2/ahead_of_bit/{well_id}
}

interface CasingString { /* NOT PRESENT ANYWHERE IN BACKEND — do not implement against real data; placeholder only if built fresh */ }

interface TelemetryPoint {
  wellId: string; timestamp: string; depthM: number; ropMHr: number; wobKlbs: number;
  rpm: number; torqueKnM: number; standpipePressurePsi: number; flowInLpm: number;
  flowOutLpm: number; pitVolumeBbl: number; mudWeightPpg: number; dExponent: number;
  // all VERIFIED present, but ONLY for WELL-HGJ-012, and ONLY within MD 2128.5-2136.0m
  // source: GET /api/v2/telemetry/{well_id}?depth=
}

interface DorsResult {
  rank: number; wellId: string; distanceKm: number; dorsScore: number;
  spatial: number; formation: number; depth: number; trajectory: number; hazard: number;
  structuralFaultStatus: "POSSIBLE_FAULT_BOUNDARY"|"SAME_FAULT_BLOCK"|null;
  // all VERIFIED — source: GET /api/v2/offset_rank/{well_id} or /api/v2/analyze/{well_id}
}
```

---

## 21. Missing Data / Blocking Issues

1. **No shared 3D/2D scene coordinate frame.** Each well's trajectory NS/EW is local-to-itself; lat/lon exists per well but nothing projects it into the same Cartesian space as the trajectory offsets. **Blocks**: multi-well 3D scene positioning. **Fix is new, additive frontend/backend code — not fabrication.**
2. **Radius search doesn't actually filter.** `radius_km` only rescales `S_spatial`; every well is always returned. **Blocks**: a true "8-12 nearby wells" field-mode unless a hard cutoff is added.
3. **No casing data at all**, anywhere in current source (a casing endpoint that *used to* exist is still served by a stale process on port 8012, but is gone from disk).
4. **No live/streaming bit-position state.** Every endpoint requires an explicit `depth=` query param; there is no server-side concept of "where the bit is right now" outside of one SSE connection's lifetime.
5. **Telemetry covers one well, one 8-metre window.** Any "live telemetry" visualization claim beyond that single well/window has no backing data.
6. **`events/search`'s semantic mode has a real, reproducible first-call latency bug.** First call after process start can take 60-120+ seconds (a `sentence_transformers`/tensorflow/protobuf version-conflict import chain), though it self-heals to a fast keyword fallback for the rest of that process's life. If this endpoint is called from the new module, pre-warm it on backend startup or budget for an extremely slow first request.
7. **Stale running processes (ports 8002, 8012) do not match current source.** Anyone pointing a new frontend at the "documented" port 8012 today will see routes/wells that don't exist in the actual codebase. These need a manual restart before any new integration work begins.
8. **Real Volve trajectory data sits unused in `real_data/`.** For actually real trajectories for a more credible demo, that dataset (22 wells, same schema) is the fastest path — but it is currently orthogonal to Module 02's wells/formations/events (different well-ID namespace, no corresponding formation/event data for those real wells inside Module 02).
9. **No formation-surface interpolation** exists for cross-well 3D geological layers — only per-well point data.
10. **`generate_testbed.py`'s own docstring still claims "15 realistic wells"** though the code only emits 12 — a stale comment, harmless but a sign this generator has been edited without full doc upkeep; don't trust in-code comments elsewhere in the same file without similar spot-checks.

---

## 22. Exact Files Inspected

```
modules/02_nwis_backend/server.py
modules/02_nwis_backend/run_server.py
modules/02_nwis_backend/data_store.py
modules/02_nwis_backend/auth.py
modules/02_nwis_backend/orchestrator.py
modules/02_nwis_backend/README.md
modules/02_nwis_backend/requirements.txt
modules/02_nwis_backend/.env            (keys only, no values printed)
modules/02_nwis_backend/models/schemas.py
modules/02_nwis_backend/engines/dors_engine.py
modules/02_nwis_backend/engines/stratigraphic_correlator.py
modules/02_nwis_backend/engines/risk_corridor_engine.py
modules/02_nwis_backend/engines/trajectory_engine.py
modules/02_nwis_backend/ml/hazard_predictor.py
modules/02_nwis_backend/ml/feature_engineering.py
modules/02_nwis_backend/ml/train_hazard_models.py   (grepped for thresholds only)
modules/02_nwis_backend/live/replay_engine.py
modules/02_nwis_backend/search/knowledge_search.py
modules/02_nwis_backend/data/synthetic/generate_testbed.py
modules/02_nwis_backend/data/synthetic/wells.json
modules/02_nwis_backend/data/synthetic/trajectories.json (sampled)
modules/02_nwis_backend/data/synthetic/formation_tops.json (sampled via API)
modules/02_nwis_backend/data/synthetic/drilling_events.json (sampled via API)
modules/02_nwis_backend/data/synthetic/telemetry_stream.json (sampled via API)
modules/02_nwis_backend/data/models/*.joblib (listed, not deserialized beyond existence)
modules/02_nwis_backend/data/logs/*.log (listed only)
README.md (repo root)
database/docker-compose.yml
real_data/real_trajectories.json
real_data/real_trajectories_witsml.json
real_data/real_events_module01.json
real_data/validate_m2_m4_trajectory.py
real_data/witsml/ (directory listing only)
```

Runtime tools used: `curl` against live HTTP endpoints on ports 8001/8002/8012/8099; `netstat`/PowerShell `Get-CimInstance Win32_Process` to identify running processes and their command lines; a direct Python REPL invocation of `sentence_transformers`/`tensorflow` imports to reproduce the `/events/search` latency bug outside the server process.

---

## FINAL MACHINE-READABLE SUMMARY

```
BACKEND_STATUS:
RUNNING (multiple processes; see detail — ports 8002 and 8012 are STALE/do not match current source; a fresh instance matching current source was started on port 8099 for this audit and may still be running)

ACTIVE_WELL:
WELL-HGJ-012

TOTAL_WELLS:
12

TRAJECTORY_WELLS:
12

COMMON_COORDINATE_FRAME:
NO

FORMATION_WELLS:
12

EVENT_WELLS:
12

HAZARD_WELLS:
12 (all hazards are derived/computed from event data, not a separate dataset)

CASING_WELLS:
0

TELEMETRY_WELLS:
1

DORS_AVAILABLE:
YES

RADIUS_SEARCH_AVAILABLE:
YES (but radius_km only rescales DORS spatial score — it does NOT exclude wells outside the radius; see §12)

3D_REAL_TRAJECTORIES_READY:
PARTIAL (real per-well minimum-curvature trajectory shapes exist and are exposed via API; data itself is synthetic, not real OIL India surveys; a real, unconnected Volve trajectory dataset exists separately in real_data/)

REAL_MULTI-WELL_3D_READY:
NO (no shared coordinate frame merging wellhead lat/lon with per-well local trajectory NS/EW exists anywhere in the backend; must be built new)

PRIMARY_BLOCKERS:
1. No shared XY scene coordinate frame across wells (only per-well local NS/EW + independent lat/lon)
2. radius_km does not actually filter, only rescales DORS spatial score
3. Zero casing data/schema/endpoint in current source
4. No live/streaming bit-position server state — depth must be supplied by caller every request
5. Telemetry limited to 1 well / 8-metre depth window
6. /api/v2/events/search has a real first-call latency bug (60-120s+) due to a tensorflow/protobuf version conflict triggered by the optional sentence-transformers dependency, before self-healing to keyword fallback
7. Pre-existing live processes on ports 8002 and 8012 are running stale code that does not match the current source tree (8012 even serves a /api/v2/casing endpoint that no longer exists on disk) — restart both before building against them
8. All well/trajectory/formation/event/telemetry data is synthetic (fixed random.seed(42)); a real, schema-compatible Volve-field trajectory dataset exists at real_data/ but is not wired into Module 02's API

MOST_RELEVANT_FILES:
modules/02_nwis_backend/server.py
modules/02_nwis_backend/data_store.py
modules/02_nwis_backend/models/schemas.py
modules/02_nwis_backend/engines/dors_engine.py
modules/02_nwis_backend/engines/stratigraphic_correlator.py
modules/02_nwis_backend/engines/risk_corridor_engine.py
modules/02_nwis_backend/engines/trajectory_engine.py
modules/02_nwis_backend/data/synthetic/generate_testbed.py
modules/02_nwis_backend/data/synthetic/wells.json
modules/02_nwis_backend/data/synthetic/trajectories.json
real_data/real_trajectories_witsml.json
real_data/validate_m2_m4_trajectory.py
```
