# 16 — Deployment Guide (Backend → Render, Frontend → Vercel)

Written for someone who has never deployed this project before. Every
step below was verified against the actual repository during this pass —
not copied from a generic template. Costs are stated plainly; this guide
targets the **free tier of both platforms**, with the one honest
exception documented in §3 (Database).

## 0. What you're deploying

- **Backend** — one FastAPI process (`Backend/run.py`) serving document
  intelligence, well/geospatial intelligence, physics simulation,
  predictive analytics, and evidence delivery, all on one origin. Deploys
  to **Render** as a Docker web service.
- **Frontend** — a Vite/React SPA plus two static marketing pages
  (`public/landing/`). Deploys to **Vercel**, which builds and serves it
  natively (no Docker needed on this side).
- **Database** — PostgreSQL + PostGIS + pgvector + TimescaleDB. Read §3
  before assuming this is free — it genuinely is not, on a managed host,
  without a specific workaround explained there.

## 1. Before you start — env files

This project has exactly **two** env files, consolidated this pass (there
used to be five more, one per module — all deleted; nothing in the active
code path reads them anymore):

| File | Purpose | Template |
|---|---|---|
| `Backend/.env` | Everything the backend reads | `Backend/.env.example` |
| `frontend/.env` | Everything the frontend reads | `frontend/.env.example` |

Both `.env` files are git-ignored. Both `.env.example` files are
committed and kept accurate — copy, don't guess. If you ever see a
`modules/*/.env` file again, it's stale; delete it (confirmed this pass
that nothing in the running app loads any file under `modules/`).

## 2. Deploy the backend to Render

### 2.1 Push the repo to GitHub
Render deploys from a GitHub repo. If this project isn't already on
GitHub, create a repo and push it — `Backend/.env` and `frontend/.env`
will not be included (`.gitignore` already excludes them, confirmed this
pass: no `.env` file is tracked).

