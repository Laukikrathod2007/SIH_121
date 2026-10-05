# Module 02 visualization integration contract

This document reflects source inspection of `SIH121/modules/02_nwis_backend/server.py`, `data_store.py`, `models/schemas.py`, `auth.py`, and `data/synthetic/generate_testbed.py`. It is not a claim that a particular process or port is currently serving that source. No backend source was modified by the standalone visualization task.

## Current-source verification (2026-10-01)

Module 02 was imported from disk and exercised with an in-process FastAPI `TestClient`; no TCP port or existing backend process was used. The test authenticated using the key already loaded server-side by the app and did not print it.

| Probe | Result |
|---|---|
| `GET /api/v2/health` | 200; active ID `WELL-HGJ-012`; auth enabled |
| `GET /api/v2/wells` without key | 401 |
| `GET /api/v2/wells` with key | 200; 14 total records: 12 generated testbed wells and 2 Volve metadata records |
| `GET /api/v2/wells/WELL-HGJ-012` | 200 |
| `GET /api/v2/offset_rank/WELL-HGJ-012?depth=2136.001` | 200; depth came from the actual loaded telemetry records |
| `GET /api/v2/formations/WELL-HGJ-012` | 200 |
| `GET /api/v2/events/WELL-HGJ-012` | 200 |
| `GET /api/v2/corridors/WELL-HGJ-012?depth=2136.001` | 200 |
| `GET /api/v2/telemetry/WELL-HGJ-012?depth=2136.001&window=5` | 200 |
| `GET /api/v2/trajectory/15%2F9-F-12` | 200; 438 stations, `MINIMUM_CURVATURE` |
| `GET /api/v2/casing/15%2F9-F-12` | 200; 6 records |

The health/source check found 12 generated wells across several field prefixes, of which `WELL-HGJ-010`, `WELL-HGJ-011`, and `WELL-HGJ-012` are the HGJ cluster, plus the two Volve wells. This differs from the earlier runtime claim of 12 total HGJ wells. The standalone HGJ view currently selects the three exact HGJ IDs and does not claim the other nine generated wells are HGJ offsets.

Module 02's inspected source still has no `/api/v2/visualization/capabilities` endpoint or dataset query parameter on `/api/v2/wells`; support and provenance are recorded in this document instead. The default well-list route returns both dataset groups. The standalone provider filters its NWIS view to exact `WELL-HGJ-*` identifiers and uses the local Volve JSON provider for the Volve surveys.

## Authentication and transport

- Data endpoints use `X-API-Key` when `NWIS_API_KEY` is configured in Module 02.
- Browser code calls same-origin `/api/...`. In development, Vite forwards to `NWIS_BACKEND_URL` and adds the key server-side. Do not set `VITE_NWIS_API_KEY` or put a key in frontend JavaScript.
- `GET /api/v2/health` is open in the inspected source. Data routes use API-key and rate-limit dependencies.
- The standalone Vite proxy has no default backend port. Configure a source process explicitly; do not target stale 8002/8012 services.

## Source-inspected endpoints

