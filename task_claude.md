We are transforming this repository from a working SIH prototype into a serious, production-shaped product for **SIH Problem Statement 26121: eRTMAC-NWIS / Nearby Wells Intelligence System**.

IMPORTANT:
- This is an IMPLEMENTATION task, not another audit.
- Do not merely describe what should be done.
- Inspect the existing repository and then MODIFY THE CODEBASE.
- Do not ask me for clarification. Make technically defensible decisions from the existing code.
- Preserve functionality that already works.
- Do not rewrite working modules unnecessarily.
- Do not fabricate capabilities or data.
- Do not add fake metrics, fake production telemetry, or fake AI.
- Do not spend time on visual redesign in this pass.
- Do not break the existing frontend routes or currently working APIs.
- After implementation, actually run the relevant services/tests and verify the changes against the running system.

CONTEXT FROM PREVIOUS VERIFIED ENGINEERING WORK

The repository currently has:
- frontend/ → React + TypeScript application
- modules/01_document_intelligence/ → FastAPI :8001
- modules/02_nwis_backend/ → FastAPI :8002
- modules/04_physics_engine/ → FastAPI :8003 and hosts predictive analytics functionality
- evidence-server/ → :4100
- PostgreSQL/PostGIS/pgvector/TimescaleDB infrastructure exists in the repository but is NOT currently the authoritative runtime datastore
- M02 currently relies heavily on in-memory data
- real Volve data exists
- synthetic well/event/telemetry data exists
- document ingestion, semantic search, offset-well intelligence, geological correlation, risk analysis, physics simulation and 3D visualization already work
- real-data-trained STUCK_PIPE and WELLBORE_INSTABILITY model artifacts are now wired and validated
- M02 and M05 risk engines are intentionally independent
- telemetry used by the physics system is simulation, not real OIL India eRTMAC telemetry
- all of the above has already been runtime-verified

The goal of THIS PASS is to establish a real backend foundation so later work can stop depending on ad-hoc in-memory structures.

==================================================
PHASE 1 OBJECTIVE
==================================================

Create the canonical persistent data layer for NWIS.

The application should move toward:

Frontend
   ↓
API
   ↓
Domain/service layer
   ↓
Repository/data-access layer
   ↓
PostgreSQL + PostGIS + pgvector/time-series support

Do NOT migrate every endpoint in this pass.
First build the correct foundation and migrate one representative vertical path to prove it works.

==================================================
1. FIRST INSPECT THE EXISTING DATABASE IMPLEMENTATION
==================================================

Before editing:
- inspect database/
- inspect all SQL/schema/init/migration files
- inspect Docker/database configuration
- inspect existing PostgreSQL/PostGIS/TimescaleDB/pgvector setup
- inspect existing Python dependencies
- inspect M01/M02 models and data structures
- inspect how wells, trajectories, formations, events, casing, documents and telemetry are currently represented
- inspect current IDs and field names
- inspect seed scripts and sample data
- inspect environment/configuration handling

Do not invent a parallel schema if an existing schema can be corrected and reused.

Preserve useful existing schema/data wherever practical.

==================================================
2. DEFINE A CANONICAL NWIS DOMAIN MODEL
==================================================

Create a clear canonical model for at least these entities:

1. Well
2. WellTrajectory
3. Formation
4. DrillingEvent
5. CasingProgram
6. Document
7. DocumentExtraction
8. Evidence
9. TelemetryRecord
10. RiskPrediction
11. ModelVersion
12. AuditLog

Use the repository's existing terminology where possible.

For each entity establish:
- primary key
- external/source identifier where applicable
- relationships
- timestamps
- units
- nullable vs required fields
- provenance/source
- created_at / updated_at where appropriate

Important:
- Do not silently change existing well IDs.
- Support IDs containing `/`, `-`, `_`, etc.
- Preserve real Volve identifiers.
- Distinguish synthetic/simulated/real provenance explicitly.
- Do not mix simulation data and real-source data without a provenance field.

Add an explicit provenance concept such as:

source_type:
  REAL
  SYNTHETIC
  SIMULATED
  IMPORTED
  DERIVED

Use the exact naming convention that best fits the repository, but keep it consistent everywhere.

