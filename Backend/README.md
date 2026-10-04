# NWIS Unified Backend

ONE FastAPI application serving all of eRTMAC-NWIS's backend functionality on
**one port (8000)**: document intelligence (M01), NWIS wells/geology/risk (M02),
physics + predictive analytics (M04/M05), and PDF evidence serving.

## Run it

```bash
cd Backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt                      # runtime
pip install -r requirements-dev.txt                  # + pytest (for tests)
pip install -r requirements-optional.txt             # optional: docling, spacy, rich
cp .env.example .env                                 # set NWIS_API_KEY
python run.py
```

Listens on `http://localhost:8000`. Docs at `/docs`. Liveness `/health`,
readiness `/ready`. In development `run.py` uses auto-reload (watching `Backend/`
and `modules/`); with `NWIS_ENV=production` reload is off and startup fails
unless `NWIS_API_KEY` is set.

Frontend: `cd frontend && npm run dev` (port 5173), with `VITE_API_BASE` and
`VITE_API_KEY` in `frontend/.env`.

## Import architecture

The legacy module directories (`modules/01_document_intelligence`, …) start with
digits and share top-level names (`models`, `api`), so they cannot be imported
directly. They are exposed as **real packages** under `Backend/app/modules/`,
without moving any files:

| Package | Directory it maps to |
|---|---|
| `app.modules.document_intelligence` | `modules/01_document_intelligence` |
| `app.modules.nwis` | `modules/02_nwis_backend` |
| `app.modules.physics` | `modules/04_physics_engine` |
| `app.modules.predictive_analytics` | `modules/05_predictive_analytics` |

Each package's `__init__.py` sets `__path__` to the legacy directory, so
standard import machinery does the rest. All imports inside `modules/` use the
fully-qualified `app.modules.<pkg>.…` names. There is **no** `sys.path`
mutation, no `sys.modules` manipulation, no per-request middleware, and no
dependence on the working directory. Import order does not matter (tested with
five permutations in fresh interpreters). The only code that touches `sys.path`
is standalone launchers/CLIs (`run_server.py`, benchmarks, training scripts),
and only under `if __name__ == "__main__":`.

```
Backend/
  run.py                 startup command
  requirements*.txt      ONE authoritative dependency set
  pytest.ini, run_tests.py
  app/
    main.py              the one FastAPI app, /health, /ready
    core/                config, auth, lifecycle, logging, errors
    integrations/        mount M01 / M02 / M04 routes onto the app
    modules/             package adapters (see table above)
    api/evidence.py      PDF evidence router
  tests/                 unit / contract / integration
```

## Authentication

One implementation in `app/core/auth.py`: `X-API-Key` check plus three sliding-
window rate limiters (ingest 20, general 60, physics 600 requests per 60 s;
override with `NWIS_RATE_LIMIT_*` env vars). The legacy `auth.py` files in each
module re-export the same function objects, so there is no divergent copy.
Responses: 401 missing/invalid key, 403 where the original routes returned it,
429 when rate-limited. Public: `/health`, `/ready`, the evidence router and
the physics WebSocket stream (intentionally unauthenticated, as before).

## Lifecycle

Startup/shutdown live in `app/core/lifecycle.py` (FastAPI lifespan). Nothing
runs at import time. The physics simulation loop is a single named task
(`nwis-physics-sim-loop`) started idempotently and cancelled on shutdown; the
Postgres pool is closed on shutdown. `/ready` reports `physics_sim_loop_running`
and per-module health. If a database is configured but unreachable, DB-backed
routes return 503 (never silently fall back to memory).

## Tests

```bash
cd Backend
python run_tests.py                 # backend suite + each legacy module suite, each in its own process
pytest -m "unit or contract"         # architecture/contract tests only
NWIS_LIVE_INGEST=1 pytest -m integration   # against a running server (ingest writes real data)
```

Integration tests skip when no server is running.

## Known limitations

- Manifest verified in a clean venv on Python 3.14.3 only.
- sklearn model artifacts were trained on 1.9.0 and load with an
  `InconsistentVersionWarning` on 1.9.1.
- The NWIS general limiter (60/min) can return 429 under very rapid UI
  navigation; raise `NWIS_RATE_LIMIT_GENERAL_MAX_REQUESTS` if needed.
- `modules/real_data/*` tools are import-verified but were not executed
  (they write datasets/artifacts).
- Module directories were intentionally not moved; a future pass could
  relocate them into `app/` and drop the adapter packages.
- The old Node evidence server lives in `old/evidence-server/`; its PDFs are
  still served from there (`EVIDENCE_PDF_DIR`).
