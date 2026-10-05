# NWIS Spatial Visualization

Standalone spatial offset discovery and subsurface viewer. The NWIS provider labels the HGJ testbed as synthetic/demo data and excludes Volve wells. The Volve provider reads its own verified WITSML survey dataset and retains its source well IDs. Providers are separate; no HGJ-to-Volve well mapping is performed.

## Run locally

1. Install Node.js 18 or newer and run `npm install` in this folder.
2. Copy `.env.example` to `.env.local`.
3. Set `SPATIAL_BACKEND_URL` to the chosen backend URL. Leave it blank until you know the intended service; there is no fallback to stale ports. `NWIS_BACKEND_URL` remains supported for Module 02.
4. For protected generic backends, set `SPATIAL_API_AUTH_HEADER` and `SPATIAL_API_AUTH_VALUE` (or `SPATIAL_API_KEY` for `X-API-Key`) in `.env.local`. These values are read by the Vite server proxy only and must never be `VITE_` variables. `NWIS_API_KEY` remains supported for Module 02.
5. The standalone preview defaults to the bundled Volve survey dataset so the workspace shows verified survey paths without a backend. Set `VITE_VISUALIZATION_PROVIDER=nwis` when `SPATIAL_BACKEND_URL` is configured to use the synthetic HGJ testbed. Restart Vite after changing environment values.
6. Run `npm run dev`.

### Earth imagery and Cesium configuration

- The global and field layers use CesiumJS with a WGS84 globe and source-backed well locations. CesiumJS itself is Apache-2.0; Google imagery is optional.
- Without Google credentials, the module uses Esri World Imagery satellite tiles on the globe. If that imagery endpoint is unavailable, it falls back to locally bundled Natural Earth country boundaries. The Cesium credit and imagery-provider attribution remain visible when applicable. Without an ion token or Google 3D tiles, the globe uses ellipsoid elevation rather than implying terrain coverage.
- The field view samples surface height from the active Cesium terrain provider when that provider exposes terrain availability; otherwise the UI reports surface elevation as unavailable. The field uses three original GLB detail tiers: `active_surface_rig.glb` for the active well, `selected_surface_wellhead.glb` for the chosen offset, and `offset_wellhead.glb` for other located candidates. They are anchored to provider well coordinates and clamped to terrain when available; they are representational assets, not surveyed or photographic installations. Their triangle counts are 5,888 / 1,744 / 1,248 respectively. Asset provenance and limitations are documented in `public/models/ATTRIBUTIONS.md`. Rebuild them with `python scripts/build_surface_wellhead.py`.
- Optional photorealistic Google tiles: set `VITE_GOOGLE_MAPS_3D_KEY` in `.env.local`, enable the Map Tiles API and billing in Google Cloud, and restrict the browser key to your development/production HTTP referrers and the Map Tiles API. A `VITE_` value is included in browser code by design; it is not a secret and must not be unrestricted. Cesium's credit display remains on-screen so Google and tile-provider attributions are visible.
- Optional Cesium World Terrain elevation: set `VITE_CESIUM_ION_TOKEN` to a public, origin-restricted ion token. This token is also browser-visible. If absent or rejected, satellite imagery remains available over the ellipsoid.
- No Google or ion key is required for the local survey visualization to run. No rig, terrain model, or well position is synthesized to fill imagery gaps.

Google's current pricing documentation lists 7,000 free monthly billable events for the India Photorealistic 3D Tiles Enterprise SKU; usage beyond the free threshold is billable, and quotas/prices vary by SKU and billing region. Check [Google's India pricing table](https://developers.google.com/maps/billing-and-pricing/pricing-india) and [Map Tiles usage and billing](https://developers.google.com/maps/documentation/tile/usage-and-billing) before enabling it. Tile root requests count toward usage quotas. The module deliberately does not enable Google tiles unless a key is explicitly configured.

The Earth layer and subsurface layer are separate renderers sharing the same active well, radius, offset selection, and provider-normalized records. Cesium handles surface geography, terrain sampling, the anchored representative wellsite model, and camera flights; React Three Fiber handles local underground geometry and the trajectory-following shaded wellbore rendering. The interface cross-fades while Cesium flies below the wellhead and R3F frames the surveyed paths. Google photorealistic coverage is not guaranteed at every well location.

The browser requests `/api/...` on its own origin. Vite forwards those calls only when `SPATIAL_BACKEND_URL` or the legacy `NWIS_BACKEND_URL` is configured and attaches the configured credential server-side. Production hosting must provide an equivalent server-side reverse proxy.

## Data sources and limits

- **NWIS mode:** consumes Module 02 wells and analytical endpoints. The adapter keeps only `WELL-HGJ-*` rows and marks them `NWIS_TESTBED_SYNTHETIC`. Generated testbed trajectories can be rendered only with this synthetic/demo provenance; they are not represented as historical OIL India surveys. Testbed telemetry and related records are not presented as historical field data.
- **Volve mode:** reads `public/data/volve/real_trajectories_witsml.json`, a copy of the verified 22-record Equinor Volve WITSML survey dataset. The provider preserves each exact `well_id`, station values, method, type, and station count. It does not synthesize formation/event/hazard/casing/DORS/telemetry layers.
- **Oil Assam public-location mode:** reads `public/data/assam/documented-wellheads.json`, containing two named locations transcribed from an Oil India environmental submission on India's government environmental-clearance portal (Jaloni GT 15 / Well 314 and Naohalia No. 3 / Well 333). Published DMS positions are converted to decimal degrees; the source does not state a coordinate datum. This provider supplies locations only. It does not supply trajectories, DORS, formations, events, hazards, casing, or telemetry, and these records are never joined to the NWIS testbed.
- The Volve trajectory file contains no wellhead coordinates. Verified coordinates from the explicit Module 02 mapping are available only for the exact F-12 and F-1 survey IDs; other trajectories have no map position until verified metadata is supplied. F-1 survey coverage is partial where the source stations end.
- Radius filtering requires a known coordinate and distance at or inside the selected radius. Unknown distance does not count as nearby.
- MD, TVD, and TVDSS remain separate. The renderer does not extrapolate beyond survey coverage.
- The renderer uses React Three Fiber. The normalized provider output feeds it without source-specific API parsing in the scene.
- Local 3D frame: active wellhead is the origin; X=east, Y=up, Z=north; units are metres scaled uniformly by 0.02. Wellhead coordinates use a local equirectangular ENU conversion. Each survey's EW/NS values are added to its wellhead offset. TVD stays relative to each wellhead; wells are not depth-correlated unless a common datum is available.

## Backend request contract

See [BACKEND_INTEGRATION.md](./BACKEND_INTEGRATION.md) for the source-inspected Module 02 routes, response wrappers, API key flow, and verification limits. The browser must never receive `NWIS_API_KEY`.

For another backend, implement `Offset3DDataProvider` and inject it with the public `SpatialVisualization` component. See [CUSTOM_BACKEND_INTEGRATION.md](./CUSTOM_BACKEND_INTEGRATION.md) for normalized field requirements, provenance, secure proxy guidance, and what must be mapped for a specific backend. Backend routes and response formats cannot be inferred automatically; the renderer stays unchanged once the adapter satisfies that contract.

## Build and API smoke check

Run `npm test` for spatial/provider contract checks and `npm run build` to type-check and build the standalone frontend. `npm run smoke:api` can query a backend explicitly configured by `NWIS_BACKEND_URL`; it requires server-side `NWIS_API_KEY` if auth is enabled and a confirmed `NWIS_TELEMETRY_MD` for depth-required requests. Do not use an unverified local port as a backend target.
