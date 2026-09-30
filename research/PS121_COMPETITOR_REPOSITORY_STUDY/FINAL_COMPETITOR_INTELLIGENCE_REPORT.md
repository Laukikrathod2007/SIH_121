# PS 121 — Comprehensive Competitor Intelligence, Codebase Audit & Architectural Roadmap

**Problem Statement**: SIH 26121 — eRTMAC-NWIS: AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations  
**Sponsoring Organization**: Oil India Limited (OIL)  
**Study Date**: September 2026  
**Status**: Pre-Implementation Research & Target Architectural Specification  

---

## Table of Contents
- [PS 121 — Comprehensive Competitor Intelligence, Codebase Audit \& Architectural Roadmap](#ps-121--comprehensive-competitor-intelligence-codebase-audit--architectural-roadmap)
  - [Table of Contents](#table-of-contents)
  - [1. Executive Summary \& Scope](#1-executive-summary--scope)
    - [Primary Ground-Truth Findings:](#primary-ground-truth-findings)
  - [2. Curated Competitor Inventory \& Commit Recency](#2-curated-competitor-inventory--commit-recency)
  - [3. Comprehensive Capability \& Verification Matrix](#3-comprehensive-capability--verification-matrix)
    - [Legend:](#legend)
  - [4. Code-Level Gap Analysis \& Technical Limitations](#4-code-level-gap-analysis--technical-limitations)
    - [Gap 1: Absence of Stratigraphic Normalization \& Dip-Aware Depth Slicing](#gap-1-absence-of-stratigraphic-normalization--dip-aware-depth-slicing)
    - [Gap 2: Geospatial Proximity Without Structural Fault-Block Gating](#gap-2-geospatial-proximity-without-structural-fault-block-gating)
    - [Gap 3: Synthetic Data Fallbacks in Log Correlation](#gap-3-synthetic-data-fallbacks-in-log-correlation)
    - [Gap 4: Retrospective Search vs Forward Predictive Lookahead](#gap-4-retrospective-search-vs-forward-predictive-lookahead)
    - [Gap 5: Text Citations vs Interactive PDF Bounding-Box Overlays](#gap-5-text-citations-vs-interactive-pdf-bounding-box-overlays)
  - [5. Comparative Technology Stack Evaluation](#5-comparative-technology-stack-evaluation)
  - [6. Commoditized Features (What We Should NOT Build)](#6-commoditized-features-what-we-should-not-build)
  - [7. Defensible USPs \& Engineering Differentiators for PS 121](#7-defensible-usps--engineering-differentiators-for-ps-121)
  - [8. Proposed End-to-End Target Architecture](#8-proposed-end-to-end-target-architecture)
  - [9. Detailed Repository-by-Repository Code Audits](#9-detailed-repository-by-repository-code-audits)

---

## 1. Executive Summary & Scope

To establish an engineering foundation for **PS 121 (SIH 26121 — eRTMAC-NWIS)**, we conducted a repository-first code audit across GitHub to analyze what existing teams have built, what works, what is mock or prototype data, and what open technical challenges remain unaddressed.

A total of **27 repositories** were discovered and downloaded into an isolated research workspace (`research/competitors/`). After filtering out empty scaffolds, static HTML mockups, and peripheral hardware tools, **12 high-value competitor and domain benchmark codebases** were subjected to deep source code analysis.

### Primary Ground-Truth Findings:
1. **The Stratigraphic Dip Blindness (100% of Competitors)**:  
   Every competitor repository correlates offset wells on raw **Measured Depth (MD)** or static vertical depth slices ($\pm 100\text{m}$). In regional structural dip settings ($3^\circ-15^\circ$ SE across the Upper Assam Shelf), this causes severe geological interval misalignment.
2. **Geospatial Distance vs Structural Fault Blocks**:  
   All existing geospatial implementations compute simple 2D surface distance (Haversine), failing to account for sealing thrust faults that isolate reservoir pressure compartments.
3. **Passive Post-Mortem Search vs Forward Predictive Lookahead**:  
   Competitor systems operate as retrospective Q&A search tools rather than autonomous, forward-looking monitors that project upcoming risks (+50m to +200m) ahead of the active bit.
4. **Disconnection Between Document AI & Drilling Physics**:  
   Repositories with advanced RAG treat drilling reports purely as unstructured text strings without calculating physical pore pressure ($PP$), fracture gradients ($FG$), or dynamic mud window operating margins.
5. **Lack of Traceable Visual PDF Provenance**:  
   Existing solutions output text answers with file name strings; none provide synchronized, 1-click PDF canvas viewers with pixel-exact bounding-box highlight overlays on source EOWR/DDR documents.

---

## 2. Curated Competitor Inventory & Commit Recency

| Repository Name | Clone Path | Source URL | Latest Commit | Code Files | Primary Architecture |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **invo-coder19/Drill-IQ** | `direct/invo-coder19-Drill-IQ` | [GitHub](https://github.com/invo-coder19/Drill-IQ) | 2026-09-27 | 64 | React 19, Vite, TanStack Router, TypeScript |
| **pallavi-a11y/eRTMAC-NWIS** | `direct/pallavi-eRTMAC-NWIS` | [GitHub](https://github.com/pallavi-a11y/eRTMAC-NWIS) | 2026-09-27 | 42 | FastAPI, Qdrant, pypdfium2, Qwen2.5-VL, OpenCV |
| **dhanwanth-dh/eRTMAC--NWIS** | `direct/dhanwanth-eRTMAC-NWIS` | [GitHub](https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support) | 2026-09-26 | 32 | FastAPI, 5 XGBoost Models, Isolation Forest, React 19 |
| **thor11223344/PetrolQ** | `direct/PetrolQ` | [GitHub](https://github.com/thor11223344/PetrolQ) | 2026-09-24 | 36 | FastAPI, PostGIS, pgvector, MapLibre GL, Eaton PPFG |
| **vidhiii1711/eRTMAC-NWIS** *(Team DrillX)* | `direct/vidhiii1711-eRTMAC-NWIS` | [GitHub](https://github.com/vidhiii1711/eRTMAC-NWIS) | 2026-09-23 | 111 | Node.js, Express, React, MongoDB (Vercel Deployed) |
| **tech-nitin/wellwise** | `direct/tech-nitin-wellwise` | [GitHub](https://github.com/tech-nitin/wellwise) | 2026-09-22 | 17 | JavaScript, Three.js, GSAP, CSS2DRenderer |
| **n3ssdub3y/SIH_2026_PLANNS** | `direct/SIH_2026_PLANNS` | [GitHub](https://github.com/n3ssdub3y/SIH_2026_PLANNS) | 2026-09-22 | 18 | FastAPI, Flask, ChromaDB, NetworkX, FastDTW |
| **rudrachauhan12999/eRTMAC-NWIS** | `direct/rudrachauhan12999-eRTMAC-NWIS` | [GitHub](https://github.com/rudrachauhan12999/eRTMAC-NWIS) | 2026-09-20 | 121 | FastAPI, Motor, MongoDB, React, Vite |
| **Physics0070/nwis** | `direct/Physics0070-nwis` | [GitHub](https://github.com/Physics0070/nwis) | 2026-09-08 | 34 | FastAPI, PostgreSQL, SQLAlchemy, Alembic, React |
| **suryanshkota07-oss/AROH** | `direct/suryanshkota07-AROH` | [GitHub](https://github.com/suryanshkota07-oss/AROH-drilling-intelligence) | 2026-08-29 | 52 | FastAPI, Python, NumPy, Pydantic |
| **djimrastephane/DDR_UTAH_FORGE** | `drilling/DDR_UTAH_FORGE` | [GitHub](https://github.com/djimrastephane/DDR_UTAH_FORGE) | 2026-03-12 | 108 | Python, PyMuPDF, OpenCV, NetworkX, ChromaDB |
| **ArokyaMatthew/DrillMind** | `direct/DrillMind` | [GitHub](https://github.com/ArokyaMatthew/DrillMind) | 2026-06-02 | 48 | FastAPI, rank-bm25, ChromaDB, PyTorch LSTM |

---

## 3. Comprehensive Capability & Verification Matrix

### Legend:
- ✅ **Verified**: Implemented in source code with functional logic.
- 🟡 **Partial / Mock**: Rule-based heuristic, incomplete logic, or relying on static/synthetic mock data.
- ❌ **Not Found**: Feature is absent from the repository.

| Capability / Dimension | dhanwanth | Physics0070 | vidhiii1711 | PetrolQ | pallavi | DrillMind | DDR_UTAH_FORGE | Proposed PS 121 Target Design |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Nearby Well Discovery** | ✅ (6-factor) | ✅ (Postgres) | ✅ (Mongo) | ✅ (PostGIS) | ✅ (Geopy) | ❌ | ❌ | **3D Subsurface Proximity + Fault-Block Gating** |
| **GIS & Subsurface Mapping** | 🟡 (Leaflet) | 🟡 (2D plot) | 🟡 (2D map) | ✅ (MapLibre) | 🟡 (Leaflet) | ❌ | 🟡 (2D schematic)| **MapLibre GL 2D/3D + Three.js Subsurface Formations** |
| **3D Trajectory Calculation** | 🟡 (Raw depth)| 🟡 (Raw depth)| 🟡 (MD/TVD) | 🟡 (Min Curv)| ❌ | ❌ | ❌ | **Minimum Curvature $(MD,Inc,Az) \to (TVD,TVDSS,N,E,DLS)$** |
| **Historical Ingestion Engine**| 🟡 (CSV) | ✅ (Doc profile)| 🟡 (JSON seed)| 🟡 (PyMuPDF) | ✅ (Qwen-VL) | ✅ (WITSML/Alpaca)| ✅ (Deep PDF) | **Dual-Engine: High-Speed PyMuPDF + OpenCV Table Segmenter** |
| **Scanned OCR & Table Layout** | ❌ | 🟡 (Basic OCR)| ❌ | 🟡 (EasyOCR) | ✅ (pypdfium+CV)| ❌ | ✅ (OCR Fallback)| **Hierarchical Table Cell Geometry + Confidence Gating** |
| **Drilling Event / NPT Model** | ✅ (5 XGBoost)| ✅ (Event DB) | ✅ (25-param) | ✅ (Regex) | ✅ (VLM parser)| ✅ (Keywords) | ✅ (14-class NPT)| **IADC / BSEE Normalized Drilling Ontology + Severity Scoring** |
| **Hybrid RAG Retrieval** | 🟡 (Summary) | ✅ (Passage) | 🟡 (LLM prompt)| ✅ (AHP RAG) | ✅ (Qdrant) | ✅ (RRF BM25+Chroma)| 🟡 (Router) | **Dynamic $\Omega$-Reranking (Dense Vector + BM25 + Stratigraphic $\xi$)** |
| **Stratigraphic $\xi$ Normalization**| ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **Dimensionless Depth $\xi(d) = \frac{d_{tvdss}-Top}{Thickness} \in [0,1]$ across Dip** |
| **Ahead-of-Bit Lookahead Corridor**| 🟡 (Rule check)| 🟡 (Depth sample)| 🟡 (Warning URL)| 🟡 (Static Dict)| ❌ | ❌ | ❌ | **Autonomous $+50\text{m}$ to $+200\text{m}$ Predictive Risk Projection** |
| **PPFG Mud Window & Hydraulics** | 🟡 (Telemetry)| ❌ | 🟡 (PP col) | ✅ (Eaton PPFG)| ❌ | ❌ | ❌ | **Dynamic Mud Window Margins ($MW_{act}-PP, FG-ECD$)** |
| **Decision Logging / Audit Trail**| 🟡 (Alerts) | ✅ (EngineerAction)| ✅ (DecisionLog)| 🟡 (Dossier) | 🟡 (Review UI)| 🟡 (Alert store)| 🟡 (Artifacts) | **Structured Audit Trail Recording Operator Actions & Rationale** |
| **1-Click Visual PDF Provenance**| ❌ | 🟡 (Passage) | ❌ | 🟡 (Text cite)| ✅ (Page crops)| 🟡 (Chunk ID) | ✅ (Page headers)| **Interactive PDF Canvas with Glowing Bounding-Box Overlays** |
| **Real-Time Telemetry & Anomaly**| ✅ (IsoForest)| ✅ (Replay) | ✅ (Drilling stream)| 🟡 (Simulator)| ❌ | ✅ (PyTorch LSTM)| ❌ | **Multi-Channel Anomaly Detection + FastDTW Alignment** |

---

## 4. Code-Level Gap Analysis & Technical Limitations

### Gap 1: Absence of Stratigraphic Normalization & Dip-Aware Depth Slicing
- **Evidence**:
  - `SIH_2026_PLANNS`: `NLP/nwis-sentinel/backend/app/services/similarity_engine.py` Lines 25–40 ($1 - \frac{|\Delta MD|}{500}$).
  - `DrillMind`: `src/drillmind/copilot/context_builder.py` Lines 60–85 (flat $\pm 100\text{m}$ Measured Depth window).
  - `PetrolQ`: `backend/api/lookahead.py` Lines 15–45 (static hardcoded dictionary `WELL_FORMATION_HORIZONS`).
  - `dhanwanth-dh`: `backend/services/similarity_service.py` Lines 35–40 (total depth difference $|TD_{\text{act}} - TD_{\text{off}}|$).
- **Technical Challenge**: In structural thrust belts (Assam-Arakan basin), formations dip at $3^\circ-15^\circ$ SE and vary significantly in thickness. A bit at 2,400m MD in Well A may be drilling permeable Tipam Sandstone, while in Well B (2 km away) 2,400m MD has already entered the overpressured Barail Coal-Shale. Comparing raw depths produces false-analog matches.
- **PS 121 Target Specification**: Dimensionless interval coordinate transformation:
  $$\xi(d) = \frac{d_{\text{tvdss}} - Z_{\text{top}}}{Z_{\text{base}} - Z_{\text{top}}} \in [0.0, 1.0]$$
  Analog search queries offset events at $\xi_{\text{offset}} \in [\xi_{\text{act}} - 0.1, \xi_{\text{act}} + 0.1]$, guaranteeing true geological interval equivalence.

### Gap 2: Geospatial Proximity Without Structural Fault-Block Gating
- **Evidence**:
  - `PetrolQ`: `backend/models.py` (`ST_DWithin` on surface wellhead).
  - `dhanwanth-dh`: `backend/services/nearby_well_service.py` (2D Haversine formula).
  - `suryanshkota07-AROH`: `ai/analogue_matching.py` (2D Euclidean proximity score).
- **Technical Challenge**: In compartmentalized reservoirs with sealing faults (e.g. Naga Thrust, Disang Thrust), an offset well 600m away across a sealing fault has completely disconnected pressure and fluid regimes compared to a well 2,500m away within the same structural compartment.
- **PS 121 Target Specification**: PostGIS structural fault polygon intersection (`ST_Crosses`). If an active-to-offset baseline intersects a sealing fault polygon, apply a structural barrier penalty ($\beta_{\text{fault}} = 0.2$).

### Gap 3: Synthetic Data Fallbacks in Log Correlation
- **Evidence**:
  - `PetrolQ`: `backend/api/correlate.py` Lines 30–65:
    ```python
    def synthesize_gr_logs(well_id: str, tvd_max: float = 3500.0):
        # Generates synthetic GR log curve based on regional stratigraphy
        depths = np.linspace(100.0, tvd_max, 120)
        val = 45.0 + 15.0 * np.sin(z / 40.0) + rng.uniform(-5, 5)
    ```
- **Technical Challenge**: When LAS log files are missing, generating trigonometric sine waves undermines domain credibility.
- **PS 121 Target Specification**: Ingest and parse real industry-standard LAS 2.0 / DLIS well log files with automated curve alias standardization (`GR`, `CGR` $\to$ Standard Gamma Ray) and FastDTW alignment on real geological curves.

### Gap 4: Retrospective Search vs Forward Predictive Lookahead
- **Evidence**:
  - `DrillMind`, `pallavi-a11y`, `invo-coder19`: Platforms require engineers to type search queries after an incident occurs.
- **Technical Challenge**: During active operations, rig engineers cannot manually search archives.
- **PS 121 Target Specification**: Autonomous forward corridor engine projecting $[d_{\text{tvdss}}, d_{\text{tvdss}} + 100\text{m}]$ ahead of the bit on every depth update, scanning offset well $\xi$-intervals to pre-warn of upcoming mud loss zones and overpressured transitions.

### Gap 5: Text Citations vs Interactive PDF Bounding-Box Overlays
- **Evidence**:
  - `SIH_2026_PLANNS`, `PetrolQ`, `Physics0070`: Output plain text string citations (e.g. `"Source: Well_A1_EOWR.pdf, Page 42"`).
- **Technical Challenge**: Rig superintendents and drilling engineers require visual auditability before acting on AI recommendations.
- **PS 121 Target Specification**: Preserve normalized bounding-box coordinates $(x_0, y_0, x_1, y_1)$ during ingestion. Clicking a recommendation opens the original 500-page PDF in a synchronized canvas viewer, highlighting the exact casing table or mud loss excerpt in glowing amber.

---

## 5. Comparative Technology Stack Evaluation

| Layer | Audited Competitor Best-Practices | Limitations in Other Repositories | Recommended PS 121 Stack |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | **React 19 + Vite + TypeScript + Tailwind CSS** (`invo-coder19`, `PetrolQ`, `vidhiii1711`) | Streamlit (`DDR_UTAH_FORGE`) has sluggish UI state rerenders during live telemetry streaming. | **React 19 + Vite + TypeScript + Tailwind CSS + Lucide Icons** |
| **3D Subsurface View**| **Three.js + CSS2DRenderer** (`tech-nitin/wellwise`) with camera OrbitControls. | 2D Leaflet (`pallavi`, `tarumishra`) cannot visualize deviated 3D wellbore paths. | **MapLibre GL (2D/3D Map) + Three.js (3D Subsurface Well Visualizer)** |
| **Backend API** | **FastAPI Asynchronous REST + WebSockets** (`Physics0070`, `dhanwanth-dh`, `DrillMind`) | Flask / Synchronous Node blocks under heavy telemetry payloads. | **FastAPI (Python 3.11+) + Uvicorn + WebSockets** |
| **Relational & GIS DB**| **PostgreSQL 16 + PostGIS** (`PetrolQ`, `Physics0070`) with Alembic migrations. | Flat CSVs (`dhanwanth`) or SQLite (`ChromaDB`) lack spatial indexing and concurrent writes. | **PostgreSQL 16 + PostGIS (Spatial Indexing: GIST)** |
| **Vector Database** | **pgvector** (`PetrolQ`) co-located inside PostgreSQL tables. | Isolated ChromaDB/FAISS requires slow multi-step in-memory Python joins for metadata filtering. | **pgvector (Unified Relational + Spatial + Vector in Postgres)** |
| **Sparse / Lexical Search**| **BM25 (`rank-bm25`)** with Reciprocal Rank Fusion ($k=60$) (`DrillMind`). | Pure dense vector search fails on specialized acronyms (e.g. `BHA`, `LCM`, `LOT`, `POOH`). | **Hybrid PostgreSQL Full-Text Search (tsvector/BM25) + pgvector RRF** |
| **Document Ingestion** | **Dual-Engine PyMuPDF + OpenCV Table Segmentation** (`DDR_UTAH_FORGE`). | Full VLM per page (`pallavi`) takes 15s/page (hours for 500-page EOWR). | **High-Speed PyMuPDF Layout Extractor + OpenCV Table Line Detector** |
| **Machine Learning** | **Multi-Hazard XGBoost Ensemble + Isolation Forest** (`dhanwanth-dh`). | Single generic risk score fails to differentiate stuck pipe from gas kicks. | **XGBoost 5-Hazard Suite + Isolation Forest + FastDTW Telemetry Alignment** |
| **Drilling Physics** | **Eaton PPFG Pore Pressure + Mud Window Margins** (`PetrolQ`). | Most competitor systems treat drilling reports as text without rock mechanics equations. | **Eaton Method Pore Pressure + Dynamic Operating Margins ($MW-PP, FG-ECD$)** |

---

## 6. Commoditized Features (What We Should NOT Build)

The audit reveals that several generic features are widely implemented and offer **zero defensibility**:

- ❌ **Generic PDF Upload & Text Chatbot**: Basic LangChain / FAISS wrapper over PDF text (`DrillSense`, `SIH_PLANNS`).
- ❌ **Basic 2D Leaflet Pin Map**: Simple marker placement on OpenStreetMap tiles (`tarumishra`, `pallavi`).
- ❌ **Static Summary Dashboard Cards**: Hardcoded metric cards ("1,248 Wells") (`tarumishra`).
- ❌ **Synthetic Data Generators**: Generating trigonometric fake logs (`45 + 15*sin(z/40)`) or `random.uniform()` risk scores (`PetrolQ`).
- ❌ **Uncalibrated Dense-Only Vector Search**: Cosine similarity without depth/formation pre-filtering retrieves irrelevant sections from random depths.

---

## 7. Defensible USPs & Engineering Differentiators for PS 121

Every proposed USP is grounded in an verified code gap, backed by mathematical rigor, and designed for maximum operational defensibility:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            PS 121 CORE TECHNICAL DIFFERENTIATORS                            │
├──────────────────────────┬───────────────────────────────┬──────────────────────────────────┤
│ Differentiator           │ Competitor Code Gap           │ Proposed Target Design           │
├──────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ 1. Stratigraphic Depth   │ Zero competitors handle dip;  │ Dimensionless interval scaling:  │
│    Normalization (ξ)     │ compare raw Measured Depth.   │ ξ(d) = (TVDSS - Top) / Thickness │
├──────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ 2. Fault-Block Barrier   │ Surface 2D distance only;     │ PostGIS ST_Crosses intersection  │
│    Structural Gating     │ ignores sealing fault blocks. │ with structural barrier penalty. │
├──────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ 3. Autonomous Lookahead  │ Passive search bars; no       │ Forward corridor [+50m, +200m]   │
│    Ahead-of-Bit Corridor │ predictive lookahead.         │ projecting upcoming hazards.     │
├──────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ 4. Dynamic Mud Window    │ Reports treated as text;      │ Real-time margins: Trip Margin = │
│    Margins (PPFG + ECD)  │ no pore pressure mechanics.   │ MW - PP, Loss Margin = FG - ECD. │
├──────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ 5. 1-Click Interactive   │ Plain text string citations;  │ Synchronized PDF canvas with     │
│    PDF Bounding Box      │ no visual page verification.  │ glowing amber bounding boxes.    │
└──────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

## 8. Proposed End-to-End Target Architecture

```
[ Active Well Planning & Real-Time Telemetry Stream ]
   ├── WGS84 Wellhead Coordinates (Lat, Lon, KB Elevation)
   ├── 3D Directional Survey (MD, Inclination, Azimuth)
   └── Real-time Telemetry (Depth, ROP, WOB, RPM, Torque, SPP, Mud Weight In/Out, Flow Rate)
        │
        ▼
[ Layer 1: Geospatial & Structural Fault-Block Gating ]
   ├── PostGIS Spatial Query (`ST_DWithin` on WGS84 Geometries)
   ├── Fault Barrier Polygon Intersection (`ST_Crosses` on Regional Fault Layer)
   └── Output: Top 3–5 Structurally Compatible Offset Wells (Filtered by Fault Compartment)
        │
        ▼
[ Layer 2: 3D Trajectory & Stratigraphic Normalization (ξ-Sync) ]
   ├── Minimum Curvature Algorithm: $(MD, Inc, Az) \to (TVD, TVDSS, Northing, Easting, DLS)$
   ├── Regional Structural Dip & True Stratigraphic Thickness Alignment
   ├── Dimensionless Coordinate Mapping: $\xi(d) = \frac{d_{\text{tvdss}} - Z_{\text{top}}}{Z_{\text{base}} - Z_{\text{top}}} \in [0.0, 1.0]$
   └── Output: Normalized Offset Well Depth Intervals ($\xi \pm 0.10$)
        │
        ▼
[ Layer 3: Dynamic Ahead-of-the-Bit Lookahead Corridor ]
   ├── Forward Corridor Projection: $[d_{\text{tvdss}}, d_{\text{tvdss}} + 100\text{m}]$ along 3D trajectory
   ├── Intersects corridor with offset well $\xi$-intervals
   └── Identifies upcoming formation tops, casing shoe depths, and historical loss/kick zones
        │
        ▼
[ Layer 4: Multi-Modal Hybrid RAG & Knowledge Graph Engine ]
   ├── High-Speed PyMuPDF Layout Extraction preserving normalized coordinates $(x_0, y_0, x_1, y_1)$
   ├── OpenCV Morphological Contour Line Detection for complex casing/mud tables
   ├── pgvector Dense Embeddings + PostgreSQL Full-Text Search (BM25) with RRF ($k=60$)
   └── Dynamic $\Omega$-Reranking: $\Omega = 0.40 \cdot \text{VectorSim} + 0.25 \cdot \text{BM25} + 0.25 \cdot (1 - |\Delta \xi|) + 0.10 \cdot \text{Severity}$
        │
        ▼
[ Layer 5: Subsurface Engineering Physics & Anomaly Detection ]
   ├── Eaton Pore Pressure Gradient ($PP$) & Hubbert-Willis Fracture Gradient ($FG$)
   ├── Real-time Operating Margins: $\text{Trip Margin} = MW_{\text{act}} - PP, \quad \text{Loss Margin} = FG - ECD$
   └── Isolation Forest Anomaly Detection + FastDTW Telemetry Alignment
        │
        ▼
[ Layer 6: Auditable Decision Support & Visual Provenance ]
   ├── Structured 4-Step Operational Action Plans (Priority, Mud Weight, RPM, WOB, LCM formulation)
   ├── Operator Decision Log (`EngineerAction` audit trail: accepted, rejected, investigating)
   └── Synchronized PDF Canvas Viewer with Glowing Amber Bounding-Box Overlays on Source EOWRs
```

---

## 9. Detailed Repository-by-Repository Code Audits

Individual deep-dive audit files with complete code breakdowns are available in [`research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/`](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/):

1. [**dhanwanth_ertmac_nwis.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/dhanwanth_ertmac_nwis.md) — 5 XGBoost models, Isolation Forest anomaly detector, 6-factor similarity, and 4-step action recommendations.
2. [**physics0070_nwis.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/physics0070_nwis.md) — PostgreSQL + Alembic relational schema, telemetry replay service, and `EngineerAction` decision audit model.
3. [**vidhiii1711_drillx.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/vidhiii1711_drillx.md) — Team DrillX fullstack app (Vercel), 20+ telemetry parameters, and `DecisionLogController`.
4. [**petrolq.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/petrolq.md) — PostGIS spatial radius queries, offline MapLibre tiles, Saaty AHP weighted RAG, and Eaton PPFG.
5. [**tech_nitin_wellwise.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/tech_nitin_wellwise.md) — Three.js 3D subsurface geological layer explorer with camera OrbitControls and CSS2D callout annotations.
6. [**invo_coder19_drill_iq.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/invo_coder19_drill_iq.md) — React 19, Vite, TanStack Router with interactive `WellMap.tsx` and Offset Relevance Score.
7. [**drillmind.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/drillmind.md) — Multi-agent specialist architecture (`DrillingAgent`, `HistoricalAgent`, `SafetyAgent`) and RRF BM25+Vector hybrid retrieval.
8. [**ddr_utah_forge.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOwR_REPOSITORY_STUDY/repositories/ddr_utah_forge.md) — PyMuPDF layout segmentation, OCR confidence scoring, morphological table fallback, and phase-transition causality tracking.
9. [**sih_2026_planns.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/sih_2026_planns.md) — FastDTW telemetry anomaly detector, NetworkX knowledge graph, and hazard-specific feature weights.
10. [**pallavi_ertmac_nwis.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/pallavi_ertmac_nwis.md) — Qwen2.5-VL two-pass VLM extraction, OpenCV table detection, and strict RAG score floor.
11. [**rudrachauhan_ertmac_nwis.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/rudrachauhan_ertmac_nwis.md) — Modular FastAPI backend with dedicated routers for `/alerts`, `/events`, `/formations`, `/risk`, `/telemetry`.
12. [**suryanshkota07_aroh.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/suryanshkota07_aroh.md) — Deterministic 5-factor analog well matching and forward depth risk projection.
13. [**volve_drilling.md**](file:///d:/Programming/Project%203.0/PS121/research/PS121_COMPETITOR_REPOSITORY_STUDY/repositories/volve_drilling.md) — Standard WITSML 1.3.1 trajectory surveys and 24-well LAS log curves.
