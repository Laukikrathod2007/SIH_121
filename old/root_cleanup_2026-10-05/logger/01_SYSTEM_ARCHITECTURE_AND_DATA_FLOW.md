# SIH 26121 — eRTMAC-NWIS: System Architecture & Data Flow

## 1. End-to-End System Architecture

The following diagram illustrates the 4-tier architecture of eRTMAC-NWIS:

```text
+------------------------------------------------------------------------------------+
|                                OPERATIONAL COCKPIT                                 |
|                                                                                    |
|  +-----------------------+  +--------------------------+  +---------------------+  |
|  |   Geospatial Offset   |  |   Stratigraphic Depth    |  | Real-Time Telemetry |  |
|  |     GIS Map View      |  | & Risk Corridor Tracker  |  |  & Anomaly Strips   |  |
|  +-----------------------+  +--------------------------+  +---------------------+  |
|  +-----------------------------------------------------+  +---------------------+  |
|  |      Explainable DDR/WCR Evidence & PDF Citation    |  |  AI Drilling Agent  |  |
|  |           Modal with Historical Mitigation          |  |  (Tool Calling Cop) |  |
|  +-----------------------------------------------------+  +---------------------+  |
+------------------------------------------▲-----------------------------------------+
                                           │ REST / WebSocket / JSON
+------------------------------------------▼-----------------------------------------+
|                                BACKEND APPLICATION                                 |
|                                                                                    |
|  +------------------------------------------------------------------------------+  |
|  |                       FastAPI High-Performance Engine                        |  |
|  |                                                                              |  |
|  |  +-------------------------+  +-----------------------+  +----------------+  |  |
|  |  |  Dynamic Relevance Eng  |  | Interval Correlator   |  | Risk Corridor  |  |  |
|  |  | (5-Weight Distance/Form)|  | (MD/TVD/Stratig Norm) |  | Lead-Time Warn |  |  |
|  |  +-------------------------+  +-----------------------+  +----------------+  |  |
|  |  +-------------------------+  +-----------------------+  +----------------+  |  |
|  |  | Anomaly Detector ML     |  | Evidence / RAG Engine |  | Agent Tools    |  |  |
|  |  | (IsolationForest/Rules) |  | (BM25 + Semantic Vec) |  | Orchestrator   |  |  |
|  |  +-------------------------+  +-----------------------+  +----------------+  |  |
|  +------------------------------------------------------------------------------+  |
+------------------------------------------▲-----------------------------------------+
                                           │ SQL / Vector Queries
+------------------------------------------▼-----------------------------------------+
|                                DATA & STORAGE LAYER                                |
|                                                                                    |
|  +---------------------+  +--------------------+  +-----------------------------+  |
|  |     PostgreSQL      |  |      PostGIS       |  |     pgvector / Qdrant       |  |
|  | Normalized Entities |  | Geospatial Spatial |  | DDR/WCR Embeddings & Vector |  |
|  | (Wells/Logs/Events) |  | Coordinates/Dist   |  | Semantic Search Chunks      |  |
|  +---------------------+  +--------------------+  +-----------------------------+  |
+------------------------------------------▲-----------------------------------------+
                                           │ Ingestion & Indexing Pipeline
+------------------------------------------▼-----------------------------------------+
|                               INGESTION & DATA PIPELINE                            |
|                                                                                    |
|  +-----------------------+  +--------------------------+  +---------------------+  |
|  | WITSML Trajectory/Log |  | Daily Drilling Reports   |  | eRTMAC Telemetry    |  |
|  | Parsers & Formation   |  | (DDR) / WCR PDF Parser   |  | Stream Replay Sim   |  |
|  +-----------------------+  +--------------------------+  +---------------------+  |
+------------------------------------------------------------------------------------+
```

---

## 2. Intelligence Loop Execution Flow

When an active well increments its depth (e.g., during live drilling or replay):

