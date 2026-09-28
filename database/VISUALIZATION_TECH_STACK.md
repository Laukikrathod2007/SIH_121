# NWIS 3D Visualization Technology Stack

## Executive Summary

For visualizing drilling operations in 3D (including subsurface formation layers and well trajectories), I recommend a **dual approach**:

---

## Approach 1: Web-Based 3D Visualization (Recommended for Module 2)

### Primary Technology: **Cesium.js + deck.gl**

#### **Cesium.js** - For 3D Geospatial Rendering
[https://cesium.com/platform/cesiumjs/](https://cesium.com/platform/cesiumjs/)

**Why Cesium?**
- ✅ **3D Globe with Terrain** - Visualize wells on actual earth surface with elevation
- ✅ **Subsurface Rendering** - Can render underground geometries
- ✅ **Time-Series Animation** - Replay drilling progress over time
- ✅ **PostGIS Integration** - Direct support for geospatial data
- ✅ **Open Source** - Free for commercial use
- ✅ **WebGL-Based** - Runs in browser, no installation needed

**Cesium Features for NWIS:**
```javascript
// 1. Well location markers
viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(95.62, 27.38, 0),
    point: {
        pixelSize: 10,
        color: Cesium.Color.RED
    },
    label: {
        text: 'Well DG-003',
        font: '14pt monospace'
    }
});

// 2. Well trajectory (drill path)
const wellPath = Cesium.Cartesian3.fromDegreesArrayHeights([
    95.62, 27.38, 0,      // Surface
    95.62, 27.38, -1000,  // 1000m depth
    95.63, 27.39, -2000,  // 2000m depth (directional)
    95.64, 27.40, -3000   // 3000m TD
]);

viewer.entities.add({
    polyline: {
        positions: wellPath,
        width: 5,
        material: Cesium.Color.YELLOW
    }
});

// 3. Formation layers (colored volumes)
viewer.entities.add({
    polygon: {
        hierarchy: formationBoundary,
        height: -1000,        // Top of formation
        extrudedHeight: -1500, // Bottom of formation
        material: Cesium.Color.ORANGE.withAlpha(0.7),
        outline: true,
        outlineColor: Cesium.Color.BLACK
    }
});
```

#### **deck.gl** - For Data-Driven Overlays
[https://deck.gl/](https://deck.gl/)

**Why deck.gl?**
- ✅ **High-Performance** - Can render millions of data points
- ✅ **2D/3D Layers** - Switch between map and 3D views
- ✅ **GeoJSON Support** - Easy PostGIS integration
- ✅ **React Integration** - Works seamlessly with React apps

**deck.gl Layers for NWIS:**
- `ScatterplotLayer` - Well locations with color-coded status
- `LineLayer` - Well trajectories
- `PolygonLayer` - Formation boundaries
- `HeatmapLayer` - Drilling activity intensity
- `ArcLayer` - Offset well connections

### Database to Visualization Pipeline

```
PostgreSQL/PostGIS
      ↓
FastAPI REST Endpoint
      ↓  (GeoJSON format)
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [95.62, 27.38]
      },
      "properties": {
        "well_name": "DG-003",
        "status": "drilling",
        "depth": 2500
      }
    }
  ]
}
      ↓
Cesium.js / deck.gl
      ↓
Browser Rendering
```

---

## Approach 2: Offline 3D Modeling (For High-Fidelity Presentations)

### Primary Technology: **Blender + Python API**

#### **Blender** - Professional 3D Modeling
[https://www.blender.org/](https://www.blender.org/)

**Why Blender?**
- ✅ **Free and Open Source**
- ✅ **Python API** - Automate 3D scene creation from database
- ✅ **Photorealistic Rendering** - Publication-quality images/videos
- ✅ **Geological Modeling** - Can model complex subsurface structures

**Blender Python Script Example:**
```python
import bpy
import psycopg2

# Connect to database
conn = psycopg2.connect("dbname=nwis_production")
cursor = conn.cursor()

# Fetch well trajectory
cursor.execute("""
    SELECT northing_m, easting_m, tvd
    FROM directional_surveys
    WHERE well_id = %s
    ORDER BY measured_depth_md
""", (well_uuid,))

points = cursor.fetchall()

# Create curve in Blender
curve_data = bpy.data.curves.new('WellPath', type='CURVE')
curve_data.dimensions = '3D'
polyline = curve_data.splines.new('POLY')
polyline.points.add(len(points) - 1)

for i, (x, y, z) in enumerate(points):
    polyline.points[i].co = (x, y, -z, 1)  # Negative Z for depth

# Create object
curve_obj = bpy.data.objects.new('Well_DG-003', curve_data)
bpy.context.collection.objects.link(curve_obj)

# Add formation layers as meshes
cursor.execute("""
    SELECT formation_name, top_depth_tvd, bottom_depth_tvd
    FROM formation_tops
    WHERE well_id = %s
""", (well_uuid,))

for formation_name, top, bottom in cursor.fetchall():
    bpy.ops.mesh.primitive_cube_add(size=1000)
    layer = bpy.context.active_object
    layer.name = formation_name
    layer.location.z = -(top + bottom) / 2
    layer.scale.z = (bottom - top) / 2
```

**Output Formats:**
- Static images (PNG, JPEG) for reports
- Animation videos (MP4) showing drilling progress
- Interactive 3D scenes (GLTF/GLB) for web embedding

---

## Recommended Hybrid Approach

### **For Module 2 (Real-Time Dashboard):**

**Tech Stack:**
- **Frontend:** React + TypeScript
- **Map:** Leaflet.js (2D top view)
- **3D Viewer:** Cesium.js (side cross-section view)
- **Charts:** Apache ECharts
- **Backend:** FastAPI (Python) serving GeoJSON

**UI Layout:**
```
┌────────────────────────────────────────────────────┐
│  NWIS Dashboard - Well DG-003                      │
├────────────────────┬───────────────────────────────┤
│                    │                               │
│  2D Map View       │  Real-Time Parameters         │
│  (Leaflet)         │  ┌─────────────────────┐     │
│                    │  │ Depth: 2,534 m      │     │
│  • Well locations  │  │ WOB: 28.5 klbs      │     │
│  • Offset wells    │  │ ROP: 15.2 m/hr      │     │
│  • Proximity rings │  │ Status: Drilling    │     │
│                    │  └─────────────────────┘     │
├────────────────────┴───────────────────────────────┤
│                                                    │
│  3D Cross-Section View (Cesium.js)                │
│  ┌───────────────────────────────────────────┐    │
│  │              Surface                       │    │
│  │  ═════════════════════════════════════    │    │
│  │     Formation 1 (Sandstone)               │    │
│  │  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌           │    │
│  │       Formation 2 (Shale)                 │    │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓            │    │
│  │         Formation 3 (Limestone)           │    │
│  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░              │    │
│  │          ⬇ Current Bit Position           │    │
│  └───────────────────────────────────────────┘    │
└────────────────────────────────────────────────────┘
```

**Data Flow:**
```
PostgreSQL → FastAPI → WebSocket → React → Cesium.js
   ↓            ↓                      ↓
TimescaleDB   GeoJSON              deck.gl
              REST API            (data overlay)
```

---

## Database Queries for 3D Visualization

### 1. Well Trajectory for 3D Path
```sql
-- Query for Cesium.js polyline
SELECT 
    measured_depth_md,
    ST_X(position_3d::geometry) AS longitude,
    ST_Y(position_3d::geometry) AS latitude,
    -ST_Z(position_3d::geometry) AS elevation_m  -- Negative for below surface
FROM directional_surveys
WHERE well_id = 'well_uuid'
ORDER BY measured_depth_md;
```

### 2. Formation Layers for Cross-Section
```sql
-- Query for colored formation zones
SELECT 
    formation_name,
    formation_lithology,
    top_depth_tvd,
    bottom_depth_tvd,
    (bottom_depth_tvd - top_depth_tvd) AS thickness_m,
    CASE formation_lithology
        WHEN 'Sandstone' THEN '#F4A460'  -- Sandy brown
        WHEN 'Shale' THEN '#696969'      -- Dim gray
        WHEN 'Limestone' THEN '#F5DEB3' -- Wheat
        ELSE '#CCCCCC'
    END AS color_hex
FROM formation_tops
WHERE well_id = 'well_uuid'
ORDER BY top_depth_tvd;
```

### 3. Nearby Wells for Map
```sql
-- Query for map markers (GeoJSON format)
SELECT json_build_object(
    'type', 'FeatureCollection',
    'features', json_agg(
        json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(location)::json,
            'properties', json_build_object(
                'well_id', well_id,
                'well_name', well_name,
                'status', well_status,
                'depth', total_depth_md,
                'field', field_name
            )
        )
    )
) AS geojson
FROM wells
WHERE ST_DWithin(
    location,
    (SELECT location FROM wells WHERE well_id = 'active_well'),
    10000  -- 10km radius
);
```

---

## Implementation Timeline

### Week 1-2: Setup
- Install Cesium.js and deck.gl in React project
- Create database views for GeoJSON output
- Build FastAPI endpoints for geospatial data

### Week 3: 2D Map
- Implement Leaflet.js base map
- Add well markers with status colors
- Add proximity circles (5km, 10km, 20km)

### Week 4: 3D Cross-Section
- Implement Cesium.js viewer
- Render well trajectories as polylines
- Add formation layers as colored volumes

### Week 5: Real-Time Updates
- WebSocket connection for live telemetry
- Animate bit position in 3D view
- Update depth markers in real-time

### Week 6: Polish
- Add camera controls (zoom, pan, tilt)
- Time-lapse replay of drilling progress
- Export 3D scene as GLTF for presentations

---

## Recommended NPM Packages

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "cesium": "^1.112.0",
    "resium": "^1.17.2",        // React bindings for Cesium
    "deck.gl": "^8.9.0",
    "@deck.gl/react": "^8.9.0",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "apache-echarts": "^5.4.3",
    "echarts-for-react": "^3.0.2",
    "axios": "^1.6.2",
    "@turf/turf": "^6.5.0"      // Geospatial calculations
  }
}
```

---

## Alternative: Subsurface Visualization Specialists

If you need **highly specialized subsurface visualization**, consider:

### **Pyvista** (Python 3D Visualization)
[https://pyvista.org/](https://pyvista.org/)
- Built specifically for scientific 3D visualization
- Direct integration with geological data
- Can export to VTK format for Blender

```python
import pyvista as pv

# Create well trajectory
points = np.array([[x, y, -z] for x, y, z in survey_data])
well_path = pv.Spline(points, 100)

# Create formation layers
formations = pv.MultiBlock()
for formation in formation_data:
    layer = pv.Box(bounds=[
        xmin, xmax, ymin, ymax, 
        -formation['top'], -formation['bottom']
    ])
    formations.append(layer)

# Render
plotter = pv.Plotter()
plotter.add_mesh(well_path, color='yellow', line_width=5)
plotter.add_mesh(formations, opacity=0.7)
plotter.show()
```

---

## Final Recommendation

**For Your Module 2:**

🎯 **Use Cesium.js + deck.gl + Leaflet.js**

**Why:**
- Web-based (no installation required)
- Real-time updates via WebSocket
- Integrates perfectly with PostgreSQL/PostGIS
- Professional-looking visualizations
- Active community and documentation
- Can be embedded in any web dashboard

**Architecture:**
```
PostgreSQL/PostGIS (Database)
         ↓
    FastAPI (Backend)
         ↓
  React App (Frontend)
         ↓
    ┌──────────────┬──────────────┐
    ↓              ↓              ↓
Leaflet.js    Cesium.js      ECharts
(2D Map)     (3D Cross)     (Charts)
```

This gives you:
- ✅ 2D map for planning and nearby wells
- ✅ 3D cross-section for subsurface visualization
- ✅ Real-time telemetry charts
- ✅ All in one integrated dashboard
- ✅ Mobile-responsive
- ✅ Shareable via URL

---

**Questions?** Let me know if you'd like code examples for any specific visualization!
