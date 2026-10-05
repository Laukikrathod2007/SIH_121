# SIH 26121 — GIS & Spatial Intelligence: Geodetics, Projections & Trajectories

## 1. Executive Summary
This document designs the geospatial intelligence engine of NWIS. It addresses geodetic datums, Coordinate Reference System (CRS) transformations for Indian basins, PostGIS spatial radius queries, and the Minimum Curvature Method (MCM) for calculating 3D subterranean trajectories from directional survey stations.

---

## 2. Geodetic Datums & CRS Transformations in Indian Operations

Drilling archives in Oil India Limited span over 60 years and utilize multiple conflicting geodetic reference datums:

```
[GEODETIC SYSTEMS IN OIL OPERATIONAL AREAS]
├── Legacy Survey Archives (1950s–1990s):
│   └── Indian Everest 1956 Datum / Polyconic Projection (Old Survey of India topo sheets).
├── Regional UTM Projections:
│   ├── WGS 84 / UTM Zone 45N (EPSG:32645) — Western Assam & Bengal Basin.
│   └── WGS 84 / UTM Zone 46N (EPSG:32646) — Upper Assam (Duliajan, Moran, Naharkatiya) & Arunachal.
└── Modern GPS / Satellite Telemetry:
    └── WGS 84 Geographic Coordinates (EPSG:4326) — Latitude / Longitude in decimal degrees.
```

### Pitfall Avoidance:
Treating Everest 1956 coordinates as WGS84 without transformation introduces a **datum shift error of 150 to 300 meters** on the surface! In closely spaced development drilling, a 200m spatial shift causes software to select the wrong offset wells. NWIS uses standard Proj4/GDAL transformation grids to reproject all coordinates to WGS84 (EPSG:4326).

---

## 3. PostGIS Spatial Radius Query Formulation

To satisfy PS Requirement §Outcome ii (*"interactive map-based visualization within a user-defined radius"*), NWIS utilizes PostGIS geodesic geography calculations:

```sql
-- Retrieve all offset wells within user-defined radius (e.g., 5.0 km) around active well
SELECT 
    well_id, 
    well_name, 
    surface_lat, 
    surface_lon, 
    field_name,
    ST_Distance(
        geom::geography, 
        ST_SetSRID(ST_MakePoint(:active_lon, :active_lat), 4326)::geography
    ) / 1000.0 AS distance_km
FROM wells
WHERE ST_DWithin(
    geom::geography, 
    ST_SetSRID(ST_MakePoint(:active_lon, :active_lat), 4326)::geography, 
    :radius_meters
)
AND well_id != :active_well_id
ORDER BY distance_km ASC;
```

---

## 4. Minimum Curvature Method (MCM) for 3D Wellbore Paths

Directional wellbores are measured at discrete survey stations ($MD, \text{Inc}, \text{Azi}$). The industry-standard **Minimum Curvature Method (MCM)** calculates the smooth 3D trajectory between stations:

```
Station 1: [MD_1, Inc_1, Azi_1] ─── (Circular Arc in 3D Space) ───► Station 2: [MD_2, Inc_2, Azi_2]
```

### Mathematical Formulation:
1. **Dogleg Angle ($\beta$):**
   $$\cos \beta = \cos(\text{Inc}_2 - \text{Inc}_1) - \sin \text{Inc}_1 \sin \text{Inc}_2 \left( 1 - \cos(\text{Azi}_2 - \text{Azi}_1) \right)$$
2. **Ratio Factor ($RF$):**
   $$RF = \frac{2}{\beta} \tan\left(\frac{\beta}{2}\right) \quad (\text{for small } \beta, RF \to 1.0)$$
3. **Displacement Coordinates ($\Delta N, \Delta E, \Delta TVD$):**
   $$\Delta TVD = \frac{\Delta MD}{2} \left[ \cos \text{Inc}_1 + \cos \text{Inc}_2 \right] \times RF$$
   $$\Delta \text{North} = \frac{\Delta MD}{2} \left[ \sin \text{Inc}_1 \cos \text{Azi}_1 + \sin \text{Inc}_2 \cos \text{Azi}_2 \right] \times RF$$
   $$\Delta \text{East} = \frac{\Delta MD}{2} \left[ \sin \text{Inc}_1 \sin \text{Azi}_1 + \sin \text{Inc}_2 \sin \text{Azi}_2 \right] \times RF$$

NWIS executes this calculation dynamically to render 3D wellbore paths, allowing engineers to visualize how offset wellbores converge, diverge, or cross subsurface fault planes relative to the active well.
