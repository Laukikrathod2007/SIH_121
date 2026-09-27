# Module 2 Planning Document
## Geospatial Offset Intelligence + 3D Well Cross-Section Visualization

**Document Version:** 1.0  
**Created:** September 27, 2026  
**Module Owner:** Harshal (Team Member)  
**PS Outcome:** ii. "Provide an interactive map-based visualization of nearby wells within a user-defined radius."

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Module Overview](#module-overview)
3. [Architectural Decisions](#architectural-decisions)
4. [Data Requirements & Schema](#data-requirements--schema)
5. [3D Visualization Architecture](#3d-visualization-architecture)
6. [2D Map Visualization](#2d-map-visualization)
7. [Backend API Design](#backend-api-design)
8. [Additional Data Documents Needed](#additional-data-documents-needed)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Testing Strategy](#testing-strategy)
11. [Technology Stack](#technology-stack)

---

## 1. Executive Summary

### What Module 2 Delivers

**Two complementary visualizations working in harmony:**

1. **2D Interactive Map (Left Panel)**
   - Bird's eye view showing active well + nearby offset wells
   - User-defined radius slider (5-50 km)
   - Color-coded wells by geological relevance
   - Click well → triggers 3D cross-section view

2. **3D Well Cross-Section Viewer (Right Panel/Modal)**
   - Side-by-side comparison: Active well vs. selected offset well
   - Interactive 3D rendering showing:
     - Wellbore trajectory (vertical or deviated path)
     - Geological formation layers with colors and lithology patterns
     - Casing strings at different depths (conductor, surface, production)
     - Incident markers at exact depths (lost circulation, stuck pipe, kicks)
     - Live bit position advancing in real-time
     - Predictive hazard zones highlighted ahead of bit

### Key Design Decisions (Based on Discussion)

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Q1: 3D Visualization Scope** | **True 3D Model** (Interactive Three.js rendering) | More visually impressive for judges; better for deviated wells; industry-standard expectation |
| **Q2: Geological Data Detail** | **WCR + Lithology + Survey Data** | Need formation tops, lithology descriptions, survey data for accurate 3D model |
| **Q3: Multiple Wells Display** | **Comparison View** (Active + Best Offset side-by-side) | Most valuable for decision-making; shows correlation patterns |
| **Q4: Real-time Integration** | **Live Bit Position + Predictive Overlay** | Core: bit advances in real-time; Enhancement: highlight danger zones ahead |
| **Q5: OCR Data Priority** | **WCR (structure) + DDR (incidents) + Survey (trajectory)** | WCR has formation tops and casing; DDR has incidents; Survey has well path |

---

## 2. Module Overview

### 2.1 User Journey

```
Step 1: Drilling Engineer opens NWIS dashboard
        └─> Sees 2D map centered on active well (Nahorkatiya-A1)

Step 2: Drags radius slider from 5 km → 25 km
        └─> Map updates to show 12 offset wells within 25 km
        └─> Wells color-coded:
            • Green (pulsing): Active well
            • Blue: Geologically relevant offsets
            • Gray: Different fault block (low relevance)

Step 3: Clicks offset well marker "Nahorkatiya-A3" (8 km away)
        └─> 3D Cross-Section Viewer opens in right panel
        └─> Shows side-by-side view:
            [Nahorkatiya-A1 (Active)]  |  [Nahorkatiya-A3 (Offset)]
            
Step 4: 3D Viewer displays:
        ├─ Wellbore trajectories (both wells)
        ├─ Geological layers (Girujan Clay → Barail Formation → Tipam Sandstone)
        ├─ Casing strings (conductor, surface, production casing)
        ├─ Incident markers:
        │   • Nahorkatiya-A3: Lost circulation at 3,542m (Barail Formation)
        │   • Red sphere marker at exact depth
        ├─ Live bit position on Nahorkatiya-A1:
        │   • Currently at 3,487m (green pulsing marker)
        │   • 55 meters before historical loss zone
        ├─ Predictive hazard overlay:
        │   • Yellow highlighted zone: 3,520m - 3,560m
        │   • Label: "⚠️ Approaching historical loss zone"

Step 5: Engineer rotates 3D view (mouse drag)
        └─> See well trajectory from different angles
        └─> Understand geological correlation between wells

Step 6: Engineer hovers over incident marker
        └─> Tooltip shows:
            "Lost Circulation Event
             Depth: 3,542m MD (3,489m TVDSS)
             Formation: Barail Formation
             Loss: 40 bbl total loss
             NPT: 18 hours
             Mitigation: Nut-plug LCM pill
             Source: DDR 2019-06-12, Page 7"

Step 7: Engineer clicks "View Full Report" on tooltip
        └─> PDF viewer opens with highlighted evidence
```

---

### 2.2 Module Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Module 2: Geospatial Intelligence                 │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                 ┌───────────────┴────────────────┐
                 │                                │
       ┌─────────▼─────────┐          ┌─────────▼──────────┐
       │  2D Map Component  │          │  3D Viewer Component│
       │  (React Leaflet)   │          │  (React Three Fiber)│
       └─────────┬──────────┘          └──────────┬──────────┘
                 │                                │
                 │                                │
       ┌─────────▼────────────────────────────────▼──────────┐
       │           Frontend State Management                  │
       │           (React Context + Zustand)                  │
       └─────────┬──────────────────────────────┬─────────────┘
                 │                              │
       ┌─────────▼──────────┐        ┌─────────▼──────────────┐
       │  API: /wells/nearby │        │ API: /wells/{id}/3dmodel│
       │  (Spatial Query)    │        │ (Geological Data)       │
       └─────────┬───────────┘        └─────────┬──────────────┘
                 │                              │
       ┌─────────▼──────────────────────────────▼──────────────┐
       │           Backend FastAPI Service                      │
       │  ┌──────────────────┐  ┌────────────────────────┐    │
       │  │ Spatial Service  │  │ Geological Correlation │    │
       │  │ (PostGIS Queries)│  │ Service (Depth Align)  │    │
       │  └──────────────────┘  └────────────────────────┘    │
       └─────────┬──────────────────────────────┬──────────────┘
                 │                              │
       ┌─────────▼──────────────────────────────▼──────────────┐
       │         PostgreSQL + PostGIS + pgvector                │
       │  Tables:                                               │
       │  • wells (location, metadata)                          │
       │  • formation_tops (depth, lithology)                   │
       │  • well_surveys (trajectory: MD, Inc, Azi)             │
       │  • casing_programs (shoe depths)                       │
       │  • incidents (events at depth)                         │
       └────────────────────────────────────────────────────────┘
```

---

## 3. Architectural Decisions

### 3.1 Why True 3D Model (Not Simple 2D Schematic)?

**Decision: Use Three.js for interactive 3D rendering**

**Pros:**
✅ **Handles deviated wells accurately** - Most modern wells are directional/horizontal  
✅ **Industry expectation** - Oil & gas uses 3D visualization (Petrel, Techlog)  
✅ **Judge appeal** - More visually impressive in hackathon demo  
✅ **Geological correlation** - Easier to see formation continuity in 3D  
✅ **User engagement** - Interactive rotation/zoom increases understanding  

**Cons:**
❌ Development complexity (mitigated by React Three Fiber library)  
❌ Performance for many wells (mitigated by rendering only 2 wells at a time)  

**Tech Stack Decision:**
- **Three.js** (via React Three Fiber) for runtime 3D rendering in browser
- **Blender** for creating static 3D assets (drill bit models, rig equipment)
- **NOT using Blender at runtime** (too heavy, not browser-compatible)

---

### 3.2 Why Blender + Three.js Workflow?

**Blender's Role:**
- Create **static 3D models** (drill bit, casing shoe, BOP stack) → Export as .glb/.gltf files
- Design **lithology textures** (sandstone pattern, shale layers) → Export as PNG textures
- **NOT** used for real-time rendering or data visualization

**Three.js's Role:**
- **Runtime 3D engine** in browser (WebGL-based)
- Dynamically generates well trajectories, formation layers from database data
- Loads Blender-created assets (.glb models) and applies to scene
- Handles user interaction (rotation, zoom, hover)

**Workflow:**
```
Design Phase (Once):
Blender → Create drill bit model → Export as drill_bit.glb → Store in /public/assets/

Runtime (Every time user opens 3D viewer):
1. Fetch well data from API (survey points, formation tops)
2. Three.js generates well trajectory path from survey data
3. Three.js generates formation layer meshes from formation tops
4. Three.js loads drill_bit.glb and positions at current bit depth
5. User sees complete 3D scene with real data + designed assets
```

---

### 3.3 Data Strategy: WCR + DDR + Survey

**Why Multiple Document Types?**

Each document type contributes different critical data:

| Document Type | Critical Data | Example Fields | OCR Difficulty | Priority |
|---------------|---------------|----------------|----------------|----------|
| **Well Completion Report (WCR)** | Structure & Geology | Formation tops, casing program, final well design | Medium (structured tables) | **HIGH** |
| **Daily Drilling Report (DDR)** | Incidents & Operations | Incidents, NPT, depth progress, drilling parameters | High (handwritten, varied formats) | **HIGH** |
| **Well Survey Data** | Trajectory | MD, Inclination, Azimuth, TVD, coordinates | Low (numeric tables) | **CRITICAL** |
| **Mud Log** | Lithology Detail | Show descriptions, lithology %, cuttings analysis | High (free text descriptions) | Medium |
| **Cement Bond Log (CBL)** | Casing Integrity | Cement quality behind casing | Low (log curves) | Low |

**OCR Pipeline Strategy (Module 1):**

Module 1 will scan **all three priority document types**:

```python
# Module 1 OCR Pipeline
class DocumentRouter:
    def classify_document(self, pdf_path):
        """Classify document type to route to correct extractor"""
        # Use first page text to identify document type
        if "WELL COMPLETION REPORT" in first_page:
            return "WCR"
        elif "DAILY DRILLING REPORT" in first_page:
            return "DDR"
        elif "DIRECTIONAL SURVEY" in first_page or "MD" in headers:
            return "SURVEY"
```


**Extraction Targets per Document Type:**

**From WCR:**
- Well metadata (name, location, dates, total depth)
- Formation tops table (formation name, MD, TVDSS)
- Casing program table (size, depth, grade)
- Mud program (mud weight, type per depth interval)
- Final well status

**From DDR:**
- Daily depth progress
- Incidents (type, depth, description, NPT hours)
- Drilling parameters (ROP, WOB, RPM, SPP per depth)
- Operational remarks

**From Survey:**
- Survey station data (MD, Inclination, Azimuth, TVD, Northing, Easting)
- Minimum: 1 survey station every 30m for smooth trajectory

---

## 4. Data Requirements & Schema

### 4.1 Minimum Data Fields for 3D Visualization

To render a complete 3D well cross-section, we need **exactly these fields**:

#### 4.1.1 Well Trajectory Data (CRITICAL)

**Why needed:** To draw the wellbore path in 3D space

```sql
-- well_surveys table
CREATE TABLE well_surveys (
    id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(id),
    measured_depth_m DECIMAL(8,2) NOT NULL,      -- Distance along wellbore
    inclination_deg DECIMAL(5,2) NOT NULL,       -- Angle from vertical (0° = vertical, 90° = horizontal)
    azimuth_deg DECIMAL(5,2) NOT NULL,           -- Compass direction (0° = North, 90° = East)
    tvd_m DECIMAL(8,2),                          -- True Vertical Depth
    northing_m DECIMAL(10,2),                    -- Y coordinate
    easting_m DECIMAL(10,2),                     -- X coordinate
    survey_date DATE
);
```

**Example Data (Deviated Well):**
```
MD (m)  | Inc (°) | Azi (°) | TVD (m) | Northing (m) | Easting (m)
--------|---------|---------|---------|--------------|------------
0       | 0.0     | 0.0     | 0       | 0            | 0
500     | 2.5     | 135.0   | 499.9   | -5.2         | 5.2
1000    | 15.8    | 135.0   | 989.3   | -87.4        | 87.4
1500    | 32.5    | 135.0   | 1444.2  | -245.8       | 245.8
2000    | 48.2    | 135.0   | 1825.7  | -478.3       | 478.3
2500    | 65.0    | 135.0   | 2098.4  | -756.9       | 756.9
3000    | 78.5    | 135.0   | 2281.5  | -1067.2      | 1067.2
3500    | 87.2    | 135.0   | 2384.9  | -1398.4      | 1398.4  (Nearly horizontal)
```

**How Three.js uses this:**
```javascript
// Convert survey stations to 3D trajectory curve
const trajectoryPoints = surveyData.map(station => 
    new THREE.Vector3(
        station.easting_m,      // X axis
        -station.tvd_m,         // Y axis (negative because depth increases downward)
        station.northing_m      // Z axis
    )
);
const curve = new THREE.CatmullRomCurve3(trajectoryPoints);
const wellboreGeometry = new THREE.TubeGeometry(curve, 200, 0.15, 8, false);
```

---

#### 4.1.2 Formation Tops Data (CRITICAL)

**Why needed:** To draw colored geological layers

```sql
-- formation_tops table
CREATE TABLE formation_tops (
    id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(id),
    formation_name VARCHAR(100) NOT NULL,
    top_depth_md_m DECIMAL(8,2) NOT NULL,       -- Where formation starts (Measured Depth)
    top_depth_tvd_m DECIMAL(8,2),               -- True Vertical Depth
    lithology_primary VARCHAR(50),               -- sandstone, shale, limestone, coal
    lithology_description TEXT,                  -- "Gray shale with sand streaks"
    color_hex VARCHAR(7),                        -- For visualization (#F4A460 for sandstone)
    age VARCHAR(50),                             -- Eocene, Miocene, etc.
    hazard_zone BOOLEAN DEFAULT FALSE            -- Known trouble zone
);
```

**Example Data (OIL India - Upper Assam Basin):**
```
Formation Name       | Top MD (m) | Top TVD (m) | Lithology  | Color    | Hazard
---------------------|------------|-------------|------------|----------|--------
Surface              | 0          | 0           | soil       | #8B4513  | false
Girujan Clay         | 280        | 280         | shale      | #696969  | false
Namsang Formation    | 1850       | 1840        | sandstone  | #F4A460  | false
Tikak Parbat         | 2650       | 2615        | limestone  | #E8E8E8  | false
Kopili Formation     | 3100       | 3042        | shale      | #4F4F4F  | false
Barail Formation     | 3400       | 3312        | sandstone  | #DAA520  | TRUE (Lost circulation risk)
Tipam Sandstone      | 3750       | 3628        | sandstone  | #DEB887  | false
Lakadong Sandstone   | 4200       | 4058        | sandstone  | #CD853F  | false
```

**How Three.js uses this:**
```javascript
// Create geological layer meshes
formationTops.forEach((formation, index) => {
    const topDepth = formation.top_depth_tvd_m;
    const bottomDepth = formationTops[index + 1]?.top_depth_tvd_m || totalDepth;
    const thickness = bottomDepth - topDepth;
    
    const layerGeometry = new THREE.BoxGeometry(50, thickness, 50); // 50m x 50m horizontal extent
    const layerMaterial = new THREE.MeshStandardMaterial({
        color: formation.color_hex,
        opacity: 0.7,
        transparent: true
    });
    const layer = new THREE.Mesh(layerGeometry, layerMaterial);
    layer.position.y = -(topDepth + thickness/2);  // Center at middle of layer
});
```

---

#### 4.1.3 Casing Program Data (IMPORTANT)

**Why needed:** To show casing strings (pipes) inside wellbore

```sql
-- casing_program table
CREATE TABLE casing_program (
    id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(id),
    casing_type VARCHAR(50) NOT NULL,            -- conductor, surface, intermediate, production
    outer_diameter_inch DECIMAL(5,2) NOT NULL,   -- 30", 20", 13-3/8", 9-5/8", 7"
    shoe_depth_md_m DECIMAL(8,2) NOT NULL,       -- How deep casing goes
    shoe_depth_tvd_m DECIMAL(8,2),
    top_depth_md_m DECIMAL(8,2) DEFAULT 0,       -- Usually 0 (surface)
    grade VARCHAR(20),                            -- K55, N80, P110
    weight_per_foot_lb DECIMAL(6,2),
    cement_top_md_m DECIMAL(8,2),                -- Where cement reaches
    installation_date DATE
);
```

**Example Data (Typical OIL India Well):**
```
Casing Type     | OD (inch) | Shoe Depth (m) | Grade | Purpose
----------------|-----------|----------------|-------|---------------------------
Conductor       | 30"       | 50             | K55   | Structural support, soil isolation
Surface         | 20"       | 600            | K55   | Freshwater protection
Intermediate    | 13-3/8"   | 2800           | N80   | Isolate unstable formations
Production      | 9-5/8"    | 3650           | P110  | Production string
Liner           | 7"        | 4500           | P110  | Reservoir section (hangs from production)
```

**How Three.js uses this:**
```javascript
// Render casing strings as cylinders
casingProgram.forEach(casing => {
    const radius = (casing.outer_diameter_inch * 0.0254) / 2;  // Convert inch to meters
    const length = casing.shoe_depth_tvd_m;
    
    const casingGeometry = new THREE.CylinderGeometry(radius, radius, length, 32);
    const casingMaterial = new THREE.MeshStandardMaterial({
        color: getCasingColor(casing.casing_type),  // Gray for steel
        metalness: 0.8,
        roughness: 0.3
    });
    const casingMesh = new THREE.Mesh(casingGeometry, casingMaterial);
    casingMesh.position.y = -length / 2;  // Top at surface, extends downward
});
```

---

#### 4.1.4 Incident/Event Data (IMPORTANT)

**Why needed:** To place incident markers at exact depths

```sql
-- incidents table
CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(id),
    incident_type VARCHAR(50) NOT NULL,          -- lost_circulation, stuck_pipe, kick, torque_spike
    depth_md_m DECIMAL(8,2) NOT NULL,
    depth_tvd_m DECIMAL(8,2),
    formation VARCHAR(100),
    incident_date DATE NOT NULL,
    description TEXT,
    severity VARCHAR(20),                        -- minor, moderate, severe, critical
    npt_hours DECIMAL(6,2),                      -- Non-Productive Time
    cost_usd DECIMAL(12,2),
    mitigation_action TEXT,
    success BOOLEAN,
    source_document VARCHAR(255)                 -- Link to PDF, page number
);
```

**Example Data:**
```
Well         | Type              | Depth (m) | Formation      | NPT (hrs) | Mitigation
-------------|-------------------|-----------|----------------|-----------|-------------------------
Nahorkatiya-A1| lost_circulation | 3542      | Barail Form.   | 18        | 30 bbl nut-plug LCM pill
Nahorkatiya-A1| stuck_pipe       | 2987      | Kopili Shale   | 36        | Spotting fluid + jarring
Moran-B2     | kick              | 3211      | Tipam SS       | 12        | Well control, kill mud
Moran-B2     | lost_circulation | 3556      | Barail Form.   | 24        | Cement plug
```

**How Three.js uses this:**
```javascript
// Place incident markers as 3D spheres
incidents.forEach(incident => {
    const markerGeometry = new THREE.SphereGeometry(5, 32, 32);  // 5m radius sphere
    const markerMaterial = new THREE.MeshStandardMaterial({
        color: getIncidentColor(incident.incident_type),  // Red for severe, yellow for moderate
        emissive: 0xff0000,
        emissiveIntensity: 0.3
    });
    const marker = new THREE.Mesh(markerGeometry, markerMaterial);
    marker.position.y = -incident.depth_tvd_m;
    marker.userData = incident;  // Store data for hover tooltip
});
```

---

#### 4.1.5 Live Drilling Data (Real-time / Mock)

**Why needed:** Show current bit position advancing

```sql
-- drilling_realtime table (updated every minute)
CREATE TABLE drilling_realtime (
    id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(id),
    timestamp TIMESTAMPTZ NOT NULL,
    current_depth_md_m DECIMAL(8,2) NOT NULL,
    current_depth_tvd_m DECIMAL(8,2),
    rop_m_per_hr DECIMAL(6,2),                   -- Rate of Penetration
    wob_klb DECIMAL(6,2),                        -- Weight on Bit (1000 lbs)
    rpm DECIMAL(6,2),                            -- Rotary speed
    spp_psi DECIMAL(7,2),                        -- Standpipe Pressure
    torque_kft_lb DECIMAL(7,2),                  -- Torque
    flow_rate_gpm DECIMAL(6,2),                  -- Mud flow rate
    pit_volume_bbl DECIMAL(7,2),                 -- Mud pit volume
    gas_units_ppm DECIMAL(8,2)                   -- Gas detection
);
```

**For Hackathon Demo (Mock Data):**
```javascript
// Simulate bit advancing 15 meters per hour
setInterval(() => {
    currentDepth += 0.25;  // 0.25m per minute = 15 m/hr
    updateBitPosition(currentDepth);
    
    // Check if approaching hazard zone
    if (isNearHazard(currentDepth)) {
        triggerProactiveAlert();
    }
}, 60000);  // Every 1 minute
```

---

### 4.2 Complete Database Schema for Module 2

```sql
-- Main wells table
CREATE TABLE wells (
    id SERIAL PRIMARY KEY,
    well_name VARCHAR(100) UNIQUE NOT NULL,
    field_name VARCHAR(100),
    location GEOGRAPHY(POINT, 4326) NOT NULL,    -- PostGIS for spatial queries
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    spud_date DATE,
    completion_date DATE,
    total_depth_md_m DECIMAL(8,2),
    total_depth_tvd_m DECIMAL(8,2),
    well_type VARCHAR(20),                        -- vertical, directional, horizontal
    well_status VARCHAR(20),                      -- active, completed, abandoned
    operator VARCHAR(100),
    basin VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index for fast radius queries
CREATE INDEX idx_wells_location ON wells USING GIST(location);

-- All other tables as defined above:
-- well_surveys, formation_tops, casing_program, incidents, drilling_realtime
```

---

### 4.3 Data Validation Rules

To ensure synthetic data looks **realistic and logically correct**, enforce these rules:

#### Geological Rules:
✅ **Rule 1:** Formation tops must increase with depth (older formations deeper)
```python
assert formation_tops[i].depth < formation_tops[i+1].depth
```

✅ **Rule 2:** Formation thickness must be realistic (50m - 500m typical)
```python
thickness = formation_tops[i+1].depth - formation_tops[i].depth
assert 50 <= thickness <= 500
```

✅ **Rule 3:** Lithology transitions must be logical
```python
# Valid transitions: shale → sandstone → shale (depositional cycles)
# Invalid: limestone → coal → limestone (geologically unlikely)
```

#### Drilling Rules:
✅ **Rule 4:** Casing sizes must decrease with depth (telescoping)
```python
assert casing[i].diameter > casing[i+1].diameter
```

✅ **Rule 5:** Casing shoes must be set before next section drilled
```python
assert casing[i].shoe_depth < casing[i+1].shoe_depth
```

✅ **Rule 6:** Incidents must occur at drilled depths
```python
assert incident.depth <= well.total_depth
```

#### Survey Rules:
✅ **Rule 7:** Inclination cannot exceed 90° (horizontal limit)
```python
assert 0 <= inclination <= 90
```

✅ **Rule 8:** Survey frequency: minimum 1 station per 30m
```python
max_spacing = max(survey[i+1].md - survey[i].md for i in range(len(survey)-1))
assert max_spacing <= 30
```

✅ **Rule 9:** TVD cannot exceed MD (physical impossibility)
```python
assert tvd <= md
```

---

## 5. 3D Visualization Architecture

### 5.1 Technology Stack

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| **3D Rendering Engine** | Three.js (via React Three Fiber) | Industry standard WebGL library; massive ecosystem; excellent docs |
| **React Integration** | @react-three/fiber + @react-three/drei | Declarative Three.js in React; includes helpers (OrbitControls, Text, etc.) |
| **3D Model Assets** | Blender → .glb/.gltf export | Create drill bits, BOP, rig equipment as static models |
| **Textures** | Procedural + PNG images | Sandstone, shale patterns; rock textures |
| **Physics (Optional)** | @react-three/cannon | If we want particles for mud circulation |
| **Performance** | React Three Fiber's `useFrame` + LOD | Level of Detail for distant objects |

---

### 5.2 React Component Hierarchy

```
<Module2Dashboard>
    ├─ <MapView>                          (Left panel: 2D map)
    │   ├─ <LeafletMap>
    │   ├─ <WellMarkers>
    │   └─ <RadiusSlider>
    │
    ├─ <Well3DViewer>                     (Right panel: 3D cross-section)
    │   ├─ <Canvas>                       (React Three Fiber canvas)
    │   │   ├─ <Scene>
    │   │   │   ├─ <ActiveWell>
    │   │   │   │   ├─ <WellTrajectory curve={surveyData} />
    │   │   │   │   ├─ <CasingStrings casings={casingProgram} />
    │   │   │   │   ├─ <LiveBit position={currentDepth} />
    │   │   │   │   └─ <IncidentMarkers incidents={activeIncidents} />
    │   │   │   │
    │   │   │   ├─ <OffsetWell>
    │   │   │   │   ├─ <WellTrajectory curve={offsetSurveyData} />
    │   │   │   │   ├─ <CasingStrings casings={offsetCasingProgram} />
    │   │   │   │   └─ <IncidentMarkers incidents={offsetIncidents} />
    │   │   │   │
    │   │   │   ├─ <GeologicalLayers formations={formationTops} />
    │   │   │   │   ├─ <FormationLayer name="Girujan Clay" color="#696969" />
    │   │   │   │   ├─ <FormationLayer name="Barail Formation" color="#DAA520" hazard={true} />
    │   │   │   │   └─ <FormationLayer name="Tipam Sandstone" color="#DEB887" />
    │   │   │   │
    │   │   │   ├─ <HazardZone depth={3520} height={40} />
    │   │   │   │
    │   │   │   ├─ <OrbitControls />    (Mouse rotation)
    │   │   │   ├─ <AmbientLight />
    │   │   │   └─ <DirectionalLight />
    │   │   │
    │   │   └─ <DepthAxis />            (Vertical ruler showing meters)
    │   │
    │   ├─ <Tooltip3D />                 (Hover tooltips for incidents)
    │   └─ <ViewControls>                (Zoom, reset camera, toggle layers)
    │
    └─ <ComparisonStats>                 (Bottom panel: metrics comparison)
        ├─ <DepthComparison />
        ├─ <IncidentCount />
        └─ <GeologicalSimilarity />
```

---

### 5.3 Core Three.js Components (Code Examples)

#### 5.3.1 WellTrajectory Component

```typescript
// src/components/3d/WellTrajectory.tsx
import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface SurveyStation {
    md: number;
    inc: number;
    azi: number;
    tvd: number;
    northing: number;
    easting: number;
}

interface WellTrajectoryProps {
    surveyData: SurveyStation[];
    color?: string;
    isActive?: boolean;
}

export function WellTrajectory({ surveyData, color = '#1E90FF', isActive = false }: WellTrajectoryProps) {
    const tubeRef = useRef<THREE.Mesh>(null);
    
    // Convert survey stations to 3D points
    const trajectoryPoints = surveyData.map(station => 
        new THREE.Vector3(
            station.easting,
            -station.tvd,      // Negative because depth goes down
            station.northing
        )
    );
    
    // Create smooth curve through survey points
    const curve = new THREE.CatmullRomCurve3(trajectoryPoints);
    
    // Pulse animation for active well
    useFrame((state) => {
        if (isActive && tubeRef.current) {
            const pulsate = Math.sin(state.clock.elapsedTime * 2) * 0.1 + 1;
            tubeRef.current.scale.set(pulsate, 1, pulsate);
        }
    });
    
    return (
        <mesh ref={tubeRef}>
            <tubeGeometry args={[curve, 200, 0.15, 16, false]} />
            <meshStandardMaterial 
                color={color}
                metalness={0.6}
                roughness={0.4}
                emissive={isActive ? color : '#000000'}
                emissiveIntensity={isActive ? 0.3 : 0}
            />
        </mesh>
    );
}
```


#### 5.3.2 GeologicalLayers Component

```typescript
// src/components/3d/GeologicalLayers.tsx
import * as THREE from 'three';

interface FormationTop {
    formation_name: string;
    top_depth_tvd_m: number;
    color_hex: string;
    lithology_primary: string;
    hazard_zone: boolean;
}

interface GeologicalLayersProps {
    formations: FormationTop[];
    totalDepth: number;
    extent: number;  // Horizontal extent (50m x 50m box)
}

export function GeologicalLayers({ formations, totalDepth, extent = 50 }: GeologicalLayersProps) {
    return (
        <group name="geological-layers">
            {formations.map((formation, index) => {
                const topDepth = formation.top_depth_tvd_m;
                const bottomDepth = formations[index + 1]?.top_depth_tvd_m || totalDepth;
                const thickness = bottomDepth - topDepth;
                const centerDepth = topDepth + thickness / 2;
                
                return (
                    <mesh 
                        key={formation.formation_name}
                        position={[0, -centerDepth, 0]}
                        userData={{ formation }}
                    >
                        <boxGeometry args={[extent, thickness, extent]} />
                        <meshStandardMaterial
                            color={formation.color_hex}
                            opacity={formation.hazard_zone ? 0.5 : 0.7}
                            transparent
                            side={THREE.DoubleSide}
                            roughness={0.8}
                        />
                        
                        {/* Formation label */}
                        <mesh position={[extent/2 + 5, 0, 0]}>
                            <textGeometry args={[formation.formation_name, { size: 2, height: 0.1 }]} />
                            <meshBasicMaterial color="#ffffff" />
                        </mesh>
                        
                        {/* Hazard zone highlighting */}
                        {formation.hazard_zone && (
                            <mesh>
                                <boxGeometry args={[extent + 2, thickness, extent + 2]} />
                                <meshBasicMaterial 
                                    color="#FF6B6B"
                                    opacity={0.2}
                                    transparent
                                    wireframe
                                />
                            </mesh>
                        )}
                    </mesh>
                );
            })}
        </group>
    );
}
```

---

#### 5.3.3 LiveBit Component (Pulsing Marker)

```typescript
// src/components/3d/LiveBit.tsx
import { useRef } from 'react';
import { useFrame, useLoader } from '@react-three/fiber';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import * as THREE from 'three';

interface LiveBitProps {
    currentDepthTVD: number;
    eastingOffset: number;
    northingOffset: number;
}

export function LiveBit({ currentDepthTVD, eastingOffset = 0, northingOffset = 0 }: LiveBitProps) {
    const bitRef = useRef<THREE.Group>(null);
    
    // Load drill bit 3D model (created in Blender)
    const gltf = useLoader(GLTFLoader, '/assets/drill_bit.glb');
    
    // Pulsing animation
    useFrame((state) => {
        if (bitRef.current) {
            const pulse = Math.sin(state.clock.elapsedTime * 3) * 0.2 + 1;
            bitRef.current.scale.set(pulse, pulse, pulse);
            
            // Slow rotation
            bitRef.current.rotation.y += 0.02;
        }
    });
    
    return (
        <group 
            ref={bitRef}
            position={[eastingOffset, -currentDepthTVD, northingOffset]}
        >
            {/* Use Blender model if available */}
            <primitive object={gltf.scene.clone()} scale={0.5} />
            
            {/* Fallback: Simple cone if model not loaded */}
            <mesh rotation={[Math.PI, 0, 0]}>
                <coneGeometry args={[0.5, 2, 8]} />
                <meshStandardMaterial 
                    color="#00FF00"
                    emissive="#00FF00"
                    emissiveIntensity={0.5}
                    metalness={0.9}
                />
            </mesh>
            
            {/* Glow effect */}
            <pointLight color="#00FF00" intensity={1} distance={10} />
        </group>
    );
}
```

---

#### 5.3.4 IncidentMarkers Component

```typescript
// src/components/3d/IncidentMarkers.tsx
import { useState } from 'react';
import { Html } from '@react-three/drei';

interface Incident {
    id: number;
    incident_type: string;
    depth_tvd_m: number;
    description: string;
    npt_hours: number;
    formation: string;
}

interface IncidentMarkersProps {
    incidents: Incident[];
    eastingOffset?: number;
    northingOffset?: number;
}

export function IncidentMarkers({ incidents, eastingOffset = 0, northingOffset = 0 }: IncidentMarkersProps) {
    const [hoveredId, setHoveredId] = useState<number | null>(null);
    
    const getIncidentColor = (type: string) => {
        const colors = {
            lost_circulation: '#FF4444',
            stuck_pipe: '#FF8C00',
            kick: '#DC143C',
            torque_spike: '#FFD700'
        };
        return colors[type] || '#FF0000';
    };
    
    return (
        <group name="incident-markers">
            {incidents.map((incident) => (
                <group 
                    key={incident.id}
                    position={[eastingOffset + 3, -incident.depth_tvd_m, northingOffset]}
                    onPointerOver={() => setHoveredId(incident.id)}
                    onPointerOut={() => setHoveredId(null)}
                >
                    {/* Sphere marker */}
                    <mesh>
                        <sphereGeometry args={[hoveredId === incident.id ? 0.8 : 0.5, 32, 32]} />
                        <meshStandardMaterial
                            color={getIncidentColor(incident.incident_type)}
                            emissive={getIncidentColor(incident.incident_type)}
                            emissiveIntensity={0.4}
                        />
                    </mesh>
                    
                    {/* Tooltip on hover */}
                    {hoveredId === incident.id && (
                        <Html distanceFactor={10}>
                            <div className="incident-tooltip">
                                <h4>{incident.incident_type.replace('_', ' ').toUpperCase()}</h4>
                                <p><strong>Depth:</strong> {incident.depth_tvd_m}m TVDSS</p>
                                <p><strong>Formation:</strong> {incident.formation}</p>
                                <p><strong>NPT:</strong> {incident.npt_hours} hours</p>
                                <p className="description">{incident.description}</p>
                            </div>
                        </Html>
                    )}
                </group>
            ))}
        </group>
    );
}
```

---

#### 5.3.5 Main 3D Viewer Component

```typescript
// src/components/Well3DViewer.tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid } from '@react-three/drei';
import { WellTrajectory } from './3d/WellTrajectory';
import { GeologicalLayers } from './3d/GeologicalLayers';
import { LiveBit } from './3d/LiveBit';
import { IncidentMarkers } from './3d/IncidentMarkers';
import { CasingStrings } from './3d/CasingStrings';

interface Well3DViewerProps {
    activeWell: WellData;
    offsetWell: WellData | null;
}

export function Well3DViewer({ activeWell, offsetWell }: Well3DViewerProps) {
    return (
        <div className="well-3d-viewer" style={{ width: '100%', height: '100vh' }}>
            <Canvas>
                {/* Camera setup */}
                <PerspectiveCamera makeDefault position={[100, -2000, 100]} fov={50} />
                
                {/* Lighting */}
                <ambientLight intensity={0.4} />
                <directionalLight position={[50, 100, 50]} intensity={0.8} castShadow />
                <pointLight position={[0, -2000, 0]} intensity={0.5} />
                
                {/* Grid for reference */}
                <Grid 
                    args={[200, 200]}
                    cellSize={10}
                    cellThickness={0.5}
                    cellColor="#6e6e6e"
                    sectionSize={50}
                    sectionThickness={1}
                    sectionColor="#4a4a4a"
                    fadeDistance={500}
                />
                
                {/* Active Well (Left side) */}
                <group position={[-30, 0, 0]}>
                    <WellTrajectory 
                        surveyData={activeWell.surveys}
                        color="#00FF00"
                        isActive={true}
                    />
                    <CasingStrings casings={activeWell.casing_program} />
                    <LiveBit currentDepthTVD={activeWell.current_depth_tvd} />
                    <IncidentMarkers incidents={activeWell.incidents} />
                </group>
                
                {/* Offset Well (Right side) */}
                {offsetWell && (
                    <group position={[30, 0, 0]}>
                        <WellTrajectory 
                            surveyData={offsetWell.surveys}
                            color="#1E90FF"
                        />
                        <CasingStrings casings={offsetWell.casing_program} />
                        <IncidentMarkers 
                            incidents={offsetWell.incidents}
                            eastingOffset={30}
                        />
                    </group>
                )}
                
                {/* Geological Layers (shared between wells) */}
                <GeologicalLayers 
                    formations={activeWell.formation_tops}
                    totalDepth={Math.max(activeWell.total_depth_tvd, offsetWell?.total_depth_tvd || 0)}
                    extent={80}
                />
                
                {/* Controls */}
                <OrbitControls 
                    enableDamping
                    dampingFactor={0.05}
                    minDistance={50}
                    maxDistance={500}
                />
            </Canvas>
            
            {/* UI Overlay */}
            <div className="viewer-overlay">
                <div className="well-labels">
                    <div className="active-well-label">
                        🟢 {activeWell.well_name} (Active)
                        <br />Current: {activeWell.current_depth_tvd}m TVDSS
                    </div>
                    {offsetWell && (
                        <div className="offset-well-label">
                            🔵 {offsetWell.well_name} (Offset)
                            <br />TD: {offsetWell.total_depth_tvd}m TVDSS
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
```

---

### 5.4 Blender Asset Creation Workflow

**Step-by-step guide for creating 3D assets in Blender:**

#### Asset 1: Drill Bit Model

```
1. Open Blender → Delete default cube
2. Add Cone (Shift+A → Mesh → Cone)
   - Vertices: 16
   - Radius: 0.5m
   - Depth: 2m
3. Add modifier → Array (circular) for cutting teeth
4. Material:
   - Base Color: #444444 (dark gray steel)
   - Metallic: 0.9
   - Roughness: 0.3
5. Export: File → Export → glTF 2.0 (.glb)
   - Save as: public/assets/drill_bit.glb
   - Format: glTF Binary (.glb)
   - Include: Selected Objects only
```

#### Asset 2: Lithology Textures

```
Sandstone Texture:
1. Blender → Shading workspace
2. Create material with noise texture
3. Color: #F4A460 (sandy brown)
4. Texture → Image Texture → Bake to PNG
5. Export as: public/assets/textures/sandstone.png (512x512)

Shale Texture:
1. Similar process
2. Color: #696969 (dark gray)
3. Add horizontal line pattern (bedding planes)
4. Export as: public/assets/textures/shale.png

Limestone Texture:
1. Color: #E8E8E8 (light gray)
2. Add subtle crystalline pattern
3. Export as: public/assets/textures/limestone.png
```

**Using textures in Three.js:**
```typescript
import { useTexture } from '@react-three/drei';

function FormationLayer({ lithology }) {
    const sandstoneTexture = useTexture('/assets/textures/sandstone.png');
    const shaleTexture = useTexture('/assets/textures/shale.png');
    
    const texture = lithology === 'sandstone' ? sandstoneTexture : shaleTexture;
    
    return (
        <mesh>
            <boxGeometry args={[50, 100, 50]} />
            <meshStandardMaterial map={texture} />
        </mesh>
    );
}
```

---

## 6. 2D Map Visualization

### 6.1 Map Component Architecture

```typescript
// src/components/MapView.tsx
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import { useState, useEffect } from 'react';
import L from 'leaflet';

interface Well {
    id: number;
    well_name: string;
    latitude: number;
    longitude: number;
    relevance_score: number;  // 0-100
    is_active: boolean;
}

interface MapViewProps {
    activeWell: Well;
    offsetWells: Well[];
    radius: number;  // km
    onWellClick: (well: Well) => void;
}

export function MapView({ activeWell, offsetWells, radius, onWellClick }: MapViewProps) {
    const [selectedWellId, setSelectedWellId] = useState<number | null>(null);
    
    // Custom marker icons
    const activeIcon = L.divIcon({
        className: 'active-well-marker',
        html: '<div class="pulse-marker green"></div>',
        iconSize: [20, 20]
    });
    
    const offsetIcon = (relevance: number) => L.divIcon({
        className: 'offset-well-marker',
        html: `<div class="well-marker ${getRelevanceClass(relevance)}"></div>`,
        iconSize: [12, 12]
    });
    
    const getRelevanceClass = (score: number) => {
        if (score >= 80) return 'high-relevance';      // Blue
        if (score >= 50) return 'medium-relevance';    // Light blue
        return 'low-relevance';                        // Gray
    };
    
    return (
        <div className="map-view">
            {/* Radius Slider */}
            <div className="radius-control">
                <label>Search Radius: {radius} km</label>
                <input 
                    type="range" 
                    min="5" 
                    max="50" 
                    step="5"
                    value={radius}
                    onChange={(e) => onRadiusChange(Number(e.target.value))}
                />
            </div>
            
            {/* Map */}
            <MapContainer
                center={[activeWell.latitude, activeWell.longitude]}
                zoom={10}
                style={{ height: '100%', width: '100%' }}
                preferCanvas={true}
            >
                {/* Dark mode tile layer (control room friendly) */}
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                />
                
                {/* Radius circle around active well */}
                <Circle
                    center={[activeWell.latitude, activeWell.longitude]}
                    radius={radius * 1000}  // Convert km to meters
                    pathOptions={{
                        color: '#00FF00',
                        fillColor: '#00FF00',
                        fillOpacity: 0.1,
                        weight: 2
                    }}
                />
                
                {/* Active Well Marker */}
                <Marker
                    position={[activeWell.latitude, activeWell.longitude]}
                    icon={activeIcon}
                >
                    <Popup>
                        <div className="well-popup active">
                            <h3>🟢 {activeWell.well_name}</h3>
                            <p><strong>Status:</strong> Active Drilling</p>
                            <p><strong>Current Depth:</strong> 3,487m</p>
                            <p><strong>Formation:</strong> Barail Formation</p>
                        </div>
                    </Popup>
                </Marker>
                
                {/* Offset Well Markers */}
                {offsetWells.map(well => (
                    <Marker
                        key={well.id}
                        position={[well.latitude, well.longitude]}
                        icon={offsetIcon(well.relevance_score)}
                        eventHandlers={{
                            click: () => {
                                setSelectedWellId(well.id);
                                onWellClick(well);
                            }
                        }}
                    >
                        <Popup>
                            <div className="well-popup offset">
                                <h3>🔵 {well.well_name}</h3>
                                <p><strong>Relevance:</strong> {well.relevance_score}%</p>
                                <p><strong>Distance:</strong> {calculateDistance(activeWell, well).toFixed(1)} km</p>
                                <button onClick={() => onWellClick(well)}>
                                    View 3D Cross-Section
                                </button>
                            </div>
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
}
```

---

### 6.2 Geological Relevance Scoring Algorithm

**Multi-factor scoring to rank offset wells (not just distance):**

```python
# Backend: services/relevance_scoring.py

from typing import List, Dict
import math

def calculate_relevance_score(active_well: Well, offset_well: Well) -> Dict:
    """
    Calculate multi-factor geological relevance score (0-100)
    
    Factors:
    1. Physical Distance (25% weight)
    2. Geological Similarity (35% weight)
    3. Fault Block Matching (25% weight)
    4. Directional Similarity (15% weight)
    """
    
    # Factor 1: Physical Distance Score
    distance_km = haversine_distance(
        active_well.latitude, active_well.longitude,
        offset_well.latitude, offset_well.longitude
    )
    distance_score = max(0, 100 - (distance_km * 2))  # Penalize >50km heavily
    
    # Factor 2: Geological Similarity (formation overlap)
    active_formations = set(f.formation_name for f in active_well.formation_tops)
    offset_formations = set(f.formation_name for f in offset_well.formation_tops)
    
    formation_overlap = len(active_formations & offset_formations) / len(active_formations)
    geological_score = formation_overlap * 100
    
    # Factor 3: Fault Block Matching
    # (Assume we have fault block IDs in database)
    fault_block_score = 100 if active_well.fault_block_id == offset_well.fault_block_id else 20
    
    # Factor 4: Directional Similarity (for directional wells)
    if active_well.well_type == 'directional' and offset_well.well_type == 'directional':
        active_azi = get_average_azimuth(active_well.surveys)
        offset_azi = get_average_azimuth(offset_well.surveys)
        
        azi_diff = abs(active_azi - offset_azi)
        azi_diff = min(azi_diff, 360 - azi_diff)  # Handle wraparound
        directional_score = max(0, 100 - (azi_diff / 1.8))  # Perfect match at 0°, zero at 180°
    else:
        directional_score = 50  # Neutral for vertical wells
    
    # Weighted combination
    final_score = (
        distance_score * 0.25 +
        geological_score * 0.35 +
        fault_block_score * 0.25 +
        directional_score * 0.15
    )
    
    return {
        'total_score': round(final_score, 1),
        'distance_km': round(distance_km, 2),
        'distance_score': round(distance_score, 1),
        'geological_score': round(geological_score, 1),
        'fault_block_score': fault_block_score,
        'directional_score': round(directional_score, 1),
        'explanation': generate_explanation(final_score, distance_km, formation_overlap)
    }

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points"""
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def generate_explanation(score, distance, overlap):
    if score >= 80:
        return f"Highly relevant: Only {distance:.1f} km away with {overlap*100:.0f}% formation overlap"
    elif score >= 50:
        return f"Moderately relevant: {distance:.1f} km away, some geological similarity"
    else:
        return f"Low relevance: Different geological context or too far ({distance:.1f} km)"
```

---

## 7. Backend API Design

### 7.1 API Endpoints for Module 2

```python
# Backend: routers/wells.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/api/wells", tags=["wells"])

# ============================================================================
# Endpoint 1: Get Nearby Wells (with relevance scoring)
# ============================================================================
@router.get("/nearby")
async def get_nearby_wells(
    active_well_id: int,
    radius_km: float = 25.0,
    min_relevance: float = 0.0,
    db: Session = Depends(get_db)
):
    """
    Get offset wells within radius of active well, ranked by relevance.
    
    Query params:
    - active_well_id: ID of the well currently drilling
    - radius_km: Search radius (5-50 km)
    - min_relevance: Filter wells below this relevance score (0-100)
    
    Returns: List of offset wells with relevance scores
    """
    
    active_well = db.query(Well).filter(Well.id == active_well_id).first()
    if not active_well:
        raise HTTPException(status_code=404, detail="Active well not found")
    
    # PostGIS spatial query
    nearby_wells = db.execute(f"""
        SELECT 
            w.*,
            ST_Distance(
                w.location::geography,
                ST_SetSRID(ST_MakePoint({active_well.longitude}, {active_well.latitude}), 4326)::geography
            ) / 1000 as distance_km
        FROM wells w
        WHERE 
            w.id != {active_well_id}
            AND ST_DWithin(
                w.location::geography,
                ST_SetSRID(ST_MakePoint({active_well.longitude}, {active_well.latitude}), 4326)::geography,
                {radius_km * 1000}
            )
        ORDER BY distance_km
    """).fetchall()
    
    # Calculate relevance scores
    scored_wells = []
    for well_row in nearby_wells:
        offset_well = db.query(Well).filter(Well.id == well_row.id).first()
        relevance = calculate_relevance_score(active_well, offset_well)
        
        if relevance['total_score'] >= min_relevance:
            scored_wells.append({
                'id': offset_well.id,
                'well_name': offset_well.well_name,
                'latitude': offset_well.latitude,
                'longitude': offset_well.longitude,
                'total_depth_tvd_m': offset_well.total_depth_tvd_m,
                'relevance_score': relevance['total_score'],
                'distance_km': relevance['distance_km'],
                'explanation': relevance['explanation']
            })
    
    # Sort by relevance descending
    scored_wells.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return {
        'active_well': {
            'id': active_well.id,
            'well_name': active_well.well_name,
            'latitude': active_well.latitude,
            'longitude': active_well.longitude
        },
        'offset_wells': scored_wells,
        'total_found': len(scored_wells),
        'search_radius_km': radius_km
    }


# ============================================================================
# Endpoint 2: Get 3D Model Data for Well
# ============================================================================
@router.get("/{well_id}/3dmodel")
async def get_well_3d_model(
    well_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete 3D visualization data for a well:
    - Survey trajectory data
    - Formation tops
    - Casing program
    - Incidents
    - Current bit position (if active)
    """
    
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    
    # Fetch surveys
    surveys = db.query(WellSurvey).filter(
        WellSurvey.well_id == well_id
    ).order_by(WellSurvey.measured_depth_m).all()
    
    # Fetch formation tops
    formations = db.query(FormationTop).filter(
        FormationTop.well_id == well_id
    ).order_by(FormationTop.top_depth_tvd_m).all()
    
    # Fetch casing program
    casings = db.query(CasingProgram).filter(
        CasingProgram.well_id == well_id
    ).order_by(CasingProgram.shoe_depth_tvd_m).all()
    
    # Fetch incidents
    incidents = db.query(Incident).filter(
        Incident.well_id == well_id
    ).order_by(Incident.depth_tvd_m).all()
    
    # Get current depth if active
    current_depth = None
    if well.well_status == 'active':
        latest_realtime = db.query(DrillingRealtime).filter(
            DrillingRealtime.well_id == well_id
        ).order_by(DrillingRealtime.timestamp.desc()).first()
        
        if latest_realtime:
            current_depth = {
                'md': latest_realtime.current_depth_md_m,
                'tvd': latest_realtime.current_depth_tvd_m,
                'timestamp': latest_realtime.timestamp.isoformat()
            }
    
    return {
        'well': {
            'id': well.id,
            'well_name': well.well_name,
            'well_type': well.well_type,
            'total_depth_md_m': well.total_depth_md_m,
            'total_depth_tvd_m': well.total_depth_tvd_m,
            'well_status': well.well_status
        },
        'surveys': [
            {
                'md': s.measured_depth_m,
                'inc': s.inclination_deg,
                'azi': s.azimuth_deg,
                'tvd': s.tvd_m,
                'northing': s.northing_m,
                'easting': s.easting_m
            }
            for s in surveys
        ],
        'formation_tops': [
            {
                'formation_name': f.formation_name,
                'top_depth_md_m': f.top_depth_md_m,
                'top_depth_tvd_m': f.top_depth_tvd_m,
                'lithology_primary': f.lithology_primary,
                'color_hex': f.color_hex,
                'hazard_zone': f.hazard_zone
            }
            for f in formations
        ],
        'casing_program': [
            {
                'casing_type': c.casing_type,
                'outer_diameter_inch': c.outer_diameter_inch,
                'shoe_depth_md_m': c.shoe_depth_md_m,
                'shoe_depth_tvd_m': c.shoe_depth_tvd_m
            }
            for c in casings
        ],
        'incidents': [
            {
                'id': i.id,
                'incident_type': i.incident_type,
                'depth_md_m': i.depth_md_m,
                'depth_tvd_m': i.depth_tvd_m,
                'formation': i.formation,
                'description': i.description,
                'npt_hours': i.npt_hours,
                'severity': i.severity
            }
            for i in incidents
        ],
        'current_depth': current_depth
    }


# ============================================================================
# Endpoint 3: Compare Two Wells (for side-by-side view)
# ============================================================================
@router.get("/compare")
async def compare_wells(
    active_well_id: int,
    offset_well_id: int,
    db: Session = Depends(get_db)
):
    """
    Get 3D model data for both wells in single request (optimization).
    Returns aligned geological correlation.
    """
    
    active_data = await get_well_3d_model(active_well_id, db)
    offset_data = await get_well_3d_model(offset_well_id, db)
    
    # Calculate geological correlation
    correlation = calculate_formation_correlation(
        active_data['formation_tops'],
        offset_data['formation_tops']
    )
    
    return {
        'active_well': active_data,
        'offset_well': offset_data,
        'correlation': correlation
    }
```

---

## 8. Additional Data Documents Needed

### 8.1 Priority Downloads for Module 2

Based on the 3D visualization requirements, you need additional documents with specific data types:

#### Priority 1: Survey Data (CRITICAL)

**What:** Directional survey reports showing well trajectory

**Why:** Without survey data, we can only render vertical wells (boring!)

**Where to find:**
1. **FORGE:** Look for "Directional Survey" or "Survey Report" PDFs
   - Search GDR portal: https://gdr.openei.org
   - Keywords: "survey", "directional", "deviation"

2. **Volve (via Azure):**
   - Path: `/Volve/Wellbore/Surveys/`
   - Look for CSV files with columns: MD, Inc, Azi, TVD

**What to download:**
```
Target: 3-5 survey reports (1 per well)

Example files to look for:
- "78B-32_Directional_Survey.pdf"
- "Well_58-32_Survey_Report.pdf"
- "Final_Survey_Nahorkatiya-A1.csv"
```

**Expected data format:**
```
MD (m) | Inclination (°) | Azimuth (°) | TVD (m)
-------|-----------------|-------------|--------
0      | 0.00            | 0.00        | 0.00
500    | 2.50            | 135.00      | 499.90
1000   | 15.80           | 135.00      | 989.30
```

---

#### Priority 2: Well Completion Reports with Formation Tops Tables

**What:** Final well reports with geological formation tables

**Why:** Need formation names, depths, and lithology for colored layers

**Where to find:**
1. **FORGE:** Well Completion Reports (you have some, need more)
   - Check existing: `Well-16A-Drilling-Summary.pdf`
   - Look for formation tops table in PDF

2. **SODIR CSV Export:**
   - https://factpages.sodir.no/en/wellbore
   - Search: "15/9-F" (Volve field)
   - Export formation tops as CSV

**What to download:**
```
Target: 5-8 WCRs with clear formation tops tables

Example sections to look for in PDFs:
- "Geological Summary"
- "Formation Tops" (table)
- "Stratigraphy"
- "Lithology Log"
```

**Expected data format (from table):**
```
Formation Name    | Top MD (m) | Top TVD (m) | Lithology
------------------|------------|-------------|------------
Namsang Formation | 1850       | 1840        | Sandstone
Tikak Parbat      | 2650       | 2615        | Limestone
Barail Formation  | 3400       | 3312        | Sandstone
```

---

#### Priority 3: Casing Program Tables

**What:** Casing design tables from WCRs or DDRs

**Why:** To render steel casing pipes at correct depths

**Where to find:**
- Same WCRs as above
- Look for "Casing Program" or "Tubular Design" section

**Expected data format:**
```
Casing Type     | OD (inch) | Shoe Depth (m) | Grade
----------------|-----------|----------------|-------
Conductor       | 30"       | 50             | K55
Surface         | 20"       | 600            | K55
Production      | 9-5/8"    | 3650           | P110
```

---

#### Priority 4: Incident Reports (DDRs with Incidents)

**What:** Daily reports mentioning specific incidents at depths

**Why:** To place red markers on 3D model

**Where to find:**
- Existing FORGE DDRs (you have `78B-32-DailyDrillingReports-6-27thru7-31.pdf`)
- Look for pages with "Incident", "NPT", "Lost Circulation", "Stuck Pipe"

**What to extract:**
```
Incident Type      | Depth (m) | Date       | NPT (hrs) | Description
-------------------|-----------|------------|-----------|---------------------------
Lost Circulation   | 3542      | 2019-07-15 | 18        | Total loss, Barail Formation
Stuck Pipe         | 2987      | 2019-06-28 | 36        | Differential sticking
```

---

### 8.2 Should You Download More Documents?

**Answer: YES, download 3-5 more documents for these specific data types:**

| Data Type | Current Status | Need More? | How Many? | Why? |
|-----------|----------------|------------|-----------|------|
| **Survey Data** | ❌ None | ✅ YES | 3-5 reports | Can't render deviated wells without it |
| **Formation Tops** | ⚠️ Partial (1 WCR) | ✅ YES | 5 more WCRs | Need variety for comparison view |
| **Casing Programs** | ⚠️ Partial | ✅ YES | Same WCRs | Need realistic casing strings |
| **Incidents** | ✅ Have some DDRs | ⚠️ Maybe | 2-3 more DDRs | More incidents = better demo |

---

### 8.3 Recommended Downloads (Next 30 Minutes)

**Step 1: Search FORGE GDR for Survey Data**
```powershell
# Open browser to:
https://gdr.openei.org
# Search: "FORGE directional survey"
# Download any PDFs with "survey" in name
```

**Step 2: Export SODIR Formation Tops CSV**
```
1. Go to: https://factpages.sodir.no/en/wellbore
2. Search: "15/9-F"
3. Select wells: 15/9-F-1, 15/9-F-11, 15/9-F-12
4. Click "Export" → Choose "CSV"
5. Save as: data/raw/sodir/volve_formation_tops.csv
```

**Step 3: Download 2-3 More FORGE WCRs**
```powershell
# Search GDR for:
- "FORGE Well 58-32 completion"
- "FORGE Well 56-32 completion"
```

---

## 9. Implementation Roadmap

### 9.1 Sprint Breakdown (4 Sprints × 1 Week Each)

#### Sprint 1: Foundation + 2D Map (Week 1)
**Goal:** Working 2D map with nearby wells display

**Tasks:**
- [ ] Set up database schema (wells, surveys, formations, casings, incidents tables)
- [ ] Implement PostGIS spatial queries
- [ ] Build `/api/wells/nearby` endpoint
- [ ] Implement relevance scoring algorithm
- [ ] Create MapView React component (Leaflet)
- [ ] Add radius slider control
- [ ] Test with 3-5 synthetic wells in Nahorkatiya field

**Deliverable:** Interactive 2D map showing active well + offset wells with relevance colors

**Demo:** "Watch as I drag the radius slider from 10km to 30km - the map updates to show more offset wells, color-coded by geological relevance. Blue wells are in the same fault block and formation as our active well."

---

#### Sprint 2: 3D Visualization Core (Week 2)
**Goal:** Basic 3D well viewer with single well

**Tasks:**
- [ ] Set up React Three Fiber + drei libraries
- [ ] Implement WellTrajectory component (tube geometry from surveys)
- [ ] Implement GeologicalLayers component (colored boxes)
- [ ] Implement CasingStrings component (cylinders)
- [ ] Create DepthAxis (vertical ruler showing meters)
- [ ] Add OrbitControls (mouse rotation/zoom)
- [ ] Build `/api/wells/{id}/3dmodel` endpoint
- [ ] Test with 1 vertical well, then 1 deviated well

**Deliverable:** Single well 3D cross-section with formations, trajectory, casing

**Demo:** "Here's a 3D cross-section of Nahorkatiya-A1. You can see the wellbore deviating from vertical at 2000m, passing through 5 geological formations shown as colored layers. The gray cylinders are casing strings protecting the well."

---

#### Sprint 3: Comparison View + Incidents (Week 3)
**Goal:** Side-by-side well comparison with incident markers

**Tasks:**
- [ ] Implement side-by-side rendering (active + offset)
- [ ] Implement IncidentMarkers component (3D spheres)
- [ ] Add hover tooltips for incidents (react-three/drei Html)
- [ ] Implement LiveBit component (pulsing marker)
- [ ] Build `/api/wells/compare` endpoint
- [ ] Add incident filtering (lost circulation only, stuck pipe only, etc.)
- [ ] Create Blender drill bit model → export as .glb
- [ ] Test comparison with 2 wells from same field

**Deliverable:** Comparison view showing active vs offset well with incident markers

**Demo:** "On the left is our active well Nahorkatiya-A1, currently at 3487m. On the right is offset well A-3, drilled 2 years ago. See that red sphere at 3542m on the offset well? That's a lost circulation event. Our active well is 55 meters away from that same depth in the Barail Formation - this is the proactive warning our system provides."

---

#### Sprint 4: Real-time + Polish (Week 4)
**Goal:** Live bit position + predictive hazard overlay + UI polish

**Tasks:**
- [ ] Implement real-time bit position updates (WebSocket or polling)
- [ ] Add predictive hazard zone highlighting (yellow overlay)
- [ ] Create lithology textures in Blender (sandstone, shale, limestone)
- [ ] Add formation labels (Text3D from drei)
- [ ] Implement map-to-3D integration (click well on map → opens 3D viewer)
- [ ] Add loading states and error handling
- [ ] Performance optimization (LOD, frustum culling)
- [ ] Create user guide documentation

**Deliverable:** Complete Module 2 with all features integrated

**Demo:** "As the bit advances in real-time, watch the green pulsing marker move down the wellbore. Notice the yellow highlighted zone ahead? That's a predicted hazard zone based on historical incidents from 3 offset wells. The system gives us 30-60 minutes of lead time to prepare mitigation measures."

---

### 9.2 Testing Checklist

#### Unit Tests
- [ ] Relevance scoring algorithm (test with known well pairs)
- [ ] Haversine distance calculation (validate against known distances)
- [ ] Survey data conversion (MD/Inc/Azi → TVD/Northing/Easting)
- [ ] Formation top validation (depths increasing, no overlaps)

#### Integration Tests
- [ ] API endpoint: `/api/wells/nearby` returns correct wells within radius
- [ ] API endpoint: `/api/wells/{id}/3dmodel` returns complete data
- [ ] PostGIS spatial query performance (<500ms for 100 wells)
- [ ] WebSocket real-time updates (bit position syncs within 1 second)

#### Visual Tests
- [ ] 3D wellbore trajectory matches survey data (manual validation)
- [ ] Formation layers align with TVD depths (check against WCR)
- [ ] Incident markers at correct depths (cross-reference DDR)
- [ ] Casing shoe depths match specification

#### User Acceptance Tests
- [ ] Geologist can identify relevant offset wells in <30 seconds
- [ ] Engineer can compare two wells and spot differences in <2 minutes
- [ ] System responds to radius changes in <500ms
- [ ] 3D viewer remains smooth (>30 FPS) during rotation

---

## 10. Technology Stack Summary

### Frontend
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 18.x | UI components |
| 3D Engine | Three.js | r160+ | WebGL 3D rendering |
| 3D React Bridge | @react-three/fiber | 8.x | Declarative Three.js in React |
| 3D Helpers | @react-three/drei | 9.x | OrbitControls, Text3D, Html, etc. |
| 2D Map | React Leaflet | 4.x | Interactive geospatial map |
| Map Tiles | CARTO Dark | - | Dark mode basemap for control rooms |
| State Management | Zustand | 4.x | Lightweight state (well selection, radius) |
| HTTP Client | Axios | 1.x | API requests |
| Real-time | Socket.IO Client | 4.x | Live bit position updates |

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | RESTful API + WebSocket support |
| Database | PostgreSQL 15 | Relational data storage |
| Spatial Extension | PostGIS | Geospatial queries (ST_DWithin, etc.) |
| ORM | SQLAlchemy | Database models and queries |
| Real-time | Socket.IO | Broadcast bit position updates |

### 3D Asset Creation
| Tool | Purpose |
|------|---------|
| Blender 4.0+ | Create drill bit, BOP, rig equipment models |
| Blender Export | .glb/.gltf format (optimized for Three.js) |
| Texture Paint | Create sandstone, shale, limestone textures |

### Development Tools
| Tool | Purpose |
|------|---------|
| TypeScript | Type-safe frontend code |
| Python 3.11+ | Backend development |
| Docker | Containerization for deployment |
| Vite | Fast frontend build tool |
| pytest | Backend testing |
| Vitest | Frontend testing |

---

## 11. Success Criteria

### Functional Requirements
✅ Module 2 must display interactive 2D map with active well + offset wells  
✅ Must filter wells by user-defined radius (5-50 km)  
✅ Must color-code wells by geological relevance (not just distance)  
✅ Must render 3D cross-section view for selected wells  
✅ Must show side-by-side comparison (active vs offset)  
✅ Must display geological formation layers with colors  
✅ Must render wellbore trajectories (vertical and deviated)  
✅ Must show casing strings at correct depths  
✅ Must place incident markers at exact depths  
✅ Must show live bit position for active well  
✅ Must highlight predictive hazard zones ahead of bit  

### Performance Requirements
✅ Map radius update: <500ms  
✅ 3D scene rendering: >30 FPS during rotation  
✅ API response time: <2 seconds for 3D model data  
✅ Spatial query: <1 second for 100 wells within 50km  

### User Experience Requirements
✅ Engineer can identify top 3 relevant offset wells in <30 seconds  
✅ 3D viewer controls are intuitive (no training needed)  
✅ Incident tooltips provide actionable information  
✅ System works in control room environment (dark mode, large screen)  

### Demo Requirements (Hackathon Judging)
✅ Live demo shows real-time bit advancing  
✅ Demo highlights proactive warning (approaching hazard zone)  
✅ Visually impressive (judges say "wow, that's cool")  
✅ Explains value proposition in <2 minutes  

---

## 12. Next Steps (Action Items for You)

### This Week:
1. ✅ **Read this plan document** (you're doing it!)
2. 🔲 **Download 3-5 more documents:**
   - 3 Survey reports (directional drilling data)
   - 3 WCRs with formation tops tables
   - Export SODIR CSV for validation
3. 🔲 **Set up database schema** (run SQL scripts in `backend/models/`)
4. 🔲 **Generate 5 synthetic OIL India wells** with realistic data:
   - Nahorkatiya-A1 (active, 3487m current depth)
   - Nahorkatiya-A3 (offset, 8 km away, lost circulation incident)
   - Nahorkatiya-A5, Moran-B2, Digboi-C1
5. 🔲 **Start Sprint 1 tasks** (2D map implementation)

### Next Week:
6. 🔲 Install Blender and create basic drill bit model
7. 🔲 Begin Sprint 2 (3D visualization core)
8. 🔲 Test with real FORGE survey data

### Coordination with Teammate:
- **Dependency:** Module 1 (OCR) must extract surveys, formations, casings, incidents
- **Data Format:** Agree on JSON schema for extracted data
- **Timeline:** Need Module 1 output by end of Sprint 2

---

## 13. Questions & Clarifications

**Q: Do we really need Blender? Can't we just use simple shapes?**  
A: For MVP (Sprints 1-2), simple Three.js shapes (cones, cylinders) are fine. Blender becomes valuable in Sprint 4 for polish and "wow factor" in demo. Judges appreciate attention to detail.

**Q: How do we handle wells without survey data (vertical wells)?**  
A: Generate straight-line trajectory:
```javascript
surveys = [
  { md: 0, inc: 0, azi: 0, tvd: 0, northing: 0, easting: 0 },
  { md: totalDepth, inc: 0, azi: 0, tvd: totalDepth, northing: 0, easting: 0 }
]
```

**Q: What if we can't download more FORGE documents?**  
A: **Plan B:** Generate all synthetic data based on OIL India publications:
- Use DGH India formation depth windows
- Reference OIL India technical papers for realistic incidents
- Create synthetic survey data with realistic inclination curves

**Q: Three.js performance issues with many wells?**  
A: **Solution:** Only render 2 wells at a time in 3D viewer (active + selected offset). Map view can show 100+ as simple markers.

**Q: How to sync real-time bit position in demo?**  
A: **Mock Implementation:**
```javascript
// Simulate drilling progress: 15 m/hr
setInterval(() => {
  currentDepth += 0.25;  // 0.25m per minute
  socket.emit('depth_update', { well_id: 1, depth: currentDepth });
}, 60000);
```

---

## Appendix: OIL India Formation Reference

**Upper Assam Basin Stratigraphy (for synthetic data):**

| Formation Name | Age | Depth Range (m) | Lithology | Hazards |
|----------------|-----|-----------------|-----------|---------|
| Girujan Clay | Pliocene | 200-1800 | Shale | Unstable, sloughing |
| Namsang | Miocene | 1800-2600 | Sandstone | Gas kicks |
| Tikak Parbat | Oligocene | 2600-3100 | Limestone | Lost circulation (fractures) |
| Kopili | Eocene | 3100-3400 | Shale | Differential sticking |
| **Barail** | Oligocene | **3400-3750** | **Sandstone** | **Lost circulation (HIGH RISK)** |
| Tipam | Miocene | 3750-4200 | Sandstone | Overpressure zones |
| Lakadong | Paleocene | 4200+ | Sandstone | Reservoir section |

**Use these for generating realistic synthetic well data!**

---

## Document Status

- **Version:** 1.0  
- **Status:** ✅ Complete - Ready for Implementation  
- **Next Review:** After Sprint 1 completion  
- **Contact:** Harshal (Module 2 Owner)  

---

**Let's build something amazing! 🚀**
