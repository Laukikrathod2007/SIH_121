# NWIS Unified Backend — production container image.
#
# Build context must be the REPO ROOT (not Backend/), because the unified
# backend imports modules/01_document_intelligence, modules/02_nwis_backend,
# modules/04_physics_engine, and modules/05_predictive_analytics directly
# (see Backend/app/core/config.py's MODULES_ROOT) — none of that source
# tree is duplicated into Backend/, so the image needs both directories.
#
#   docker build -f Backend/Dockerfile -t nwis-backend .
#   docker run -p 8000:8000 --env-file Backend/.env nwis-backend
#
# Render's own build step does exactly this: Dockerfile Path =
# Backend/Dockerfile, Docker Build Context Directory = . (repo root) —
# see AUDIT/16_DEPLOYMENT_GUIDE.md.

FROM python:3.12-slim

# Only the ONE runtime manifest (requirements.txt) is installed — the
# optional capabilities in requirements-optional.txt (docling Tier-2 OCR,
# spacy) are genuinely optional: the app reports them as "not_installed"
# via /health rather than failing, and they pull in large ML dependencies
# this image deliberately does not need for the core product to run.
WORKDIR /app

# System packages needed by psycopg (PostgreSQL client) and pymupdf.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY Backend/requirements.txt ./Backend/requirements.txt
RUN pip install --no-cache-dir -r Backend/requirements.txt

# Now the actual source: the unified gateway AND the four module source
# trees it imports from (see header note above) — nothing else needed at
# runtime (no tests/, no research/, no frontend/).
COPY Backend/ ./Backend/
COPY modules/ ./modules/

# The real-Volve-well data layer that modules/02_nwis_backend/data_store.py
# reads directly off disk (REAL_CASING_DATA_PATH / REAL_FORMATIONS_PATH /
# REAL_EVENTS_PATH / REAL_TRAJECTORIES_PATH) for the in-memory-store fallback
# path specifically -- confirmed missing from this image in a real Render
# deploy (data_store.py's own _read_json() has a safe [] default, so the app
# didn't crash, but silently served 0 real wells/casing/events instead of
# the intended 2 real Volve wells' worth of data). Only the 6 small JSON
# files the code actually reads are copied -- NOT the rest of real_data/
# (source PDFs under real_data/volve/, raw WITSML under real_data/witsml/,
# generator/validation scripts, _tmp_results/) which together are ~130MB of
# build-time-only material this image has no runtime need for.
COPY real_data/real_casing_records_all.json ./real_data/real_casing_records_all.json
COPY real_data/real_formations_fresh.json ./real_data/real_formations_fresh.json
COPY real_data/real_events_depth_tagged_fresh.json ./real_data/real_events_depth_tagged_fresh.json
COPY real_data/real_trajectories_witsml.json ./real_data/real_trajectories_witsml.json

# The 42 DDR PDFs (~29MB) that /api/evidence serves and the frontend's
# evidence viewer deep-links into -- see EVIDENCE_PDF_DIR in
# Backend/app/core/config.py. Missing from the image until now (they sat
# under old/, which is deliberately not copied), which is why a deployed
# /health reported evidence.pdf_dir_reachable: false.
COPY real_data/evidence_pdfs/ ./real_data/evidence_pdfs/

WORKDIR /app/Backend

# Render sets $PORT and expects the app to bind to it; app/core/config.py's
# PORT already falls back to $PORT when NWIS_PORT is unset (see that
# file's own comment) — no extra wiring needed here.
EXPOSE 8000

# NWIS_ENV=production is set via the platform's own env settings (see the
# deployment guide), not baked into the image, so the same image works
# for a local `docker run` (dev mode) and a Render deploy (production
# mode) purely by which env vars are supplied at run time.
CMD ["python", "run.py"]
