"""
NWIS Module 01 — PostgreSQL write-through for the document extraction/review
lifecycle (Pass 4: Persistent Data Flows).

This deliberately does NOT replace module 01's own SQLite job store
(api/job_store.py) or its data/output/*.json result files — those remain
the store module 01's own routes (ingest/status/results/review) read from,
so nothing about module 01's existing behavior changes if the database is
unconfigured. This package adds a second, write-through copy into the
canonical schema (database/schema.sql) so downstream NWIS queries (module
02, future reporting) have one authoritative place to read
documents/review-state/accepted-events from, per task requirement #4 ("the
unified application must not silently serve conflicting versions").

Shares module 02's connection pool (app.modules.nwis.db.connection) rather
than opening a second pool to the same database — there is exactly one
NWIS_DATABASE_URL and one process-wide pool, closed once at shutdown.
"""