### 2.2 Create the service
1. Go to [render.com](https://render.com) → New → Blueprint.
2. Connect your GitHub account and select this repo. Render will find
   `render.yaml` at the repo root automatically and propose one service,
   `nwis-backend`.
3. Click **Apply**. Render builds `Backend/Dockerfile` (build context is
   the repo root — this matters, see the Dockerfile's own header comment:
   the image needs both `Backend/` and `modules/`, which is why the
   context isn't `Backend/` alone).

### 2.3 Set the required environment variables
`render.yaml` deliberately leaves several variables for you to fill in by
hand (never commit a real API key to a blueprint file):

1. In the Render dashboard, open the `nwis-backend` service → Environment.
2. Set **`NWIS_API_KEY`** to a real secret:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   `NWIS_ENV=production` (already set by the blueprint) makes the app
   **refuse to start** if this is empty — confirmed in
   `Backend/app/core/config.py::startup_security_check()` — so this step
   is not optional once you deploy for real use.
3. Set **`NWIS_CORS_ORIGINS`** to your Vercel frontend's origin once you
   know it (you'll get the exact URL in §4 — come back and fill this in
   after that step, then redeploy). Until then the backend will reject
   browser requests from the deployed frontend with a CORS error — this
   is expected, not a bug, and the fix is exactly this one env var.
4. Set **`NWIS_DATABASE_URL`** to your Supabase project's connection
   string — see §3.2.
5. Set **`GEMINIKEY1`** (and, recommended, `GEMINIKEY2`/`GEMINIKEY3`) to
   API keys from separate free-tier Google AI Studio accounts — see §5.4.
6. Optional: `NWIS_REDUCTO_API_KEY` / `NWIS_EXTEND_API_KEY` if you want
   the Tier 2 cloud-OCR fallback live in the deployed instance. Leave
   blank otherwise — nothing breaks, `/health` just reports it as
   unconfigured.

### 2.4 Verify the deploy
Render shows a build log, then a deploy log. Once live:
```
curl https://<your-service>.onrender.com/health
```
should return `{"status": "healthy", ...}`. If it instead times out or
never finishes starting, see §5 (Known constraints) — this is almost
certainly the free-tier memory limit, not a configuration mistake.

### 2.5 The $PORT binding (already handled)
Render injects its own `PORT` env var and expects the app to listen on
it. This was fixed during this pass
(`Backend/app/core/config.py`): `PORT` now falls back to Render's `$PORT`
automatically when `NWIS_PORT` is not explicitly set, so you do not need
to configure anything extra here — confirmed by reading the fix and
restarting the app locally to verify no regression.

## 3. Database — Supabase (free tier)

### 3.1 What the schema actually needs
`database/schema.sql` requires two PostgreSQL extensions, both free on
Supabase:
- **PostGIS** — `wells.surface_location` and every trajectory station's
  location are `geography` columns; nearby-well radius queries depend on
  this.
- **pgvector** — `event_embeddings.embedding vector(384)` with an HNSW
  index. This table is schema-provisioned for a near-future capability —
  live semantic search (`modules/02_nwis_backend/search/knowledge_search.py`)
  currently computes and caches embeddings in-process at runtime, not via
  this table — but the extension is still required for the column type.

**TimescaleDB is no longer required.** `telemetry_records` was a
hypertable in an earlier pass; it is now a plain table with the same
`(well_id, time)` composite primary key and the same query-performance
index — no application code anywhere calls a Timescale-specific function
(`time_bucket()`, continuous aggregates, retention/compression policies),
so this was a pure infrastructure swap with zero query-logic impact. This
is what makes Supabase's free tier (which doesn't offer TimescaleDB)
viable without any schema compromise.

### 3.2 Set up Supabase
1. Go to [supabase.com](https://supabase.com) → New Project (free tier).
2. In the SQL Editor, enable both extensions once:
   ```sql
   create extension if not exists postgis;
   create extension if not exists vector;
   ```
3. Run `database/schema.sql` against the project (SQL Editor, paste and
   run the whole file, or `psql` with the connection string below) — this
   creates every table/index the app needs. The app does not run
   migrations itself by design (no Alembic, no migration framework, per
   this project's own engineering constraints), so this is a one-time
   manual step.
4. **Use the Shared Pooler (Supavisor) connection string, session mode —
   not the direct connection string.** Supabase's "Connect" dialog shows
   several options; the direct `db.<project-ref>.supabase.co:5432` string
   resolves to an IPv6-only address on the free tier, and Render's network
   has no outbound IPv6 route — confirmed live during this pass: the app
   booted fine but every DB query failed with
   `Network is unreachable` against the IPv6 address, even though the
   credentials and schema were correct. The Shared Pooler is IPv4 on every
   tier and is the right choice anyway for a persistent backend service
   (session mode, not transaction mode — this app holds long-lived pooled
   connections via `psycopg_pool`, not one-shot serverless calls). The
   pooler string has a different shape from the direct one — note the
   `postgres.<project-ref>` user (not bare `postgres`) and the
   `aws-0-<region>.pooler.supabase.com` host (confirmed the region prefix
   is `aws-0`, not `aws-1`, for this project — Supabase's dashboard shows
   the exact value for yours under Connect → Session pooler):
   ```
   postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
   Set this on `NWIS_DATABASE_URL` in both Render and (for local testing
   against the same Supabase instance) `Backend/.env`.
5. Optionally run `database/migrate_seed.py` once against the Supabase
   connection string to load the synthetic + real-Volve testbed data (set
   `NWIS_DATABASE_URL` in your local shell to the same pooler string
   before running it, same script the local Docker setup uses).

### 3.3 Memory mode still works, if you ever want it
`db_is_configured()` returning false (leaving `NWIS_DATABASE_URL` unset)
remains a fully supported fallback — the original, first-class operating
mode this codebase was built around, with every route's DB-backed path
additively layered on top of it. Not the recommended path for "one link,
fully working," but documented here in case Supabase is ever unreachable:
the app still serves the full synthetic + real-Volve catalog from JSON
fixtures, with alert history and document sync-status correctly reporting
`"not_configured"` rather than a silent empty state or a crash.

## 4. Deploy the frontend to Vercel

### 4.1 Import the project
1. Go to [vercel.com](https://vercel.com) → Add New → Project → import
   this repo.
2. Set **Root Directory** to `frontend` (the repo root is not the
   frontend's own root — Vercel needs to know to build from `frontend/`).
3. Vercel auto-detects Vite. Build command and output directory are
   already pinned in `frontend/vercel.json` (`npm run build`, `dist`) —
   confirmed this pass to match `package.json`'s real build script.

### 4.2 Set the environment variables
In the Vercel project's Settings → Environment Variables, add (matching
`frontend/.env.example`):
```
VITE_API_BASE=https://<your-render-service>.onrender.com
VITE_API_KEY=<the same NWIS_API_KEY you set in Render>
```
Leave `VITE_TELEMETRY_WS_URL` / `VITE_EVIDENCE_SERVER` unset — they're
derived from `VITE_API_BASE` automatically; only set them if you
genuinely serve the WebSocket or evidence endpoints from a different
origin, which is not this project's deployment shape.

### 4.3 Deploy
Click Deploy. Vercel gives you a URL like
`https://your-app.vercel.app`. **Go back to Render now** and set
`NWIS_CORS_ORIGINS` to this exact URL (§2.3 step 3), then let Render
redeploy (it does this automatically on an env var change, or trigger it
manually from the dashboard).

### 4.4 The landing page fix (already applied)
`frontend/public/landing/index.html` and `benchmarks.html` are static
marketing pages meant to live at `/` and `/benchmarks`, with the actual
React app living under `/app/*`. In local dev this redirect+base-path
rewrite is handled by a Vite dev-server-only plugin
(`vite.config.ts`'s `landingPageAtRoot()`), which does **not** run in a
production build — confirmed this pass by reading the plugin's own
`configureServer`-only hook. Without a fix, Vercel would have served the
React app's shell at `/` instead of the marketing page, and the landing
pages' own relative asset paths (`assets/css/...`, no leading slash)
would have 404'd even if reached directly. Both were fixed this pass:
- `frontend/vercel.json` now rewrites `/` → `/landing/index.html` and
  `/benchmarks` → `/landing/benchmarks.html` (with `/app/*` still
  reaching the SPA).
- Both landing HTML files now carry a permanent `<base href="/landing/">`
  tag (previously only injected by the dev-only plugin), so their
  relative asset paths resolve correctly under any serving path — Vercel,
  a direct `/landing/` visit, or local dev.
- Verified this pass via `vite build` + `vite preview`: `/landing/index.html`
  and its CSS asset both return real 200s with the fix in place.

## 5. Known constraints — read before you're surprised mid-demo

### 5.1 Backend memory footprint on Render's free tier (512 MB)
Measured directly this pass on the actual running process: the backend
worker's resident memory is **~605 MB** once `sentence-transformers`
(for semantic knowledge search) and `xgboost`/`scikit-learn` (hazard
models) are imported and the embedding model is loaded — comfortably
over Render's free-tier 512 MB limit. This is a genuine resource
constraint, not a bug to fix in this pass.

**What this means in practice**: the app may be OOM-killed by Render on
the free tier, especially right after the first semantic-search request
triggers the embedding model to load (it's lazy-loaded — see
`knowledge_search.py::_get_model()` — so a fresh deploy may start fine
and only hit the ceiling once Historical Search is actually used).

**Honest options, in order of recommendation**:
1. **Accept it for a short demo window** — Render's free tier does allow
   the process to run; it just risks a restart under memory pressure.
   For a timed judge walkthrough where you control exactly which pages
   get clicked, this is a real, zero-cost option — just avoid hammering
   Historical Search repeatedly in the same session.
2. **Upgrade to Render's next paid tier** (more RAM) for the demo window
   only, then scale back down — check Render's current pricing; this is
   the most reliable fix with the least code change.
3. **Make the semantic-search dependency genuinely optional at deploy
   time** (skip installing `sentence-transformers`/`torch` in the Render
   image, keep it in a separate optional requirements file already used
   locally) — a real, scoped engineering task, not done in this pass
   because it risks silently degrading a working feature right before a
   demo without dedicated testing. Listed as a P1 item in
   `AUDIT/15_PRODUCTION_READINESS_ROADMAP.md`.

### 5.2 Render free tier cold starts
A free Render web service spins down after 15 minutes of inactivity and
takes a noticeable number of seconds to wake on the next request. Hit the
`/health` endpoint shortly before a live demo to warm it up.

### 5.3 Docling (Tier 2 OCR) is not installed in the deployed image
`Backend/Dockerfile` installs only `requirements.txt`, not
`requirements-optional.txt` — confirmed this pass that installing Docling
pulls in large transitive ML dependencies (checked: the wheel itself is
tiny, but its dependency tree is not) that would make an already-tight
512 MB budget worse. The app's own `/health` endpoint already reports
this truthfully (`docling: not_installed`) rather than hiding it — this
is existing, correct behavior, not something this pass needs to change.

### 5.4 Agentic Knowledge Copilot & Gemini API (3-key rotation)
The Agentic Knowledge Copilot (`POST /api/v2/agent/chat`) uses a tool-calling
loop backed by Google's Gemini API (`gemini-flash-lite-latest`, the
cheapest flash tier), not a self-hosted model — Render's free tier has no
GPU/persistent-compute budget for that.
- **Configuration**:
  - `GEMINIKEY1`, `GEMINIKEY2`, `GEMINIKEY3` — API keys from three
    separate free-tier Google (AI Studio) accounts. Only `GEMINIKEY1` is
    required; 2 and 3 are optional but recommended, since each account's
    free tier has its own request quota and the orchestrator rotates to
    the next key on a rate-limit (429), auth, or server error (see
    `modules/02_nwis_backend/agent/orchestrator.py`'s
    `_is_retryable_on_another_key()`), roughly multiplying the effective
    free quota by the number of keys configured.
  - `NWIS_GEMINI_MODEL` (default: `gemini-flash-lite-latest`)
  - `NWIS_RATE_LIMIT_AGENT_MAX_REQUESTS` (default: `10` requests/60s)
- **Honest Fallback Behavior**:
  When all configured keys are rate-limited/unreachable, or none are
  configured, the route **never crashes or returns 500**. Instead, it
  automatically executes the deterministic keyword search fallback
  (`mode: "keyword_fallback"`), yielding real offset-well rankings and
  historical incident citations from the database/store.
- **Frontend Transparency**:
  The UI displays an honest mode badge (`AI-Assisted (Gemini 2.5 Flash)` vs
  `Keyword Search Fallback`), strictly adhering to the project's
  zero-hallucination policy.

## 6. Verification this guide's claims were checked against

- Full backend test suite: **287 passed, 1 skipped, 0 failed** (`backend`
  145, `document_intelligence` 27, `nwis` 73, `physics` 23,
  `predictive_analytics` 19) — run this pass with PostgreSQL both up and
  (earlier) down, confirming the memory-mode fallback paths this guide
  describes are genuinely exercised by the test suite, not asserted.
- `cd frontend && npx tsc --noEmit && npm run build` — clean.
- `frontend/public/landing/index.html` and its CSS asset verified
  reachable with real 200 responses via `vite preview` after the base-tag
  fix.
- Backend restarted multiple times this pass with a `netstat`-confirmed
  single listener on the configured port each time, per this project's
  own established restart-verification discipline.
- Live memory measurement of the actual running backend process: 605 MB
  RSS, measured via `Get-Process`, not estimated.
