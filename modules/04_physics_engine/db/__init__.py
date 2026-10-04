"""
NWIS Module 04/05 — PostgreSQL write-through for simulated telemetry and
predictive alerts (Pass 4: Persistent Data Flows).

Lives under module 04 (not 05) because the one real integration point —
POST /api/v3/predictive/evaluate — is a module 04 FastAPI route (module 05
has no server of its own; module 04's api/server.py imports its
RealTimeRiskInferenceService directly, same pattern as everywhere else in
this codebase).

Shares module 02's connection pool (app.modules.nwis.db.connection) — one
NWIS_DATABASE_URL, one process-wide pool, closed once at shutdown.

Does NOT change the physics engine's equations, the ML models, or the
25 Hz WebSocket broadcast loop. Persistence happens only at the existing
~1 Hz /predictive/evaluate call the frontend already makes (see
frontend/src/context/AppContext.tsx's handleNewTelemetry — it decimates
the 25 Hz stream to ~1 Hz before calling evaluate), so this adds a write
at an already-existing, already-throttled request, not a new high-rate
writer competing with the physics loop for the event loop.
"""
