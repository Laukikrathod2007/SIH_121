# NWIS real-data path audit

> Historical snapshot only: this audit describes an earlier runtime on `127.0.0.1:8002`. Do not use it as the current backend contract or connect to that port. Current source inspection and in-process endpoint verification are in [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md).

Audit date: 2026-10-01. Scope is the service that answered on `127.0.0.1:8002` at that time and the source repositories then present. No API key was available to that audit, so no protected well records were represented as inspected.

## Live service evidence

`GET http://127.0.0.1:8002/` returned service name `NWIS Backend Intelligence API v2`, status `operational`, docs path `/docs`. `GET /api/v2/health` returned:

```json
{
  "service": "NWIS Backend Intelligence API",
  "version": "2.0.0",
  "status": "healthy",
  "data_store": { "loaded": true, "wells": 12, "events": 39, "telemetry_records": 3600, "active_well_id": "WELL-HGJ-012" },
  "engines": ["DORS", "StratigraphicCorrelator", "RiskCorridorEngine", "4PillarConfidence"],
  "auth": { "status": "enabled", "role": "X-API-Key required on all data/analysis endpoints when enabled", "rate_limiting": { "enabled": true, "max_requests": 60, "window_seconds": 60 } }
}
```

These are claims made by the live health endpoint. Health does not expose record IDs, record provenance, or feature coverage.

### Verified endpoint contracts

| Purpose | Live route | Contract observed from OpenAPI / HTTP |
|---|---|---|
| List wells | `GET /api/v2/wells` | Optional `field`, `status`; requires `X-API-Key` in practice (401 without it). |
| Get one well | `GET /api/v2/wells/{well_id}` | Single path ID in this service's OpenAPI; requires `X-API-Key` in practice. Response body not inspected. |
| Well coordinates | `GET /api/v2/map/wells` | Advertised map-wells route; requires `X-API-Key` in practice. Exact output/coordinate field names not inspectable without auth. Well record endpoint could also carry coordinates, but the protected response is unverified. |
| DORS offsets | `GET /api/v2/offset_rank/{well_id}?depth={m_MD}&radius_km={km}&top_n={n}` | `depth` required, described as current bit depth in m MD; `radius_km` defaults to 25; `top_n` controls result count. |
| Formations | `GET /api/v2/formations/{well_id}` | Advertised; record structure and coverage unverified. |
| Events | `GET /api/v2/events/{well_id}` | Advertised; record structure and per-well coverage unverified. |
| Hazard corridors | `GET /api/v2/corridors/{well_id}?depth={m_MD}` | `depth` required, described as current bit depth in m MD; record structure unverified. |
| Telemetry | `GET /api/v2/telemetry/{well_id}?depth={m_MD}&window={n}` | `depth` is required, number >= 0, described as “Current drill bit depth (m MD)”; `window` optional integer, default 300, “Number of recent records to return”. Exact response structure unverified. |
| Trajectory | `GET /api/v2/trajectory/{well_id:path}` | Not in live OpenAPI; probe returned 404. |
| Casing | `GET /api/v2/casing/{well_id:path}` | Not in live OpenAPI; probe returned 404. |

Protected calls to `/wells`, `/wells/WELL-HGJ-012`, `/map/wells`, `/formations/WELL-HGJ-012`, `/events/WELL-HGJ-012`, `/corridors/WELL-HGJ-012?depth=1000`, and `/telemetry/WELL-HGJ-012?depth=1000` returned HTTP 401 with detail `Missing or invalid X-API-Key header.` The sample `depth=1000` was only a route contract probe; it is not claimed as an observed or real bit depth. Trajectory and casing probes returned 404.

The endpoint contract says telemetry must be requested at a measured depth. The implementation's deeper reason for requiring that query cannot be verified because the live service source is not present here and a response could not be obtained. No active depth should be inferred from health or fabricated to satisfy it. The adapter is explicitly `getTelemetryAtDepth(wellId, md)`; the host/replay should supply a confirmed MD.

## Source inspection and route decision

Workspace-wide source search for the live service title, active ID, auth wording, and `/api/v2/offset_rank` found no implementation of the service answering on port 8002. Its process/source ownership could not be verified from the available workspace or HTTP metadata. Therefore there is no source location to edit for that running service, and adding a route to an unrelated backend would not make its endpoint exist.

The separate `repo03-eRTMAC-NWIS` repository contains real Volve survey ingestion code, but it is not the live `/api/v2` service:

