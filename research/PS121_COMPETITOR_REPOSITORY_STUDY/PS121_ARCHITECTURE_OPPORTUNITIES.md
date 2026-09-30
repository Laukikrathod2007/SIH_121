# PS 121 — Architectural Opportunities & White Space Discovery

This document synthesizes the architectural white space discovered during our code-level audit of 11 candidate repositories, outlining the complete end-to-end architecture that combines geospatial intelligence, stratigraphic physics, multi-modal PDF extraction, and evidence-grounded reasoning for **PS 121 (SIH 26121 — eRTMAC-NWIS)**.

---

## 1. Technical White Space Identified

Across all audited competitor repositories, we identified three major architectural disconnects:
1. **The Spatial-Geological Disconnect**: Systems with GIS (e.g. `PetrolQ`) calculate surface 2D distance without 3D well trajectories or structural fault blocks.
2. **The Document-Physics Disconnect**: Systems with advanced document RAG (e.g. `DrillMind`, `DDR_UTAH_FORGE`) treat drilling reports purely as text strings, completely detached from pore pressure, mud weight, and rock mechanics.
3. **The Post-Mortem vs Predictive Disconnect**: Almost all systems require an engineer to manually ask questions after a problem occurs, rather than autonomously projecting upcoming risks ahead of the active drill bit.

**The Architectural Opportunity for PS 121**: Unify these disconnected domains into a single, closed-loop intelligence pipeline.

---

## 2. Complete End-to-End Intelligence Chain

```
[ Active Rig Telemetry / Planned Well Path ]
   ├── WGS84 Wellhead (Lat, Lon, KB Elevation)
   ├── 3D Survey (MD, Inclination, Azimuth)
   └── Real-time Drilling Parameters (Bit Depth, ROP, WOB, RPM, Torque, SPP, Mud Weight In/Out, Flow)
        │
        ▼
[ Layer 1: Geospatial & Structural Fault-Block Gating ]
   ├── PostGIS Spatial Radius Query (`ST_DWithin`)
   ├── Fault Barrier Intersection Filter (`ST_Crosses` on Fault Polygons)
   └── Returns: Top 3–5 Structurally Compatible Offset Wells
        │
        ▼
[ Layer 2: 3D Trajectory & Stratigraphic Normalization ($\xi$-Sync) ]
   ├── Minimum Curvature Trajectory Calculation: $(MD, Inc, Az) \to (TVD, TVDSS, Northing, Easting)$
   ├── Regional Structural Dip & True Stratigraphic Thickness Alignment
   ├── Dimensionless Coordinate Mapping: $\xi(d) = \frac{d_{\text{tvdss}} - Z_{\text{top}}}{Z_{\text{base}} - Z_{\text{top}}}$
   └── Returns: Normalized Offset Well Depth Intervals ($\xi \pm 0.1$)
        │
        ▼
[ Layer 3: Dynamic Ahead-of-the-Bit Lookahead Corridor ]
   ├── Projects forward corridor: $[d_{\text{tvdss}}, d_{\text{tvdss}} + 100\text{m}]$ along planned well path
   ├── Intersects corridor with offset well $\xi$-intervals
   └── Identifies upcoming formation tops, casing shoe depths, and known loss/kick horizons
        │
        ▼
[ Layer 4: Multi-Modal Hybrid RAG & Knowledge Graph Engine ]
   ├── Dense Vector Similarity (pgvector on 500+ page EOWR/DDR chunks)
   ├── Sparse BM25 Lexical Booster on drilling keywords (LCM, packoff, gas kick, overpull)
   ├── Dynamic $\Omega$-Reranking combining Semantic + Stratigraphic $\xi$ proximity + Hazard severity
   └── Entity Graph Query (NetworkX / Postgres Property Graph connecting Well $\to$ Formation $\to$ Hazard $\to$ Resolution)
        │
        ▼
[ Layer 5: Subsurface Physics & Operating Margin Verification ]
   ├── Eaton Pore Pressure Gradient ($PP$) & Fracture Gradient ($FG$) Calculation
   ├── Real-time Operating Margins: $\text{Trip Margin} = MW_{\text{act}} - PP, \quad \text{Loss Margin} = FG - ECD$
   └── Anomaly Detection on Live Telemetry (FastDTW sequence divergence, MSE spikes)
        │
        ▼
[ Layer 6: Grounded Engineering Recommendation & Visual Provenance ]
   ├── Structured Copilot Recommendation with Specific Operating Parameters (RPM, WOB, Mud Weight, LCM formulation)
   ├── Confidence Score & Risk Gauge (Kick, Lost Circulation, Stuck Pipe, Wellbore Instability)
   └── 1-Click Interactive PDF Provenance: Synchronized PDF viewer highlighting exact source text/table in glowing amber
```

---

## 3. High-Value "WOW" Engineering Integrations

### 3.1 Integrated 3D Subsurface & Trajectory Visualizer
- **Implementation**: Combine MapLibre GL with a Three.js / Plotly 3D subsurface viewer.
- **Visual Impact**: When an active well is selected, the map smoothly tilts into a 3D subsurface canvas displaying the active trajectory alongside offset well paths, formation horizon surfaces (Tipam, Barail, Kopili), and glowing red 3D hazard spheres marking historical stuck pipe or loss events at their exact 3D spatial locations.

### 3.2 Dual-View Ahead-of-Bit Projection & Risk Corridor
- **Implementation**: As the user drags the bit depth slider or replays live telemetry, a synchronized "Ahead-of-Bit Corridor" card updates in real time, showing:
  - Estimated depth to next formation top (with $\pm 15\text{m}$ geological uncertainty).
  - Historical offset events within the next 100m corridor.
  - Dynamic pore pressure vs mud weight trip margin gauge.
  - Recommended contingency actions (e.g. "Prepare 20 bbls of 35 ppb coarse mica/nut-plug LCM pill prior to drilling into Tipam Sandstone at 2,410m TVDSS").

### 3.3 Synchronized PDF Document Inspector with Bounding-Box Overlays
- **Implementation**: Clicking any citation badge opens a side-by-side split screen with the original multi-page EOWR/DDR PDF, automatically scrolling to the relevant page and highlighting the exact table row or narrative sentence with a high-contrast amber bounding box.

---

## 4. Architectural Summary

By implementing this complete chain, PS 121 will be the **only** platform that unifies:
1. **Structural Geology & GIS** (PostGIS + Fault Blocks)
2. **3D Wellbore Geometry & Stratigraphy** ($\xi$-Depth Normalization)
3. **Petroleum Engineering Physics** (Eaton PPFG + Mud Margins + Hydraulics)
4. **Advanced Document AI** (Dual-Engine Layout Extraction + pgvector Hybrid Search)
5. **Auditable Decision Support** (1-Click PDF Bounding Box Provenance)
