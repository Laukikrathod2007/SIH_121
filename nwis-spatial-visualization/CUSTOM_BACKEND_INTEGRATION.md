# Integrating a different backend

The visualization now depends on `Offset3DDataProvider`, not on NWIS endpoint names or response models. A host can inject an adapter without changing the map, scene, shared selection state, radius calculation, or panels:

```tsx
import { SpatialVisualization } from './nwis-spatial-visualization/src';
import { companyProvider } from './companyProvider';

<SpatialVisualization provider={companyProvider} />
```

`companyProvider` implements the exported `Offset3DDataProvider` interface from `src/data-contract.ts`. This is the only backend-specific integration point. `getWells()` is required; `getWell()` and all engineering layers are optional. Omit unsupported methods and the UI will report those layers unavailable. A successful empty response is different from a missing/failed capability.

For endpoints that can be called through one same-origin request function, `createMappedHttpProvider` (`src/mappedHttpProvider.ts`) provides the adapter shell: configure route builders and response normalizers, then inject the result. This avoids hand-writing repetitive request forwarding while keeping schema conversion explicit.

```ts
const companyProvider = createMappedHttpProvider({
  source: 'OIL_BACKEND',
  provenance: { isVerified: true, isSynthetic: false, isDerived: false },
  request: (path, signal) => fetch(path, { signal }).then(response => {
    if (!response.ok) throw new Error(`Backend request failed (${response.status})`);
    return response.json();
  }),
  endpoints: {
    wells: '/api/wells',
    trajectory: id => `/api/wells/${encodeURIComponent(id)}/survey`,
    // Add endpoints only where this backend provides that capability.
  },
  map: {
    wells: (raw, source) => normalizeCompanyWells(raw, source),
    trajectory: (raw, id, source) => normalizeCompanySurvey(raw, id, source),
  },
});
```

`normalizeCompanyWells` and `normalizeCompanySurvey` are intentionally backend-specific: their field names and units must be based on that backend's real contract.

## Provider mapping

Map the new backend's routes and response fields into these normalized values:

| Provider method | Normalized result | Notes |
|---|---|---|
| `getWells()` | `VisualizationWell[]` | Preserve exact IDs; coordinates must be source coordinates or `null`. |
| `getWell(id)` | `VisualizationWell` | Return the same exact ID requested. |
| `getTrajectory(id)` | `VisualizationTrajectory \| null` | Survey stations preserve MD, inclination, azimuth, TVD, NS, EW and TVDSS. Return `null` only when the source confirms none exists. |
| `getDorsOffsets(id, radiusKm, depthM)` | `VisualizationOffset[]` | Preserve source rank/scores and distance. The UI independently filters by coordinate distance. |
| `getFormations(id)` | `VisualizationFormation[]` | Preserve depth reference and formation names. |
| `getEvents(id)` | `VisualizationEvent[]` | Preserve the source well ID and measured-depth interval. |
| `getHazards(id, depthM)` | `VisualizationHazard[]` | Preserve actual interval and risk level. |
| `getCasing(id)` | `VisualizationCasing[]` | Return only casing records actually supplied. |
| `getTelemetryAtDepth(id, mdM)` | `VisualizationTelemetry[]` | Only real telemetry can drive the bit marker. |
| optional `getHealth()` | health metadata | Omitting it is supported. |

Implemented methods accept an optional `AbortSignal`. Honor it when the backend client supports cancellation. `[]` means the request succeeded and returned no records. Throw an error when the layer could not be fetched; the loader will mark that layer unavailable and retain the error reason. Use `null` for a confirmed missing trajectory. Do not convert a failed request into a successful empty layer.

Set source provenance explicitly for a new dataset:

```ts
export const companyProvider: Offset3DDataProvider = {
  source: 'OIL_BACKEND', // or a stable source label for another data world
  provenance: { isVerified: true, isSynthetic: false, isDerived: false },
  // implement the methods and normalize the backend response here
};
```

For a generated/demo backend, set `isSynthetic: true`. Unknown sources default to unverified, non-synthetic, and non-derived unless the adapter says otherwise. Provenance is propagated to every displayed data layer.

## Secure transport

Do not call a protected backend directly from browser code with a secret key. In development, set `SPATIAL_BACKEND_URL` and, when needed, `SPATIAL_API_AUTH_HEADER` plus `SPATIAL_API_AUTH_VALUE` in `.env.local`. The Vite server forwards same-origin `/api/*` requests and attaches that credential server-side. `SPATIAL_API_KEY` is a convenience alias for the common `X-API-Key` header. Legacy `NWIS_BACKEND_URL` and `NWIS_API_KEY` still work when generic values are unset. Never put credentials in `VITE_*` variables.

Production hosting must provide the equivalent same-origin `/api` reverse proxy or authenticated server session; the Vite proxy is for development/preview only. If the backend uses browser OAuth, use the host's established token/session flow and do not persist long-lived secrets in the visualization. A host may also provide its own `fetch` client inside the adapter.

## Spatial and depth requirements

- Supply actual latitude/longitude before expecting the radius filter, nearby list, globe markers, or common multi-well frame to work. Wells without coordinates remain listed but are excluded from spatial filtering.
- Survey offsets must use metres and the documented east/north convention. `trajectoryGeometry.ts` is the single station-to-scene conversion; MD, TVD and TVDSS remain separate.
- Never combine records across unrelated providers. IDs are exact join keys.
- Only an actual telemetry response can position a bit. `evaluationDepthM` is user context and remains separate from telemetry depth.
- If the backend has no formations/events/hazards/casing endpoint, leave that capability unavailable rather than manufacturing a layer.

## What remains for a specific backend

There is no safe zero-configuration adapter for an unspecified “random backend”: its URL, authentication, route names, units, and response schemas are not known. To connect one, implement its normalizer/provider, configure its same-origin server proxy, and verify representative responses and provenance. Once those are supplied, the renderer itself does not need backend-specific edits.