- `repo03-eRTMAC-NWIS/ingestion/witsml.py` parses WITSML survey XML into stations with `md_m`, `tvd_m`, `ns_m`, and `ew_m`.
- `repo03-eRTMAC-NWIS/ingestion/volve.py` parses survey CSV data.
- `repo03-eRTMAC-NWIS/ingestion/schemas.py` defines `SurveyStation` with only those four values (no inclination, azimuth or TVDSS fields in this type).
- `repo03-eRTMAC-NWIS/ingestion/loaders.py` `attach_volve_survey()` converts stations to a 2D surface `LineString` and stores min/max MD and bottom TVD.
- `repo03-eRTMAC-NWIS/backend/app/models/wellbore.py` stores optional PostGIS `LINESTRING` (SRID 4326), not the station collection needed to recover 3D TVD/NS/EW survey samples.
- `repo03-eRTMAC-NWIS/backend/app/routes/wells.py` exposes `/wells`, `/wells/{well_id:path}`, `/similar`, and `/historical-events`; it has no trajectory or casing route. Its `/wells` service returns ID, metadata and longitude/latitude (`backend/app/services/well_service.py`, `backend/app/schemas/well.py`).
- `repo03-eRTMAC-NWIS/ingestion/VOLVE_AUDIT.md` identifies the inspected public-mirror survey `15_9_F_11_A.csv` (324 rows) and says the current 26-row SODIR sample has zero overlap with Volve; the survey stations were parsed but are not persisted in the current DB as per-station 3D data.

This is evidence that survey source material and parser code exist in a different project, not evidence that `WELL-HGJ-012` or any well in the live 12-well service has those survey records. No trajectory route was added: there is no existing live-internal station representation to expose.

Other workspace artifacts were kept separate from the live API evidence. `nwis-map-package/README.md` labels its local wells/events JSON as copied “real demo data” and describes 12 wells/39 incidents; `src/wells-data.json` includes `WELL-HGJ-012` with coordinates, and `src/events-data.json` includes its three event records. Those counts match the live health aggregates, but no API record-level comparison was possible, so these JSON files are not reported as live endpoint response samples and are not wired into the visualization as fallback data. `repo09-eRTMAC-NWIS/prisma/seed.ts` instead generates randomized trajectories and casing rows for its separate demo product; those rows are synthetic and excluded from this real-data path.

## Current service capability matrix

The health endpoint verifies 12 records exist but protected list/single-well responses cannot be read. Individual IDs and capability flags are consequently unknown, not “no” and not “yes”.

| WELL | LOCATION | TRAJECTORY | FORMATIONS | EVENTS | CASING | HAZARDS |
|---|---|---|---|---|---|---|
| `WELL-HGJ-012` (health-reported active ID) | Unknown | Route absent (404) | Unknown | Unknown | Route absent (404) | Unknown |
| Other 11 records (IDs unavailable) | Unknown | Route absent (404) | Unknown | Unknown | Route absent (404) | Unknown |

The table distinguishes endpoint availability from per-well data presence. Event and telemetry totals in health do not identify which wells own those records. The API has no trajectory/casing route at all, so their per-well coverage cannot be queried through the live service.

## Required real-data path

```text
GET /api/v2/wells
  → normalizeWells(actual response) → real IDs / coordinates → field locations

GET /api/v2/offset_rank/{activeWell}?depth={confirmedMD}&radius_km={sharedRadius}
  → existing DORS response → offset order, visibility, prominence, explanation

GET /api/v2/trajectory/{well_id:path} (not currently exposed by live backend)
  → extractTrajectory(actual survey stations) → WellTrajectory state
  → stationToVec3()/surveyPoint(): x=ew_m*0.02, y=-tvd_m*0.02, z=ns_m*0.02
  → Three.js line geometry in the same local coordinate frame

GET /api/v2/telemetry/{well_id}?depth={confirmedMD}&window=300
  → getTelemetryAtDepth(wellId, md) → actual telemetry → currentDepth (MD)
  → positionAtMD(real trajectory, currentDepth) → bit position
```

The geometry mapping is centralized in `src/geometry.ts` (`surveyPoint`, `positionAtMD`, `trajectoryLine`). `src/api.ts` has response adapters (`normalizeWells`, `extractTrajectory`, `loadWellData`, `getTelemetryAtDepth`). MD, TVD and TVDSS remain distinct. However, the current live API lacks the trajectory route and returns 404; no renderer can produce real 3D survey paths from that API until backend station data and a matching route are exposed.

## API key and diagnostics

The live OpenAPI documents optional `X-API-Key`, while protected requests without the header are rejected with 401. The visualization no longer asks the browser to hold or send a key. The Vite same-origin `/api` proxy reads unprefixed `NWIS_API_KEY` from `.env.local` on the server and attaches it upstream. `VITE_NWIS_API_BASE` selects the upstream; restart Vite after changing the file. The secret is not embedded in client bundles. A production server still needs an equivalent server-side reverse proxy; static hosting alone cannot keep an API secret.

`npm run smoke:api` performs actual endpoint probes and prints representative response records, including the active well, a DORS-selected offset, telemetry, formations, events, corridors, trajectory and casing. It reads `.env.local` or process environment and never prints the key. Telemetry/DORS/corridor probes run only if `NWIS_TELEMETRY_MD` is explicitly set to a confirmed MD. In this audit environment, `NWIS_API_KEY` was not provided, so successful protected-data smoke records could not be generated. The actual protected responses are still required before completing the capability matrix and examples.

## Conclusion

Verified live active ID: `WELL-HGJ-012`. Verified count reported by live health: 12. The exact 12 IDs, real record examples, source provenance and per-well capabilities remain unavailable because authorization is required. Trajectory and casing routes are definitively absent. The current standalone 3D module **cannot yet be verified to render real well trajectories from the current backend**.
# Historical snapshot notice
