# Competitor Repository Audit: tech-nitin-wellwise

## 1. Repository Metadata
- **Repository**: `tech-nitin-wellwise`
- **URL**: `https://github.com/tech-nitin/wellwise.git`
- **Owner**: tech-nitin
- **Project**: WellWise — AI-Powered Nearby Wells Intelligence and 3D Well Explorer (SIH 2026 PS 26121)
- **Category**: **Active Direct Competitor** (Latest Commit: 2026-09-22 — 6 days ago)
- **Relevance**: High (Specialized 3D geological layer and wellbore visualization in Three.js)
- **Primary Language**: JavaScript (Three.js, GSAP, CSS2DRenderer), HTML5
- **Files Inspected**: 42 files across 6 development phases (`Well_simulation/drilling-well-explorer-*`).

---

## 2. Architecture & Tech Stack Reconstructed
```
[3D Subsurface Viewport (`drilling-well-explorer-final/src/main.js`)]
   ├── Three.js WebGL Renderer (ACESFilmicToneMapping, PCFSoftShadowMap)
   ├── OrbitControls (Subsurface rotation, zoom, damping)
   ├── CSS2DRenderer & CSS2DObject (HTML/CSS callout badges pinned to 3D depths)
   ├── GSAP Animations (Smooth camera flight transitions to depth markers)
   └── Subsurface Groups:
         ├── `geoGroup` (3D stratified geological formation surfaces)
         ├── `world` (Surface rig structure & wellhead markers)
         └── `wellPath` (3D wellbore trajectory cylinders)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **3D Subsurface Geology** | ✅ **VERIFIED** | `src/main.js` L20-60 | Multi-layer 3D geological layer rendering in Three.js with realistic lighting and fog. |
| **Interactive Trajectory Orbit**| ✅ **VERIFIED** | `src/main.js` OrbitControls | Free-form 3D camera navigation around wellbore trajectories. |
| **3D Callout Annotations** | ✅ **VERIFIED** | `src/main.js` CSS2DRenderer | High-density 2D DOM label cards anchored directly to 3D spatial coordinates. |
| **Smooth Camera Transitions**| ✅ **VERIFIED** | `src/main.js` (GSAP) | Camera transitions smoothly to critical hazard depths when selected. |
| **Backend / REST API** | ❌ **NOT FOUND** | N/A | Pure client-side 3D simulation explorer; lacks FastAPI/Python backend. |
| **Database & GIS** | ❌ **NOT FOUND** | N/A | No PostGIS or relational database. |
| **ML & RAG Intelligence** | ❌ **NOT FOUND** | N/A | Pure graphical visualization without NLP or predictive models. |

---

## 4. Code-Level Investigation & Observations
1. **Outstanding UI / 3D Inspiration**:
   - `tech-nitin-wellwise` has the most visually compelling **3D subsurface geological rendering** among all competitors.
   - The combination of Three.js, CSS2D label overlays, and GSAP camera zooming provides an exceptional visual experience.
2. **Identified Technical Limitations**:
   - It is currently an isolated 3D frontend demo without a real backend, database, or machine learning models.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt as Code Inspiration**:
  - Incorporate the Three.js + CSS2D callout technique for our 3D Subsurface Well Visualizer tab to show the active trajectory penetrating geological formation planes.
- **To Complete the Full System**:
  - Connect the 3D visualizer to our FastAPI + PostGIS backend and live telemetry stream.
