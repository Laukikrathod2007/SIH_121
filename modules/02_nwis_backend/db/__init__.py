"""
NWIS Module 02 — Canonical Database Layer (Phase 1 foundation)

API route -> service -> repository -> database (database/schema.sql).

This package is additive: importing it does nothing to the existing
in-memory NWISDataStore, and nothing here is on the import path of any
existing endpoint unless NWIS_DATABASE_URL is actually set (see
connection.py). See database/README.md for the schema this talks to and
why PostgreSQL/PostGIS is authoritative for the migrated vertical slice
(active well -> nearby wells -> well metadata) and not yet for anything
else in this module.
"""
