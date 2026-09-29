# eRTMAC-NWIS database layer: PostgreSQL + PostGIS + pgvector + TimescaleDB
# in one image. No single official image ships all three, so this builds
# pgvector from source on top of the official TimescaleDB-HA image, which
# already bundles PostGIS + TimescaleDB on PostgreSQL 16.
FROM timescale/timescaledb-ha:pg16-all

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential postgresql-server-dev-16 ca-certificates && \
    git clone --branch v0.7.4 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make && make install && \
    cd / && rm -rf /tmp/pgvector && \
    apt-get purge -y --auto-remove git build-essential postgresql-server-dev-16 && \
    rm -rf /var/lib/apt/lists/*

USER postgres