==================================================
3. DATABASE SCHEMA
==================================================

Implement the schema in the project's actual database technology.

Prefer the existing database stack rather than adding unnecessary dependencies.

The schema must support:

WELLS
- well identity
- field/basin
- operator/source
- latitude/longitude
- metadata
- provenance

TRAJECTORIES
- measured depth
- coordinates
- inclination/azimuth where available
- geometry where appropriate

FORMATIONS
- formation name
- top/bottom depth
- source/provenance

DRILLING EVENTS
- event type
- depth
- severity
- description
- formation
- timestamp/date
- source document/evidence relationship
- provenance

CASING PROGRAMS
- hole section
- casing size
- depth
- cement information where available
- provenance

DOCUMENTS
- filename
- document type
- source
- checksum/hash
- ingestion timestamp
- extraction status
- review status
- provenance

DOCUMENT EXTRACTIONS
- extracted field/entity
- value
- confidence
- extraction method
- page/section reference
- validation status

EVIDENCE
- document
- page/section
- well
- event
- formation
- text/snippet/reference
- provenance

TELEMETRY
- well
- timestamp
- depth
- RPM
- torque
- WOB
- ROP
- pressure
- temperature
- ECD
- flow/fuel/etc. only where supported by existing implementation
- provenance
- source

RISK PREDICTIONS
- well
- hazard
- probability/risk output
- model version
- source
- confidence if actually available
- timestamp
- supporting evidence relationship if available

MODEL VERSIONS
- model name
- hazard
- version
- artifact location/reference
- training source
- metrics
- feature schema/version
- status
- created_at

AUDIT LOGS
- actor/system
- action
- entity
- entity_id
- timestamp
- metadata/context

Do not create fields solely for presentation.

==================================================
4. GEOSPATIAL DESIGN
==================================================

Because this is NWIS and spatial intelligence is core:

- use PostGIS where the existing stack supports it
- represent well locations using proper geographic coordinates
- use a consistent SRID
- do NOT store only ad-hoc lat/lon strings
- add appropriate spatial indexes
- ensure nearby-well queries can eventually use database-side geographic filtering

The canonical distance calculation should be consistent with the Haversine behavior already established in the application.

Do not create a second competing geographic formula.

==================================================
5. TIME-SERIES DESIGN
==================================================

Telemetry must be structured so the existing simulation can later write into the same canonical telemetry store used by future real eRTMAC adapters.

Do not label simulation as live production data.

Provide a clear source/provenance distinction:

SIMULATED telemetry
vs
REAL telemetry

The schema should support indexed time/depth queries.

Use TimescaleDB features only if they already exist and are appropriate. Do not add unnecessary infrastructure just for appearance.

==================================================
6. MIGRATIONS
==================================================

Introduce proper migrations using the repository's existing migration mechanism.

If there is no usable migration mechanism:
- add Alembic for the Python database layer
- configure it correctly
- create an initial canonical migration
- make migrations reproducible from a clean database

Do not rely on:
- manually editing a live DB
- one-off scripts that cannot be replayed
- undocumented SQL

A clean machine should be able to initialize the database deterministically.

==================================================
7. SEED / IMPORT THE EXISTING DATA
==================================================

Build a deterministic seed/import path using existing repository data.

At minimum make it possible to load:
- existing wells
- trajectories
- formations
- drilling events
- casing data
- relevant real Volve records
- existing synthetic records where they are already used by the application

Preserve provenance.

DO NOT duplicate records every time seed runs.

Make ingestion idempotent.

For example:
running seed twice should not create two copies of the same well/event/document.

==================================================
8. DATA ACCESS LAYER
==================================================

Create a clean repository/data-access layer.

Do not allow API routes to directly manipulate database sessions everywhere.

Establish a structure equivalent to:

domain/
repositories/
services/

or whatever architecture best matches the existing repository.

The important separation is:

API route
  ↓
service/business logic
  ↓
repository
  ↓
database

Keep business logic out of raw SQL handlers.

Do not create needless abstractions purely for architecture theater.

==================================================
9. MIGRATE ONE REAL VERTICAL SLICE
==================================================

This pass MUST prove the architecture with one actual working flow.

Choose the core NWIS flow:

