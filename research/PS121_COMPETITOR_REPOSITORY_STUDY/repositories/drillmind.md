# Competitor Repository Audit: DrillMind

## 1. Repository Metadata
- **Repository**: `DrillMind`
- **URL**: `https://github.com/ArokyaMatthew/DrillMind.git`
- **Owner**: ArokyaMatthew
- **Project**: DrillMind — Real-Time Operations Center (RTOC) & Offset Intelligence Platform
- **Category**: Direct Competitor / Advanced Drilling Assistant
- **Relevance**: High (Complete production-style implementation with multi-agent orchestration, hybrid RAG, and live telemetry)
- **Primary Language**: Python (FastAPI, PyTorch, ChromaDB, rank-bm25), Vanilla JS Dashboard
- **Files Inspected**: 76 files across `src/drillmind/`, `dashboard/`, `config/`, `scripts/`, `tests/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend Dashboard (Vanilla JS / Canvas Sparklines / WebSockets)]
   ├── Live Telemetry Stream (/ws/stream)
   ├── Real-time Alerts Feed (/ws/alerts)
   ├── Time-Depth Curve Viewer (GET /api/data/timedepth)
   └── Copilot Chat Interface (POST /api/copilot/query)
        │
        ▼ (FastAPI Server: `src/drillmind/api/server.py`)
[Multi-Agent Orchestrator (`src/drillmind/agents/`)]
   ├── MultiOrchestrator & Router (Intent routing to specialist agents)
   ├── DrillingAgent (Real-time telemetry, ROP/WOB/SPP parameter analytics)
   ├── HistoricalAgent (Offset DDR query & analog retrieval)
   ├── SafetyAgent (Anomaly, kick, and stuck-pipe risk assessment)
   └── ReportingAgent (Automated shift handover & daily summary generation)
        │
        ▼
[Hybrid Retrieval Engine (`src/drillmind/rag/`)]
   ├── BM25Index (Lexical retriever: `bm25.py`)
   ├── DDRVectorStore (ChromaDB cosine embedding store: `store.py`)
   └── HybridRetriever with Reciprocal Rank Fusion (RRF k=60): `retriever.py`
        │
        ▼
[Analytics & ML Models (`src/drillmind/models/`)]
   ├── RigStateClassifier (Rule-based state machine: Rotary, Slide, Ream, Trip)
   ├── DrillingKPIs (MSE calculation, d-exponent, hydraulic horsepower)
   └── LSTMAnomalyDetector (`lstm_detector.py` for multivariate time-series)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ❌ **NOT FOUND** | N/A | DrillMind contains **zero spatial search or coordinates**. Wells are looked up purely by string name (`well_name: "15/9-F-9 A"`). |
| **GIS / Map Interface** | ❌ **NOT FOUND** | `dashboard/index.html` | No map component exists. The UI is strictly an RTOC time-series / telemetry strip chart and chat sidebar. |
| **Historical DDR Parsing** | ✅ **VERIFIED** | `src/drillmind/parsers/ddr_parser.py` | Robust parsing of WITSML XML and HuggingFace Alpaca JSON (`bengsoon/volve_alpaca`) into structured `DDRDocument` objects. |
| **OCR Processing** | ❌ **NOT FOUND** | `src/drillmind/parsers/` | No OCR or PDF extraction capabilities. Assumes all input is pre-structured XML or JSON text. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `src/drillmind/models/event_classifier.py` | Regex + keyword classifier extracting fishing, loss, kick, stuck pipe, and tool failure events. |
| **RAG Retrieval** | ✅ **VERIFIED** | `src/drillmind/rag/store.py` | ChromaDB vector search over chunked DDR operations with metadata filtering by well name and depth. |
| **Hybrid Search (RRF)** | ✅ **VERIFIED** | `src/drillmind/rag/retriever.py` L40-85 | True Reciprocal Rank Fusion ($Score = \sum \frac{w_r}{k + rank_r}$) combining BM25 ($w=0.3$) and Dense Vector ($w=0.7$). |
| **Formation Correlation** | 🟡 **PARTIAL** | `src/drillmind/parsers/depth_log_parser.py` | Extracts formation tops from LWD gamma curves on a single well, but does not perform multi-well stratigraphic normalization or thickness scaling across structural dip. |
| **Depth Correlation** | 🟡 **PARTIAL** | `src/drillmind/copilot/context_builder.py` | Queries historical chunks within a fixed $\pm 100\text{m}$ Measured Depth (MD) window. Fails on deviated wells with disparate TVD/TVDSS. |
| **Incident Prediction** | ✅ **VERIFIED** | `src/drillmind/models/anomaly_detection.py`, `lstm_detector.py` | Statistical z-score anomaly scoring + PyTorch LSTM autoencoder on drilling telemetry (WOB, Torque, SPP, Flow). |
| **Knowledge Graph** | ❌ **NOT FOUND** | N/A | No graph database or entity-relationship topology. |
| **Evidence Citations** | 🟡 **PARTIAL** | `src/drillmind/copilot/engine.py` | Returns document metadata IDs (`doc_id`, `activity_index`), but no visual PDF bounding boxes. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `src/drillmind/api/server.py`, `dashboard/app.js` | Full WebSocket telemetry replay engine with configurable speed (1x–1000x) and sparkline ring buffers. |

---

## 4. Code-Level Investigation & Gaps
1. **Zero Geospatial Dimension**:
   - DrillMind has no concept of latitude, longitude, UTM projections, or spatial radius search. It cannot discover "nearby" wells; the user must manually specify offset well names.
2. **Volve North Sea Single-Field Bias**:
   - The entire codebase is tuned to the North Sea Volve field dataset (`15/9-F-9 A`, `15/9-F-14`). It has no knowledge of onshore Assam-Arakan thrust-belt stratigraphy (Tipam, Barail, Kopili) or geothermal high-temperature regimes.
3. **No PDF / Scanned Document Pipeline**:
   - Real-world EOWRs and DDRs in Indian and global basins are delivered as 500+ page scanned or mixed-mode PDFs. DrillMind fails completely if raw XML or JSON is unavailable.
4. **Deviated Trajectory & TVDSS Blindness**:
   - Depth slicing is done strictly on Measured Depth (MD). In high-angle horizontal wells (e.g. 60° inclination), a 100m MD window represents only 50m of stratigraphic penetration, distorting analog retrieval.

---

## 5. What We Can Learn & PS 121 Differentiation
- **Strengths to Learn From**: The hybrid RRF retriever (`retriever.py`) and multi-agent specialist architecture (`DrillingAgent`, `HistoricalAgent`, `SafetyAgent`) are the best engineered in the competitor pool.
- **Our Opportunities**:
  1. Add full Geospatial & PostGIS engine to enable automatic spatial radius and polygon discovery.
  2. Implement an end-to-end OCR and table-extraction pipeline for 500+ page EOWR/DDR PDFs.
  3. Upgrade the retrieval engine with 3D TVDSS trajectory projection and Stratigraphic $\xi(d)$ normalization.
  4. Integrate interactive 1-click PDF bounding-box provenance into the frontend copilot.
