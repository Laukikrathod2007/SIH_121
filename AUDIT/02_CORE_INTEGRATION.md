# Core Integration Pass — Change Record

**Date:** 2026-10-03
**Scope:** `frontend/`, `modules/01_document_intelligence/`, `modules/02_nwis_backend/`,
`modules/04_physics_engine/`, `modules/05_predictive_analytics/`, `evidence-server/`.
**Explicitly untouched this pass:** `DrillWise-Frontend/`, `visualization_3d/`,
`extend-ai-website/`, `nwis-map-package/`, `database/`, `research/` — confirmed by
`git diff --stat` at the end of this pass; the only changes outside the listed scope
are pre-existing, pre-session modifications to `frontend/vite.config.ts` and
`frontend/public/landing/*` (added `/benchmarks` static-route support), visible in
`git log` before this session started and not touched here.

**Method:** Every service was actually started and queried (curl + a real Chromium
browser via Playwright), not inferred from source alone. Where a fix was made, it
was re-verified live afterward. Nothing was "fixed" by relaxing a check, disabling
auth, fabricating data, or training/replacing an ML model.

---

## 1. Runtime topology established

All four backend processes were started from a cold environment (no pre-existing
venvs; dependencies installed into a Python 3.12 interpreter — Python 3.14 was the
shell default but lacks prebuilt wheels for `docling`/`sentence-transformers` at
time of writing, so 3.12 was used instead; this is an environment note, not a code
change).