GET active well
→ retrieve nearby wells
→ retrieve well metadata

Move this flow to the canonical database.

The representative path should support:

- active well lookup
- nearby well lookup
- geospatial distance filtering
- well metadata retrieval

The existing API response contract should remain compatible with the frontend.

Do not make the frontend understand database internals.

The existing 2D map and 3D globe must continue working.

==================================================
10. RADIUS SEMANTICS
==================================================

Preserve the already-fixed API semantics:

- radius_km may remain a scoring-decay parameter where applicable
- max_distance_km must be the explicit hard geographic filter
- map/wells should support explicit center_well_id + radius_km hard filtering as already established

Do not regress this.

Use database-side geographic filtering for the newly migrated path.

==================================================
11. CONFIGURATION
==================================================

Make database configuration environment-driven.

No secrets in source.

Support at least:

DATABASE_URL

and/or the project's existing DB variables.

Provide a clear development configuration.

Do not destroy the existing local development startup flow.

Make connection failures explicit and readable.

==================================================
12. API SCHEMAS
==================================================

Introduce typed request/response schemas for the migrated endpoints.

Python:
- Pydantic response/request models

Frontend:
- preserve existing TypeScript types
- make types match actual API responses
- eliminate obvious duplicated incompatible definitions if encountered

Do not redesign the frontend yet.

==================================================
13. TESTS
==================================================

Add real tests for the new foundation.

At minimum:

DATABASE
- migration from clean DB
- seed idempotency

WELL
- create/load well
- retrieve by ID
- preserve special-character IDs

GEO
- nearby-well query
- max distance filtering
- correct geographic behavior

API
- active well endpoint
- nearby wells endpoint
- frontend-compatible response

PROVENANCE
- real vs synthetic vs simulated records remain distinguishable

Do not just test imports.

==================================================
14. BACKWARD COMPATIBILITY
==================================================

After implementation:

- existing M01 :8001 should still work
- existing M02 :8002 should still work
- existing M04/M05 :8003 should still work
- evidence-server :4100 should still work
- frontend :5173 should still work
- existing major dashboard routes should still load
- 2D nearby-wells functionality must still work
- 3D globe functionality must still work

Do not modify working UI behavior unless required by the new persistence layer.

==================================================
15. CLEANUP
==================================================

As part of this pass, clean only what is directly related to the foundation:

- duplicate DB configuration
- stale database URLs
- stale schema references
- duplicate model definitions for the same canonical entity
- obvious dead DB initialization paths

Do NOT start a repository-wide dead-code cleanup in this pass.

That belongs in a later hardening pass.

==================================================
16. DOCUMENTATION
==================================================

Create/update concise technical documentation describing:

- canonical database architecture
- entities and relationships
- provenance model
- migration commands
- seed/import commands
- local DB startup
- representative API path
- why PostgreSQL is now the source of truth for the migrated path

Do not write marketing copy.

==================================================
17. VERIFICATION
==================================================

At the end, actually perform verification.

Run:
- backend tests
- database migration
- seed/import
- relevant API tests
- frontend typecheck/build
- actual running services
- browser verification of the affected frontend path if available

Check for:
- startup failures
- SQL errors
- migration errors
- duplicate records
- CORS errors
- contract mismatches
- broken existing routes
- incorrect geographic results

Do not claim "verified" unless you actually ran it.

==================================================
18. FINAL RESPONSE FORMAT
==================================================

When finished, give me a concise engineering report containing:

1. WHAT CHANGED
2. DATABASE ARCHITECTURE
3. CANONICAL ENTITIES
4. MIGRATIONS CREATED
5. DATA IMPORT / SEEDING
6. ENDPOINTS MIGRATED
7. TESTS RUN + RESULTS
8. EXISTING FUNCTIONALITY VERIFIED
9. FILES CHANGED
10. REMAINING TECHNICAL DEBT
11. EXACT COMMANDS TO RUN THE NEW FOUNDATION

Most importantly:

DO THE IMPLEMENTATION NOW.

Do not stop after analysis.
Do not generate a hypothetical plan instead of changing the code.
Do not fabricate successful tests.
Do not hide failures.

The next engineering pass will build on whatever is actually implemented here, so leave the repository in a clean, working state.