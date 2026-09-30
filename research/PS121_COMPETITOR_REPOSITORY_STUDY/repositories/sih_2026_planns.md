# Competitor Repository Audit: SIH_2026_PLANNS (NWIS-Sentinel)

## 1. Repository Metadata
- **Repository**: `SIH_2026_PLANNS`
- **URL**: `https://github.com/n3ssdub3y/SIH_2026_PLANNS.git`
- **Owner**: n3ssdub3y
- **Project**: NWIS-Sentinel (SIH 2026 Problem Statement 121 / 26121)
- **Category**: Direct Competitor
- **Relevance**: High (Direct submission targeting PS 121 / 26121)
- **Primary Language**: Python (FastAPI, Flask), HTML/JS
- **Files Inspected**: 173 files across `NLP/nlp_task_ddr`, `NLP/nwis-sentinel`, `datasets/`, `ARCHITECTURE.md`, `NWIS_PROJECT_SHOWCASE.md`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend / Vis.js / HTML]
        │
        ▼ (HTTP REST)
[FastAPI Gateway / Flask Microservices (Port 8000 / 5005)]
   ├── app/routers/wells.py (Wells API)
   ├── app/routers/events.py (Events & DDR Parsing)
   ├── app/routers/matching.py (Analog Similarity Engine)
   └── app/routers/telemetry.py (Real-time Telemetry & Dynamic Time Warping)
        │
        ▼
[NLP & Knowledge Graph Pipeline]
   ├── Module 1: Regex & LLM Extraction (extraction_prompt.txt, events.jsonl)
   ├── Module 2: Stratigraphic Alignment (Linear depth normalization)
   ├── Module 3: FastDTW & Anomaly Detection (statsmodels, scipy)
   ├── Module 4: NetworkX Knowledge Graph (`knowledge_graph.gpickle`, vis-network)
   └── Module 5: Engineering Agent (Qwen2.5 / Gemini via HuggingFace & ChromaDB)
        │
        ▼
[Data Storage]
   ├── ChromaDB (SQLite vector store: `chroma.sqlite3`)
   ├── NetworkX Gpickle (`knowledge_graph.gpickle`)
   └── Flat JSON/CSV files (`wells_metadata.json`, `events.jsonl`, `telemetry/*.csv`)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | 🟡 **PARTIAL** | `app/services/similarity_engine.py` L45-80 | Uses 2D Euclidean / Haversine distance on flat lat/lon coordinates from `wells_metadata.json`. No spatial database (PostGIS) or fault-block barrier checks. |
| **GIS / Map Interface** | 🟡 **PARTIAL** | `templates/module4.html`, `vis-network.min.js` | Uses Vis.js for graph topology, but lacks a full Leaflet/MapLibre geospatial coordinate projection with formation dip vectors. |
| **Historical DDR Parsing** | ✅ **VERIFIED** | `NLP/nlp_task_ddr/prompts/extraction_prompt.txt`, `results/extracted_10_ddrs.json` | Structured JSON extraction from 10 sample DDRs with event classification (losses, kicks, stuck pipe). |
| **OCR Processing** | 🟡 **PARTIAL** | `requirements.txt` (pypdfium / pdfplumber) | Parses digital PDF/text reports; lacks full scanned OCR bounding-box polygon extraction or table cell coordinate mapping. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `app/services/nlp_extractor.py`, `results/module1_outputs/event_type_vocabulary.json` | Extracts categorized drilling events (Loss, Kick, Stuck Pipe, Equipment Failure, Casing/Cementing). |
| **RAG Retrieval** | ✅ **VERIFIED** | `module5_engineering_agent/retrieval/retriever.py`, `vector_store.py` | ChromaDB vector search + structured prompt injection (`prompts.py`). |
| **Hybrid Search** | 🟡 **PARTIAL** | `retrieval/retriever.py` | Basic embedding distance + keyword metadata filtering; lacks BM25 + dense RRF (Reciprocal Rank Fusion) mathematical rank blending. |
| **Formation Correlation** | 🟡 **PARTIAL** | `services/similarity_engine.py` L25-40 | String matching on formation names (`formations: list[str]`). Does not compute true stratigraphic thickness scaling $\xi(d) = \frac{d_{tvdss} - Top}{Thickness}$ across structural dip ($3^\circ-15^\circ$). |
| **Depth Correlation** | 🟡 **PARTIAL** | `similarity_engine.py` | Linear depth proximity score $1 - \frac{|\Delta MD|}{500}$. Fails on deviated wells where MD differs greatly from TVDSS. |
| **Incident Prediction** | ✅ **VERIFIED** | `NLP/nlp_task_ddr/results/module3_outputs/risk_predictions.jsonl` | FastDTW sequence alignment matching active well telemetry against historical incident patterns. |
| **Knowledge Graph** | ✅ **VERIFIED** | `NLP/nlp_task_ddr/module4/outputs/knowledge_graph.gpickle` | NetworkX graph connecting Wells $\to$ Formations $\to$ Incidents $\to$ Actions. Exported to Vis.js UI. |
| **Evidence Citations** | 🟡 **PARTIAL** | `module5_engineering_agent/agent/agent.py` | Injects retrieved snippet IDs into prompt; does not generate exact 1-click bounding box view on the original PDF page. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `app/routers/telemetry.py`, FastDTW | Simulates telemetry streaming from Volve CSV logs (`15_9-F-9A.csv`) and flags divergence. |

---

## 4. Code-Level Investigation & Gaps
1. **Static Pre-Extracted Datasets**:
   - In `NLP/nwis-sentinel/backend/data/demo_data.py`, several wells and events are hardcoded for demo playback. Real pipeline runs batch offline scripts to generate `.jsonl` and `.gpickle` rather than on-the-fly streaming ingestion.
2. **Deviation & Subsurface Geometry Ignored**:
   - `Well` dataclass in `similarity_engine.py` uses `total_depth_m: float` (single MD value) without 3D trajectory interpolation (Minimum Curvature Method: MD, Inc, Az $\to$ TVD, TVDSS, Northing, Easting).
3. **No Fault Block Barrier Logic**:
   - Geographic distance is calculated purely as surface distance. If an offset well is 800m away across a sealing thrust fault, it is treated as a strong analog despite having entirely disconnected pressure regimes.

---

## 5. What We Can Learn & PS 121 Differentiation
- **Strengths to Learn From**: Excellent separation of hazard weights in `similarity_engine.py` (e.g. mud loss weighs formation match at 30%, depth at 25%, mud weight at 20%). Clean FastDTW telemetry anomaly detector.
- **Our Opportunities**:
  1. Replace static flat JSON/gpickle with dynamic PostGIS + pgvector database.
  2. Implement true 3D trajectory calculation with TVDSS and Stratigraphic Normalization $\xi(d)$.
  3. Implement Fault Block isolation to prevent false-positive offset well correlations across structural boundaries.
  4. Provide true 1-click PDF bounding-box provenance.
