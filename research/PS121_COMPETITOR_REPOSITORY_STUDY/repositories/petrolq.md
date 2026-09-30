# Competitor Repository Audit: PetrolQ

## 1. Repository Metadata
- **Repository**: `PetrolQ`
- **URL**: `https://github.com/thor11223344/PetrolQ.git`
- **Owner**: thor11223344
- **Project**: PetrolQ Nearby Wells Intelligence System (eRTMAC-NWIS)
- **Category**: Direct Competitor
- **Relevance**: High (Direct submission targeting PS 121 / 26121 with extensive codebase)
- **Primary Language**: Python (FastAPI, SQLAlchemy, GeoAlchemy2, PostGIS, pgvector, PyMuPDF, LangChain), React 19 (MapLibre GL, Plotly.js)
- **Files Inspected**: 1,570 files across `backend/`, `frontend/`, `data/`, `sample_reports/`, `scripts/`, `tests/` (including 1,400+ offline map tiles).

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React 19 + Vite + Tailwind CSS + MapLibre GL + Plotly.js]
   ├── Geospatial Map View (MapLibre GL with local offline raster tiles)
   ├── 3D Well Trajectory Visualizer (Plotly.js 3D scatter plots)
   ├── Lookahead Risk Dashboard (Risk gauges, incident timelines)
   └── AI Dossier & Query Assistant (Streaming LangChain chat)
        │
        ▼ (FastAPI REST API: `backend/main.py`)
[Application Services Layer (`backend/api/` & `backend/services/`)]
   ├── api/correlate.py (Dynamic Time Warping well-to-well log correlation)
   ├── api/lookahead.py (Ahead-of-bit risk projection + formation tops)
   ├── api/ppfg.py (Pore Pressure & Fracture Gradient window calculator)
   ├── api/dossier.py (Offset well executive summary & technical dossier)
   ├── services/ahp_weights.py (Analytic Hierarchy Process multi-criteria weighting)
   ├── services/hybrid_retrieval.py (AHP-weighted BM25 + pgvector retrieval)
   └── services/knowledge_graph.py (Entity relationship linking)
        │
        ▼
[Data Layer (`backend/models.py` & `backend/database.py`)]
   ├── PostgreSQL + PostGIS (Spatial geometries: `ST_Point`, `ST_Distance`)
   ├── pgvector (Vector embeddings for document chunks)
   └── SQLAlchemy ORM (WellMaster, WellLog, DrillingParam, SyntheticEvent)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `backend/models.py`, `backend/main.py` | Spatial radius queries using GeoAlchemy2 `ST_DWithin` and `ST_Distance` on WGS84 coordinates. |
| **GIS / Map Interface** | ✅ **VERIFIED** | `frontend/src/` (MapLibre GL), `backend/static/tiles/` | Interactive map with offline raster tiles for Upper Assam (Baghjan, Nahorkatiya, Moran, Dikom). |
| **Historical DDR Parsing** | 🟡 **PARTIAL** | `backend/nlp/parser.py`, `backend/nlp/extractor.py` | Parses text from sample PDFs with PyMuPDF/pdfplumber; regex extraction for daily activities and mud weight. |
| **OCR Processing** | 🟡 **PARTIAL** | `backend/nlp/extractor.py` (EasyOCR) | Basic OCR fallback for raster images, but lacks hierarchical table cell segmentation or confidence gating. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `backend/nlp/extractor.py` | Extracts structured events (Kick, Stuck Pipe, Mud Loss, Equipment Failure, Casing) with regex patterns. |
| **RAG Retrieval** | ✅ **VERIFIED** | `backend/services/hybrid_retrieval.py` | pgvector cosine similarity search + LangChain LLM context generation (Gemini / Anthropic / OpenAI). |
| **Hybrid Search** | ✅ **VERIFIED** | `backend/services/ahp_weights.py`, `hybrid_retrieval.py` | Combines BM25 and vector search using Saaty AHP (Analytic Hierarchy Process) weights. |
| **Formation Correlation** | 🟡 **PARTIAL** | `backend/api/correlate.py` L30-65 | FastDTW curve matching implemented, but relies on **synthesized sinusoidal Gamma Ray logs** when real LAS logs are absent. |
| **Depth Correlation** | 🟡 **PARTIAL** | `backend/trajectory_calc.py` | Minimum curvature trajectory calculation exists, but stratigraphic thickness scaling $\xi(d)$ across regional dip is missing. |
| **Lookahead Risk Projection** | 🟡 **PARTIAL** | `backend/api/lookahead.py` L15-60 | Computes ahead-of-bit risk, but relies on a **hardcoded dictionary** (`WELL_FORMATION_HORIZONS`) for formation tops. |
| **PPFG Mud Window** | ✅ **VERIFIED** | `backend/api/ppfg.py` | Computes Eaton pore pressure, overburden gradient, and fracture gradient curves. |
| **Knowledge Graph** | 🟡 **PARTIAL** | `backend/services/knowledge_graph.py` | In-memory NetworkX graph connecting wells and formations; does not persist or query multi-hop graph DB. |
| **Evidence Citations** | 🟡 **PARTIAL** | `backend/api/ai_assistant.py` | Returns document filename and chunk page numbers in chat, but no PDF highlight viewer. |
| **Real-Time Telemetry** | 🟡 **PARTIAL** | `backend/simulator.py` | Synthetic telemetry generator for live demo; lacks WITSML/OPC-UA ingestion. |

---

## 4. Code-Level Investigation & Gaps
1. **Synthetic Data Fallbacks in Production Code**:
   - In `backend/api/correlate.py` (lines 30–65), `synthesize_gr_logs()` generates fake Gamma Ray curves using `np.sin(z / 40.0) + rng.uniform(-5, 5)` whenever a well lacks imported LAS files.
   - In `backend/api/lookahead.py` (lines 15–60), formation tops for Baghjan, Nahorkatiya, Moran, and Dikom are hardcoded in a static Python dictionary rather than extracted dynamically from EOWRs or geological databases.
2. **Missing Fault Block Partitioning**:
   - While spatial distance is computed via PostGIS, the system has no structural geology awareness (fault boundaries, thrust sheets). Wells separated by major fault blocks are matched purely on surface proximity.
3. **Absence of Visual Provenance**:
   - The frontend displays document names and page numbers in text bubbles, but provides no side-by-side PDF rendering with exact bounding-box highlights of the extracted sentences or tables.

---

## 5. What We Can Learn & PS 121 Differentiation
- **Strengths to Learn From**: Excellent use of PostGIS + pgvector, offline MapLibre tile packaging, AHP-weighted hybrid search, and PPFG Eaton mud window calculations.
- **Our Opportunities**:
  1. Replace synthetic GR log generation with real LAS/DLIS parsing and True Stratigraphic Normalization $\xi(d) = \frac{d_{tvdss} - Top}{Thickness}$.
  2. Make formation horizon boundaries dynamic, pulling directly from verified EOWR geological picks.
  3. Introduce Fault-Block Gating in the spatial query to discount offset wells across tectonic boundaries.
  4. Provide synchronized 1-click PDF viewer with bounding-box highlights.
