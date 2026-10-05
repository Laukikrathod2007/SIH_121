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
`render.yaml` deliberately leaves two variables for you to fill in by
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
4. Leave **`NWIS_DATABASE_URL`** unset for now unless you've already
   decided on one of the options in §3. The app runs correctly without
   it — see §3.4.
5. Optional: `NWIS_REDUCTO_API_KEY` / `NWIS_EXTEND_API_KEY` if you want
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

## 3. Database — read this before assuming "just add Postgres"

### 3.1 What the schema actually needs
`database/schema.sql` requires three PostgreSQL extensions, all
confirmed load-bearing (not optional) by reading the schema directly:
- **PostGIS** — `wells.surface_location` and every trajectory station's
  location are `geography` columns; nearby-well radius queries depend on
  this.
- **pgvector** — `event_embeddings.embedding vector(384)` with an HNSW
  index. **Confirmed this pass: this table has 45 seeded rows but no
  application code currently reads from or writes to it** — live
  semantic search (`modules/02_nwis_backend/search/knowledge_search.py`)
  actually computes and caches embeddings in-process at runtime, not via
  this table. So pgvector is schema-provisioned for a near-future
  capability, not yet the live search backend. It's still a real
  `CREATE EXTENSION` requirement either way.
- **TimescaleDB** — `telemetry_records` is a hypertable
  (`SELECT create_hypertable(...)`).

### 3.2 Render's managed Postgres does not support these
Render's own managed PostgreSQL offering does not include PostGIS,
pgvector, or TimescaleDB as installable extensions. This is a genuine
platform limitation, not a configuration step you're missing.

### 3.3 Your real options, honestly costed
1. **Self-host Postgres as a second Render Docker service**, using the
   image this repo already has
   (`database/Dockerfile` — `timescale/timescaledb-ha:pg16-all` +
   pgvector built from source, confirmed this pass to already bundle all
   three extensions correctly). **The catch**: Render's free tier gives
   services ephemeral disk only — every redeploy or restart wipes the
   database clean. This is fine for a one-off demo where you accept
   re-seeding, genuinely not fine for anything you want to persist
   across sessions. A Render **paid** instance with a persistent disk
   (starts at a few dollars/month at the time of writing — check Render's
   current pricing) removes this limitation.
2. **A managed provider with the right extensions**: Supabase supports
   PostGIS and pgvector on its free tier but not TimescaleDB (you would
   need to drop the hypertable call and accept `telemetry_records` as an
   ordinary table — a real, if small, schema change, not just a
   deployment setting). Neon supports pgvector but not PostGIS or
   TimescaleDB. Both require adapting the schema, not just pointing
   `NWIS_DATABASE_URL` at them.
3. **Deploy in memory mode (recommended for a free, zero-friction demo)**
   — leave `NWIS_DATABASE_URL` unset entirely. See §3.4.

### 3.4 Memory mode is a fully supported, tested path — not a fallback hack
This is not a workaround invented for this guide: `db_is_configured()`
returning false is the original, first-class operating mode this entire
codebase was built around, and the DB-backed paths were added later as
an *additive* layer on top of it (see `AUDIT/12`/`13`/`14`'s own
documented history). Every route this pass verified has a
parametrized `memory` test case alongside its `postgres` case (287 tests
total, confirmed passing this pass — see §6). Deployed with no database
configured, you get:
- The full synthetic + real-Volve well catalog, trajectories, formations,
  casing, and events (all loaded from JSON fixtures at startup, no
  database needed).
- DORS ranking, stratigraphic correlation, risk corridors, the full
  `/analyze` pipeline — all working, reading from the in-memory store.
- Document ingestion and review still work; approved extractions are
  saved to local JSON files (`data/output/`) instead of Postgres — on
  Render's free tier this is also ephemeral storage, so uploaded
  documents won't survive a redeploy, which is an honest, acceptable
  demo-time tradeoff, not data loss you'd notice mid-demo.
- Alert history and document sync-status both correctly report
  `"not_configured"` rather than a silent empty state or a crash — this
  tri-state honesty was specifically built and tested for exactly this
  situation (see `AUDIT/14` §1.vi).

**What you lose in memory mode**: cross-restart persistence of anything
written at runtime (new alerts, new approved documents, simulator-
generated alert history), and the live pgvector-backed search path once
that's built. Nothing about the seven SIH-required workflows is disabled
or broken.

### 3.5 If you do add a database later
Set `NWIS_DATABASE_URL` on the Render service to the connection string
(or the discrete `NWIS_DB_HOST`/`NWIS_DB_PORT`/`NWIS_DB_NAME`/
`NWIS_DB_USER`/`NWIS_DB_PASSWORD` fields — see `Backend/.env.example`),
then run `database/schema.sql` against it once (the same file the local
`docker-compose.yml` initializes with) before the app's first request
that needs it — the app does not run migrations itself by design (no
Alembic, no migration framework, per this project's own engineering
constraints).

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

### 5.4 Agentic Knowledge Copilot & Local LLM (Ollama)
The Agentic Knowledge Copilot (`POST /api/v2/agent/chat`) uses a tool-calling
loop backed by a local or networked Ollama instance running `qwen2.5:7b-instruct`:
- **Configuration**:
  - `NWIS_OLLAMA_URL` (default: `http://localhost:11434`)
  - `NWIS_OLLAMA_MODEL` (default: `qwen2.5:7b-instruct`)
  - `NWIS_RATE_LIMIT_AGENT_MAX_REQUESTS` (default: `10` requests/60s)
- **Honest Fallback Behavior**:
  Render free tier does not provide the persistent GPU or 4.7 GB RAM needed
  to host a 7B LLM. When Ollama is unreachable at request time, the route
  **never crashes or returns 500**. Instead, it automatically executes the
  deterministic keyword search fallback (`mode: "keyword_fallback"`),
  yielding real offset-well rankings and historical incident citations from
  the database/store.
- **Frontend Transparency**:
  The UI displays an honest mode badge (`AI-Assisted (Ollama / Qwen-2.5)` vs
  `Keyword Search Fallback`), strictly adhering to the project's
  zero-hallucination policy.
- **Cloud LLM Hosting**:
  To enable the full LLM agent in production, point `NWIS_OLLAMA_URL` to a
  dedicated host (e.g. RunPod, GPU instance, or Ollama cloud container).

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