| Request | Required query | Source response shape used by adapter |
|---|---|---|
| `GET /api/v2/wells` | optional `field`, `status` | `{ total, wells: Well[] }`; well fields include `well_id`, `well_name`, `field`, `field_code`, `operator`, `surface_lat`, `surface_lon`, `kb_elevation_m`, `total_depth_md_m`, `well_type`, `status` |
| `GET /api/v2/wells/{well_id:path}` | none | `{ well, trajectory_stations, formation_tops, total_events }` |
| `GET /api/v2/trajectory/{well_id:path}` | none | `{ well_id, well_name, method, well_type, stations }`; station fields `md_m`, `inclination_deg`, `azimuth_deg`, `tvd_m`, `ns_m`, `ew_m`, `tvdss_m` |
| `GET /api/v2/offset_rank/{well_id:path}` | required `depth` in m MD; optional `radius_km`, `top_n` | `{ active_well_id, depth_m, formation_at_bit, radius_km, total_ranked, rankings, dors_formula }`; ranking includes `dors_score`, `distance_km`, `component_scores` (`spatial`, `formation`, `depth`, `trajectory`, `hazard`, `total`, `distance_km`) |
| `GET /api/v2/formations/{well_id:path}` | none | `{ well_id, total, formation_tops }`; records include `formation_name`, `top_md_m`, `top_tvd_m`, `base_md_m`, `thickness_m`, plus optional interpretation fields |
| `GET /api/v2/events/{well_id:path}` | none | `{ well_id, total, total_npt_hours, events }`; events include `depth_start_md_m`, optional `depth_end_md_m`, `event_type`, `severity`, `formation`, `source_document`, and related narrative/mitigation fields |
| `GET /api/v2/corridors/{well_id:path}` | required `depth` in m MD; optional `hazard_type` | `{ well_id, depth_m, formation_at_bit, total_corridors, corridors }`; corridor depths are `depth_start_m`/`depth_end_m`; `hazard_type`, `proximity_risk_level`, contributing well/event IDs, and recommendations are preserved |
| `GET /api/v2/telemetry/{well_id:path}` | required `depth` in m MD; optional `window` (default 300) | `{ well_id, depth_m, records_returned, latest, records }`; records use `timestamp`, `depth_m`, and sensor fields such as `rop_m_hr`, `wob_klbs`, `rpm`, `torque_kn_m`, flow, pit volume, and mud weight |
| `GET /api/v2/casing/{well_id:path}` | none | `{ well_id, total, casing_records }`; records include `casing_size_inches`, `shoe_depth_md_m`, optional `top_of_cement_md_m` |

The inspected backend source has trajectory and casing routes. The standalone NWIS adapter displays returned HGJ generated trajectories only as `NWIS_TESTBED_SYNTHETIC`; it only draws casing when a record is returned. It filters the NWIS provider to HGJ IDs; Volve trajectories are consumed through the separate local provider.

## Dataset provenance and current limits

- `generate_testbed.py` uses `random.seed(42)` and generates synthetic HGJ wells, survey tracks, formation tops, drilling events, and telemetry. The NWIS visualization labels this dataset synthetic/demo. The only telemetry stream in the generated bundle is tied to the active well; it is not a general live stream.
- `data_store.py` appends two Volve well records to the generated set and loads separate Volve trajectory, formation, event, and casing extracts. The source’s `REAL_TRAJECTORY_KEY` explicitly joins `WELL-15_9-F-12` to `15/9-F-12` and `WELL-15_9-F-1` to `15/9-F-1`. Those are Volve IDs, never HGJ aliases.
- Module 02's trajectory route can return generated HGJ paths. The standalone HGJ provider labels them synthetic/demo and never presents them as verified Volve surveys.
- The corridor endpoint ranks against the store’s well/event set internally. The standalone HGJ adapter retains a corridor only when its `contributing_wells` are all HGJ IDs, preventing Volve event contributions from appearing in the HGJ demo view.
- The source-inspected store reports 12 generated wells plus 2 Volve well records. This differs from the earlier runtime audit reporting 12 total. No stale service was queried to resolve the difference. Check the chosen backend process’s health response before interpreting its totals.
- `NWISDataStore.get_telemetry_at()` selects records by depth and does not scope the query by requested `well_id`; the adapter filters returned records back to the requested well ID. Do not use telemetry from this endpoint as a server-side current-bit state.
- Casing records are loaded from a separate real-data file, not generated HGJ data. The current HGJ provider does not borrow Volve casing.
- Module 02 has no visualization capabilities endpoint in the inspected source. The frontend relies on documented routes and reports per-well missing data as unavailable.

## Required frontend safeguards

1. Never join records across providers by a guessed or sanitized identifier.
2. Use exact source IDs and exact path IDs; preserve slash-containing Volve IDs.
3. Apply `distance_km <= selectedRadiusKm` locally; the DORS radius argument is not treated as proof that every returned candidate is within the UI radius.
4. Show a bit marker only when an actual telemetry depth is returned and lies within an available verified trajectory's MD coverage.
5. Draw a casing shoe marker only from a returned real shoe depth. Do not invent casing interval geometry from a shoe-depth-only record.
