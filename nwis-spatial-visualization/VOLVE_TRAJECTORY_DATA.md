# Equinor Volve trajectory source

The standalone provider reads [public/data/volve/real_trajectories_witsml.json](./public/data/volve/real_trajectories_witsml.json), copied from `SIH121/real_data/real_trajectories_witsml.json`. The JSON is a 22-record array. Each record retains its exact source `well_id`, `well_name`, `method`, `well_type`, and survey station list. All stations carry `md_m`, `inclination_deg`, `azimuth_deg`, `tvd_m`, `ns_m`, `ew_m`, and `tvdss_m`. The records report the `MINIMUM_CURVATURE` method, so the spatial values are derived from real survey records and are labelled derived, not fabricated.

The provider indexes the source by the exact `well_id`; it does not build a trajectory allowlist from guessed human-readable IDs and does not place survey arrays in React components. It validates identity, station presence, and the seven expected station fields before returning geometry.

| Exact source well ID | Stations | MD coverage (m) | Notes |
|---|---:|---:|---|
| `WELL-15_9-F-1` | 8 | 0–210.696 | Partial survey coverage |
| `WELL-15_9-F-9 A` | 28 | 420.400–1181.034 | Survey stations available |
| `WELL-15_9-F-12` | 438 | 0–3441.290 | Survey stations available |
| `WELL-15_9-F-7` | 51 | 0–1043.956 | Survey stations available |
| `WELL-NO 15_9-F-1 C` | 438 | 0–4094 | Source identity retained verbatim |
| `WELL-NO 15_9-F-11` | 564 | 0–4770 | Source identity retained verbatim |
| `WELL-NO 15_9-F-12` | 212 | 0–3520 | Source identity retained verbatim |
| `WELL-NO 15_9-F-14` | 94 | 0–3750 | Source identity retained verbatim |
| `WELL-NO 15_9-F-15` | 187 | 0–4671 | Source identity retained verbatim |
| `WELL-NO 15_9-F-4` | 87 | 0–3510 | Source identity retained verbatim |
| `WELL-NO 15_9-F-5` | 98 | 0–3792 | Source identity retained verbatim |
| `WELL-NO 15_9-F-7` | 42 | 0–1083 | Source identity retained verbatim |
| `WELL-NO 15_9-F-9` | 25 | 0–1206 | Source identity retained verbatim |
| `WELL-15_9-F-10` | 575 | 0–5300.065 | Survey stations available |
| `WELL-15_9-F-14` | 166 | 0–3729.858 | Survey stations available |
| `WELL-15_9-F-15` | 129 | 0–4075.040 | Survey stations available |
| `WELL-15_9-F-15A` | 80 | 0–3211.785 | Survey stations available |
| `WELL-15_9-F-15B` | 87 | 0–3476.847 | Survey stations available |
| `WELL-15_9-F-15S` | 156 | 0–4042.883 | Survey stations available |
| `WELL-15_9-F-4` | 130 | 0–3484.983 | Survey stations available |
| `WELL-15_9-F-5` | 203 | 0–3761.765 | Survey stations available |
| `WELL-15_9-F-9` | 23 | 0–1048.862 | Survey stations available |

There are 22 records total. The source contains similar-looking `WELL-` and `WELL-NO` names; the provider preserves these exact IDs and does not merge them based on naming similarity.

## Coordinate and layer availability

The trajectory JSON has no wellhead latitude/longitude. An explicit source mapping in Module 02 joins `WELL-15_9-F-12` to well metadata `15/9-F-12` and `WELL-15_9-F-1` to `15/9-F-1`; only those two exact trajectory IDs receive the verified metadata coordinates. Other Volve trajectories have no map location and cannot be positioned in a common field frame yet. No IDs are joined to `WELL-HGJ-*`.

This provider supplies trajectories only. Formations, events, hazards, casing, DORS, and telemetry are unavailable for this dataset through this provider. Any separate layer must be independently verified and joined by an explicit exact-ID mapping before use.

The shared field transform uses the verified wellhead coordinate as the local ENU origin for positioned wells, then adds each survey's own EW/NS offsets. Scene axes are X=east, Y=up, Z=north, with a uniform 0.02 units-per-metre scale; depth is `y = -tvd_m * 0.02` relative to the wellhead. When a wellhead location is absent, the active trajectory can be viewed alone in its local survey frame; an unlocated offset is never assigned a guessed field position. MD is only the along-well interpolation parameter. TVD and TVDSS remain separate values; the renderer does not extrapolate past station coverage.