```text
[Step 1: Active Well Context Update]
  • Bit Depth: 3,220 m MD (3,110 m TVD)
  • Current Formation: Formation C (Tipam Sandstone)
  • Sensor Telemetry: Torque = 28.5 kNm (+22% spike), Flow Out = 1,420 lpm (-18% drop)

[Step 2: Dynamic Spatial & Contextual Filtering]
  • Spatial radius search: Finds 8 candidate offset wells within 25 km.
  • Dynamic Relevance Scoring evaluates each candidate across 5 parameters:
    - Distance Proximity
    - Formation Match at current stratigraphic horizon
    - Depth Overlap
    - Wellbore Trajectory Similarity
    - Historical Event Density

[Step 3: Stratigraphic Depth Interval Matching]
  • Active well's depth is projected against historical offset depth intervals.
  • System identifies a clustered **Historical Risk Corridor**:
    - Interval: 3,235 m – 3,270 m (15 meters ahead of bit).
    - Incidents: Well W03 (Severe Mud Loss at 3,248 m), Well W05 (Losses at 3,252 m), Well W09 (Torque Sticking at 3,242 m).

[Step 4: Multi-Signal Risk Assessment]
  • Historical Prior = HIGH (3/3 analog wells suffered lost circulation).
  • Sensor Anomaly Score = HIGH (Flow out decrease detected).
  • Lead-Time Status = "PROACTIVE EARLY WARNING: 15m to Loss Zone".

[Step 5: Evidence Grounding & Mitigation Retrieval]
  • Direct extraction of past mitigation: "Well W03 pumped 25 bbl medium-nut-plug LCM pill + reduced flow rate to 1,600 lpm."
  • Exact document citation: DDR_OIL_W03_2023.pdf, Page 42, Paragraph 3.

[Step 6: Display in Cockpit & AI Explainer]
  • Visual alert displayed with 4-pillar confidence breakdown.
  • Drilling Supervisor reviews recommended pre-treatment and gives instructions to mud engineer.
```

---

## 3. Technology Stack & Technical Rationale

| Layer | Component | Selected Technology | Technical Justification |
|---|---|---|---|
| **Frontend UI** | Operational Cockpit | React 18, TypeScript, Tailwind CSS, Lucide Icons | High-density dashboard, ultra-responsive UI, type safety, dark-mode command center theme. |
| **Interactive Map** | Spatial GIS View | Leaflet / React-Leaflet with OpenStreetMap tiles | Lightweight, fast rendering of well coordinates, radius circles, and dynamic color-coded relevance markers. |
| **Wellbore Visualization** | Stratigraphic & Trajectory Track | Canvas / SVG / Recharts / Plotly | Custom high-precision vertical depth track showing lithology layers, active bit depth, and historical hazard markers. |
| **Backend API** | Intelligence Core Engine | Python 3.10+, FastAPI, Uvicorn | Native async speed, automatic OpenAPI documentation, clean integration with Python scientific and ML libraries. |
| **Data & Geometry** | Spatial & Relational DB | PostgreSQL + PostGIS (with SQLite/GeoPandas fallback for local prototype) | Standard spatial geometry queries (ST_Distance, ST_DWithin) and structured event queries. |
| **Vector Search / RAG** | Document Knowledge Retrieval | BM25 + pgvector / SentenceTransformers (`all-MiniLM-L6-v2`) | Hybrid sparse-dense retrieval ensuring zero hallucination on historical DDR text. |
| **Machine Learning** | Anomaly & Risk Engine | Scikit-Learn (Isolation Forest / Random Forest / Logistic Regression) | Deterministic baseline + unsupervised anomaly scoring on multivariate sensor streams (Torque, Flow, SPP). |
| **Domain AI Agent** | Tool-Augmented Assistant | FastAPI Tool Dispatcher + LLM (OpenAI API / Ollama local LLM fallback) | Strictly grounded tool calling (`rank_offset_wells`, `get_risk_corridor`, `retrieve_ddr_evidence`). |
