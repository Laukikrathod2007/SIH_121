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