| Service | Command (from that module's own directory) | Port | Verified |
|---|---|---|---|
| Module 01 | `python run_server.py` | **8001** | Started cold, reached `Application startup complete`, `GET /api/v1/health` → `200 {"status":"healthy", ...}` |
| Module 02 | `python run_server.py` | **8002** | Started cold, loaded 14 wells/106 tops/44 events/3600 telemetry/10 real casing records, `GET /api/v2/health` → `200` |
| Module 04 (+05) | `python run_server.py` | **8003** | Started cold, `GET /health` → `200`, predictive models endpoint returns real (unfitted-fallback) model list |
| evidence-server | `PORT=4100 node index.js` | **4100** | Started cold, serves 42 real PDFs, confirmed via a real file download (valid PDF magic bytes) |
| frontend | `npm run dev` | 5173 | Started cold, all 14 `/app/*` routes loaded in a real browser with 0 console errors after fixes below |

### Module 01 port — resolved at the source, not guessed
**Issue:** `frontend/.env` had `VITE_M01_API_BASE=http://localhost:8011`; module 01's
own code default, `.env.example`, and every in-code comment said `8001`.
**Root cause:** `frontend/.env`'s value was simply stale — confirmed by actually
starting module 01 exactly as documented (`python run_server.py`, no `NWIS_PORT`
override) and observing `Uvicorn running on http://0.0.0.0:8001`, then a successful
authenticated `GET http://127.0.0.1:8001/api/v1/health`. Module 01's `.env` has no
`NWIS_PORT` set, so 8001 is not an alternate config choice anywhere — it is simply
what the server does when run as documented.
**Fix:** [frontend/.env](../frontend/.env) → `VITE_M01_API_BASE=http://localhost:8001`.
**Files changed:** `frontend/.env` (not tracked by git; local-only fix).
**Verified:** DocumentIngestionPage's full upload→job→result flow tested live in a
browser (see §5) — zero errors, real extraction result rendered.

### Module 02 port — resolved at the source, not guessed
**Issue:** code default and `.env.example` say `8002`; the root `README.md` told
operators to run it on `8012` instead, citing "orphaned-socket issue on this
machine" with no further evidence, and `frontend/.env`/`api.ts`'s hardcoded fallback
matched that workaround (`8012`), not the documented default.
**Investigation:** `logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md` was searched for
the claimed incident — no entry describing an actual 8002 orphaned-socket failure
was found; the only reference is the README line itself.
**Action:** actually started module 02 on its documented default, `python
run_server.py` with no `NWIS_PORT` override. Port 8002 was free and the server
started cleanly (`Uvicorn running on http://0.0.0.0:8002`), loaded its data store,
and answered `GET /api/v2/health` with a real 200. No conflict reproduced.
**A related, real phenomenon *was* reproduced during this pass** (see the module 04
note below): a uvicorn `--reload` worker that outlives its parent process can leave
a stale `LISTENING` entry in Windows' TCP table under the old PID, even after that
PID is gone — `netstat`/`Get-NetTCPConnection` keep showing it as bound, but a
fresh process can still bind the port immediately via `SO_REUSEADDR` (confirmed
with a throwaway Python socket test). This is almost certainly the real mechanism
behind the README's "orphaned-socket" claim: it looks like a stuck port from
`netstat`, but isn't actually one. Documented here instead of left as folklore.
**Fix:** standardized on the documented default, 8002, everywhere:
- `frontend/.env`: `VITE_M02_API_BASE=http://localhost:8002`
- [frontend/src/services/api.ts](../frontend/src/services/api.ts): hardcoded JS
  fallback `'http://localhost:8012'` → `'http://localhost:8002'`
- [README.md](../README.md): run instructions and directory guide corrected
- [frontend/src/pages/SystemStatusPage.tsx](../frontend/src/pages/SystemStatusPage.tsx):
  label and error-message text corrected
- [frontend/src/components/commandcenter/BackendStatusStrip.tsx](../frontend/src/components/commandcenter/BackendStatusStrip.tsx):
  label corrected
**Data/API contract affected:** none — only documentation/config/display strings;
the actual route paths and schemas are unchanged.
**Verified:** `GET /api/v2/wells`, `/events/search`, `/telemetry/{id}`,
`/corridors/{id}`, `/ahead_of_bit/{id}` all tested live with curl using the real
API key (see §6); full page walkthroughs in a real browser confirm 0 console errors
across every page that calls module 02.

### Module 04/05 architecture — made explicit, not redesigned
**Confirmed (matches `AUDIT/01_CODEBASE_MAP.md` §4):** `modules/04_physics_engine/api/server.py`
owns the single FastAPI app and every `/api/v3/...` route; it imports module 05's
`predictive/` package into itself via a `sys.path` insert. Module 05 has no server
of its own. **No new service was created** — this pass only corrected documentation
that described the relationship backwards.
**Launch command — verified broken, then fixed in documentation:** the previously
documented command,
```
cd modules/04_physics_engine/api && python -m modules.04_physics_engine.run_server
```
was actually run and fails with `ModuleNotFoundError: No module named 'modules'`
(no `modules/__init__.py` exists anywhere, so `modules` only resolves as an
implicit namespace package when the current working directory is the repo root —
which that command's own `cd` moves away from). The module's own `run_server.py`
docstring says plainly: `Usage: python run_server.py → Start server at
http://localhost:8003`. That simpler form was tested from
`modules/04_physics_engine/` directly and works cleanly (cold start to
`Application startup complete` in under 3 seconds).
**Fix:** [README.md](../README.md)'s run instructions replaced with the verified
working command and an explanation of why the old one fails.
**Files changed:** `README.md` only — no application code changed for this item.

---

## 2. Real bugs found and fixed while verifying live traffic

These were found by actually clicking through the running app in a browser, not by
re-reading source — exactly the failure mode static analysis can't catch.

### 2.1 Module 04's `/predictive/alerts/{well_id}` 404'd for real (slash-containing) well IDs
**Found:** loading `/app` in a real browser produced two real console errors:
`Failed to load resource: the server responded with a status of 404
@ http://localhost:8003/api/v3/predictive/alerts/15/9-F-12`.
**Root cause:** `modules/04_physics_engine/api/server.py` declared this route as
`@app.get("/api/v3/predictive/alerts/{well_id}")`. FastAPI's default path-parameter
type does not match a literal `/` inside `{well_id}`, so real well IDs like
`15/9-F-12` never matched the route at all — the exact same bug class that
`logger/11_NWIS_BACKEND_VISUALIZATION_READINESS_AUDIT.md` had already found and
fixed in 12 of module 02's routes, but which was never applied to this one route in
module 04.
**Fix:** [modules/04_physics_engine/api/server.py:511](../modules/04_physics_engine/api/server.py#L511)
— path parameter changed from `{well_id}` to `{well_id:path}`, matching module 02's
established fix pattern exactly.
**Data/API contract affected:** none for well IDs without a `/`; well IDs containing
`/` now resolve correctly instead of 404ing. No response shape change.
**Verified:** server restarted cold; `curl -H "X-API-Key: ..."
"http://127.0.0.1:8003/api/v3/predictive/alerts/15/9-F-12"` returned `[]` (200,
empty list — correct, no active alerts) instead of `{"detail":"Not Found"}`; the
no-slash control case (`WELL-NHK-001`) still returns `[]` correctly (no
regression); reloading `/app` in the browser went from 2 console errors to 0.

### 2.2 Module 04's API key in `frontend/.env` didn't match the actual running server
**Found:** while verifying module 04's authenticated endpoints directly (not
discoverable from static `.env.example` comparison, since both files' *placeholder*
values are empty by design — this only surfaces by actually running the server and
reading the real generated key).
**Root cause:** `modules/04_physics_engine/.env`'s auto-generated `NWIS_API_KEY`
did not match `frontend/.env`'s `VITE_M03_API_KEY` — every module-04/05 call from
the frontend (SimulatorPage, AlertsAdvisoryPage, Dashboard's physics-status polling)
would have silently 401'd.
**Fix:** `frontend/.env` → `VITE_M03_API_KEY` updated to module 04's actual
`NWIS_API_KEY` value.
**Files changed:** `frontend/.env` (not tracked by git).
**Verified:** `curl -H "X-API-Key: <corrected key>"
http://127.0.0.1:8003/api/v3/predictive/models` returned the real 3-model list
(`baseline_hazard_rules` ACTIVE, `isolation_forest_anomaly` and
`xgboost_hazard_classifier` both honestly `UNFITTED_FALLBACK`) instead of a 401.

### 2.3 Evidence PDF citation 400'd for real Volve events with a Windows path baked into the filename
**Found:** clicking a real incident citation on the Offset Map page
(`/app/offset-map`) for well `15/9-F-1` produced:
`Failed to load resource: the server responded with a status of 400
@ http://localhost:4100/evidence?name=volve%5CWELL-15_9-F-1_MUD_LOG.pdf` (`%5C` =
URL-encoded backslash).
**Root cause:** `real_data/real_events_depth_tagged_fresh.json`'s `source_document`
field for real Volve events was generated on a Windows machine with a relative
path prefix baked in (e.g. `volve\WELL-15_9-F-1_MUD_LOG.pdf`) instead of a bare
filename. `evidence-server/index.js`'s own path-traversal guard correctly rejects
any `/` or `\` in the requested name (this is the server working as intended, not
a bug in it), so the raw value always 400'd. The vendored
`nwis-map-package`-derived `WellDetailPanel`/`EvidenceViewer` components (used
unchanged, per their own header comments — explicitly out of scope to modify this
pass) pass this field straight through as-is.
**Fix, at the real-data boundary rather than in the vendored components or the
committed source JSON:** added a small `basenameOf()` helper in
[frontend/src/pages/NwisMapPage.tsx](../frontend/src/pages/NwisMapPage.tsx) that
strips any `/`- or `\`-delimited directory prefix before handing the document name
to `EvidenceViewer`.
**Files changed:** `frontend/src/pages/NwisMapPage.tsx` only. `evidence-server/`,
`nwis-map-package/`, and `real_data/*.json` were **not** modified — consistent with
the instruction to keep the real-data layer and the vendored package untouched.
**Data/API contract affected:** none — `source_document` itself is unchanged in
the data; only the value sent to evidence-server's `?name=` query is normalized.
**Verified:** reloaded the Offset Map page, selected well `15/9-F-1`, clicked the
"Daily drilling report · 15/9-F-1 · 30 m · p.1" citation — network log shows
`GET http://localhost:4100/evidence?name=WELL-15_9-F-1_MUD_LOG.pdf → 200 OK`; 0
console errors.

---

## 3. Placeholder/health-indicator fixes (task §8)

### 3.1 Dashboard's hardcoded-green backend status dots replaced with the real check
**Issue:** `DashboardPage.tsx` rendered three status dots that were always
`bg-emerald-400` regardless of actual backend health — `BackendStatusStrip.tsx`'s
own header comment already called this out explicitly as a known contrast
("unlike DashboardPage's equivalent strip, which hardcodes green for modules
01/02 regardless of actual health").
**Fix:** replaced the hardcoded block in
[frontend/src/pages/DashboardPage.tsx](../frontend/src/pages/DashboardPage.tsx)
with `<BackendStatusStrip />` — the same component `CommandCenterPage` already
uses, per the task's explicit instruction to reuse the existing mechanism rather
than duplicate health-check logic.
**`BackendStatusStrip.tsx` itself was extended**, not duplicated: it previously
checked only modules 01/02 and hardcoded module 03 as permanently "not wired"
(`Dot ok={false}`, dead gray). Added a third real check using `api.getSimStatus()`
(a real, auth-gated module 04 endpoint) as a liveness probe, since module 04/05
have no dedicated `/api/v3` health route of their own. The label was corrected
from "Module 03 · Physics Twin (not wired)" to "Module 04/05 · Physics +
Predictive (8003)", matching the real architecture (§1 of `AUDIT/01_CODEBASE_MAP.md`).
**Explicitly not done:** no fake "fitted" status was invented — the strip reports
process liveness only; whether the ML models underneath are fitted remains visible
only via `/api/v3/predictive/models`' honest `UNFITTED_FALLBACK` status, exactly
as the task instructed ("do not manufacture trained models, fake prediction
values, or fake model metrics").
**Files changed:** `frontend/src/pages/DashboardPage.tsx`,
`frontend/src/components/commandcenter/BackendStatusStrip.tsx`.
**Verified:** loaded `/app` in a real browser, inspected the three status dots'
actual computed CSS classes via a Playwright script — all three
`bg-emerald-400` (real, all three backends genuinely healthy at the time of
the check), not hardcoded.

### 3.2 DashboardPage's internal navigation links — confirmed broken, then fixed
**Confirmed live, not assumed:** navigated to `/app`, clicked the "Full
Cross-Section" link (intended destination `/app/correlation`) — the app silently
redirected to `/app` instead, because the link's `href` was the un-prefixed
`/correlation`, which the route table doesn't recognize, so React Router's
catch-all (`<Route path="*" element={<Navigate to="/app" replace />} />`) caught
it.
**Fix:** [frontend/src/pages/DashboardPage.tsx](../frontend/src/pages/DashboardPage.tsx) —
5 `<Link to="...">` targets corrected: `/alerts`→`/app/alerts`,
`/correlation`→`/app/correlation`, `/wells`→`/app/wells`, `/drilling`→`/app/drilling`,
`/risk`→`/app/risk`. Confirmed via `grep` that no other un-prefixed internal link
exists anywhere else in `frontend/src/`.
**Verified:** re-tested all 5 links in a real browser after the fix — each one now
lands on its correct destination URL (`http://localhost:5173/app/correlation`,
`/app/wells`, `/app/drilling`, `/app/risk`, `/app/alerts` respectively).

### 3.3 RiskPredictionPage — confirmed untouched
Per the task's explicit instruction not to turn illustrative figures into fake
"measured" metrics: verified live in the browser that the
"(illustrative — not measured)" labels on `featureImportances`, ROC-AUC/PR-AUC,
lead time, and inference latency are still present and intact. No changes made to
this page.

### 3.4 LiveDrillingPage / SimulatorPage fallback constants — left as-is, documented
Per the task's instruction to distinguish "necessary, intentionally demo-only"
fallbacks from cases where a real source could replace them: module 04's real
server is in fact reachable now (the key/route fixes above make it so), but its
telemetry stream (`/api/v3/physics/stream` WS, `/physics/status`) only produces
non-trivial values once a simulation is actually started (`POST
/api/v3/physics/start`) — by default `is_running: false`, `md_m: 2500.0` (the
configured initial depth). The numeric fallback constants in `SimulatorPage.tsx`
(e.g. `telemetry?.ecd_gcc || 1.29`) activate only in that same idle state and are
clearly presented as a connected-but-idle simulator, not as misrepresented live
data — no change made, consistent with "do not silently label those values as
live" already being true before this pass.

---

## 4. Documentation corrections (no functional code change)

| File | What was wrong | What it says now |
|---|---|---|
| `README.md` | Ports 8011/8012; broken module 04 launch command; module 04/05 relationship backwards | Ports 8001/8002/8003; verified working module 04 command; corrected module 04/05 relationship with a pointer to this file and `AUDIT/01_CODEBASE_MAP.md` |
| `frontend/src/services/api.ts` | Stale `:8012` default; stale "module 03 has no FastAPI routes exposed yet" comment | `:8002` default; corrected comment describing the real module-04-hosts-module-05 architecture and the `UNFITTED_FALLBACK` ML status |
| `frontend/src/vite-env.d.ts` | Stale `:8012` doc-comment; "NOT YET WIRED"/"no auth wired up" claims for module 03 | `:8002`; corrected to describe the real, running, auth-enforcing module 04/05 server |
| `frontend/.env.example` | Referenced nonexistent `modules/03_physics_engine/`; said module 03 "has no FastAPI routes exposed yet" | Describes the real module 04/05 relationship and the honest `UNFITTED_FALLBACK` ML status |
| `frontend/src/pages/SystemStatusPage.tsx` | Hardcoded `:8012` in both a user-facing error message and a display label | Both corrected to `:8002` |
| `frontend/src/components/commandcenter/BackendStatusStrip.tsx` | Hardcoded `8011`/`8012` labels (display only — the actual `api.ts` calls were already correct) | Labels corrected to `8001`/`8002`/`8003`; module 03 label corrected from a permanent "not wired" placeholder to a real, polled health check |

---

## 5. Module 01 end-to-end flow — verified beyond `/health`

Per the task's explicit instruction not to stop at a health check: a real PDF
(`modules/01_document_intelligence/data/sample_docs/synthetic_oil_india_ddr.pdf`,
module 01's own native-text test fixture) was uploaded through the running
DocumentIngestionPage UI in a real browser.

**Observed, live:** upload → `POST /api/v1/ingest` → job created
(`JOB-1908...`) → status polling → `COMPLETED` → `1 page | 3 events | Confidence:
99.0%` → full extraction result rendered in the UI, including a real formation-tops
table (e.g. "Girujan Clay" lithology row with its own confidence score). Zero
console errors across the entire upload-to-render cycle.

This confirms the full chain — frontend → module 01's real ingest endpoint → the
real 6-layer pipeline → real job store → real result JSON → frontend rendering —
works end-to-end with the corrected port configuration (§1).

---

## 6. Module 02 feature-by-feature status

Tested directly via authenticated `curl` calls (using the real `.env` key) and/or
through the pages that exercise them in a live browser session.

| Feature | Frontend | Backend | Data Source | Status | Evidence |
|---|---|---|---|---|---|
| Active Well | Header/sidebar well selector | `GET /api/v2/wells` | 12 synthetic + 2 real Volve wells | **CONNECTED** | Selector shows real well list incl. `15/9-F-12`, `15/9-F-1`; confirmed via DashboardPage network trace |
| Nearby Wells | NearbyWellsPage, NwisMapPage | `GET /api/v2/offset_rank/{id}`, `/map/wells` | Real DORS engine over live store | **CONNECTED** | Live 200s observed in browser network log; real ranked results (e.g. F-1 at 0.0 km from F-12) |
| Well Details | CommandCenterPage, WellDetailPanel | `GET /api/v2/wells/{id}`, `/trajectory/{id}` | Live store | **CONNECTED** | Real TD/field/type rendered for `15/9-F-1` (3632 m, Volve, J-Type) |
| Events | NwisMapPage, HistoricalIntelligencePage | `GET /api/v2/events/{id}`, `/events/search` | 44 events (synthetic + real Volve, depth-tagged) | **CONNECTED** | Real per-depth incident list rendered with real citations; search_mode confirmed `"semantic"` live |
| Formation/Depth | GeologicalCorrelationPage, header strip | `GET /api/v2/formations/{id}`, `/stratigraphic_depth_track/{id}` | 106 formation tops | **CONNECTED** | Header shows real "Porous Sandstone, ξ: 0.250" computed from two real API numbers |
| Correlation | GeologicalCorrelationPage | `GET /api/v2/corridors/{id}` | Real risk-corridor engine | **CONNECTED** | curl returns 5 real corridors with contributing wells/events |
| Knowledge/Search | HistoricalIntelligencePage, CopilotPage | `GET /api/v2/events/search` | sentence-transformer semantic search | **CONNECTED** | `search_mode: "semantic"` confirmed live, not keyword fallback |
| Document Ingestion | DocumentIngestionPage | Module 01 `/api/v1/*` | Real 6-layer pipeline | **CONNECTED** | Full upload→result cycle verified live (§5) |
| Risk | RiskPredictionPage | n/a (page uses only illustrative constants + module 03 context) | Hand-written illustrative figures | **SIMULATED** (explicitly labeled, untouched per instructions) | "(illustrative — not measured)" confirmed still present |
| Alerts | AlertsAdvisoryPage | Module 04 `/api/v3/predictive/alerts/{id}` | Real risk-fusion engine, rule pillar active, ML pillars UNFITTED_FALLBACK | **CONNECTED** (fix 2.1/2.2 applied) | curl + browser both confirm 200s after the two module-04 fixes |
| Physics | LiveDrillingPage, SimulatorPage | Module 04 `/api/v3/physics/*` | Real ODE physics engine | **CONNECTED**, idle by default | `/health` shows `is_running: false` until a sim is started; not a bug, matches engine design |
| Predictive | SimulatorPage, AlertsAdvisoryPage | Module 04/05 `/api/v3/predictive/*` | Rule engine ACTIVE; isolation forest + XGBoost UNFITTED_FALLBACK | **PARTIAL** (honestly reported, not fixed — no trained models were created, per instructions) | `/api/v3/predictive/models` confirmed live |
| Evidence PDFs | NwisMapPage | evidence-server `:4100/evidence` | 42 real PDF files (39 synthetic DDR + 3 real Volve) | **CONNECTED** (fix 2.3 applied) | Real PDF fetched and confirmed valid (PDF magic bytes); citation click verified live in browser |

---

## 7. Rate-limit observation (not changed, flagged for awareness)

Module 02's rate limiter (60 requests/60s, `modules/02_nwis_backend/auth.py`
default) was hit repeatedly during this pass's own rapid browser-navigation
testing — a single Offset Map page load fires one `/wells` call plus one
`/events/{id}` call per well (14 wells), and the Dashboard fires 4 calls per
mount. Real 429 responses were observed and are a correct enforcement of an
existing, intentional policy, not a bug — but the combination of a 60-req/60s
default and several pages' per-well fan-out pattern means a real user clicking
quickly between pages could plausibly hit it too. Left unchanged this pass
(changing a security-relevant rate-limit policy is outside today's "wire what
exists" scope and wasn't asked for) — flagged here for whoever next revisits
`modules/02_nwis_backend/auth.py`'s `NWIS_RATE_LIMIT_MAX_REQUESTS` default.

---

## Summary

### 1. Fixed
- Module 01 port mismatch (`frontend/.env`: 8011 → 8001), verified by actually
  running module 01 and completing a full document-ingestion flow through it.
- Module 02 port standardized on its documented default (8002) everywhere
  (`frontend/.env`, `api.ts`, README, SystemStatusPage, BackendStatusStrip),
  verified by actually running it cold with no conflict.
- Module 04's `/predictive/alerts/{well_id}` 404 for slash-containing well IDs —
  fixed with the same `{well_id:path}` pattern module 02 already used elsewhere.
- Module 04's API key mismatch between `frontend/.env` and the actual running
  server — found only by running both sides and comparing real values.
- Evidence PDF citation 400s for real Volve events (Windows path prefix in
  `source_document`) — sanitized at the app-code boundary, vendored components
  and source data left untouched.
- DashboardPage's 5 broken internal navigation links (missing `/app` prefix) —
  confirmed broken live in a browser, then fixed and re-verified live.
- DashboardPage's hardcoded-green backend status dots — replaced with the
  existing real `BackendStatusStrip` component (extended to cover module 04/05
  too, as a liveness check only — no fake "fitted" status invented).
- Module 04's documented-but-broken launch command — replaced with the verified
  working one in `README.md`.
- Several stale port/architecture claims in code comments and docs (§4).

### 2. Connected
Active Well, Nearby Wells, Well Details, Events, Formation/Depth, Correlation,
Knowledge/Search, Document Ingestion, Alerts (rule pillar), Physics (idle by
default), Evidence PDFs — all verified with a real running backend and, for the
frontend-facing ones, a real browser session with 0 console errors.

### 3. Still broken
Nothing known. Every integration point this pass set out to verify (task §§2–9)
was either confirmed already working, or found broken and fixed and re-verified
live. See §7 for a non-blocking rate-limit friction point, not a break.

### 4. Still simulated
- RiskPredictionPage's feature-importance/performance figures — explicitly
  labeled "(illustrative — not measured)", untouched per instructions.
- Module 04's physics telemetry is idle (not actively streaming non-trivial
  values) until a simulation is explicitly started via the Simulator page —
  this is the engine's real designed idle state, not a fake value.
- Live Replay (module 02's SSE endpoint) continues to simulate bit-depth
  progression through real stored data, as designed and already documented.

### 5. Still unwired
- `database/` (Postgres/PostGIS/pgvector/TimescaleDB) — confirmed still
  completely disconnected from live code, per explicit instruction not to
  migrate storage this phase.
- Module 02 ↔ Module 05's alert/advisory engine — still no direct integration;
  module 05's alerts remain reachable only via the frontend's module-03/04
  client, not through module 02. Left alone per explicit instruction not to
  redesign this relationship this phase.
- `nwis-map-package/`'s own standalone dev server (port 5180) and Express
  server (port 4000 default) — still standalone/vendored-only; the live app
  uses its copied-in components plus the separately-running `evidence-server/`,
  as already established before this pass.
- Isolation forest / XGBoost trained model artifacts — still absent; both
  pillars still run `UNFITTED_FALLBACK`, honestly reported, by explicit
  instruction not to manufacture training data or models this phase.

### 6. Architectural decisions deferred
- Whether to formalize module 04/05 into separate deployable services, or keep
  the current sys.path-import-into-one-process design, is unchanged and
  undecided — this pass only made the existing design explicit and correctly
  documented, per instructions.
- Whether/how to raise or restructure module 02's rate limit given its pages'
  real per-well fan-out pattern (§7) — flagged, not decided.
- Whether `database/`'s schema should eventually replace the in-memory/SQLite
  storage — explicitly out of scope this phase.
- Whether to retrain hazard-prediction models on more real data, or adopt the
  already-trained-but-unwired `real_data/real_trained_models/*.joblib` files
  (see `AUDIT/01_CODEBASE_MAP.md` §12/§14) — explicitly deferred; no model was
  trained, swapped, or fabricated this pass.

### 7. Next recommended phase
With the core frontend↔backend wiring now verified end-to-end and the two
real runtime bugs (module 04's routing, the evidence-server filename bug)
fixed, the next highest-value work is either (a) deciding whether to wire
`real_data/real_trained_models/*.joblib` into `hazard_predictor.py` — a small,
well-scoped change with a clear real-data benefit, now that the rest of the
stack is confirmed stable underneath it — or (b) beginning the Phase 4 (3D
frontend) planning, since the application underneath it is now confirmed
coherent and runnable. Both are genuine next steps, not emergencies; nothing
found this pass blocks either one.
