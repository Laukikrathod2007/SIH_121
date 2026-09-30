# Competitor Repository Audit: pallavi-eRTMAC-NWIS

## 1. Repository Metadata
- **Repository**: `pallavi-eRTMAC-NWIS`
- **URL**: `https://github.com/pallavi-a11y/eRTMAC-NWIS.git`
- **Owner**: pallavi-a11y
- **Project**: eRTMAC-NWIS — Multi-Modal Offset Well Intelligence
- **Category**: Direct Competitor
- **Relevance**: High (Direct submission targeting PS 121 / 26121)
- **Primary Language**: Python (FastAPI, Qdrant, pypdfium2, OpenCV, Ollama / Qwen2.5-VL), React 19 (Leaflet, Tailwind CSS v4)
- **Files Inspected**: 69 files across `backend/`, `ertmac-nwis/`, `backend/routers/`, `backend/src/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React 19 + Vite + Tailwind CSS v4 + React-Leaflet]
   ├── Geospatial Well Map (React-Leaflet pins & radius)
   ├── Multi-Modal Document Reviewer (Page viewer with extracted tables/figures)
   ├── Hazard & Risk Monitor (Extracted incident cards)
   └── DrillMind RAG Assistant (Qwen2.5-VL grounded chat)
        │
        ▼ (FastAPI Server: `backend/main.py`)
[Backend Routers (`backend/routers/`)]
   ├── corpus.py (Document corpus indexing & page retrieval)
   ├── wells_map.py (Well geolocation & manual pin creation)
   ├── risk.py (Hazard summary & severity breakdown)
   ├── review.py (Human-in-the-loop OCR review & verification)
   └── drillmind.py (Grounded Q&A engine with deterministic guards)
        │
        ▼
[Extraction & RAG Engine (`backend/src/`)]
   ├── pdf_processor.py (pypdfium2 rendering to high-res images)
   ├── unified_parser.py & table_parser.py (Multi-pass VLM + OpenCV table line detector)
   ├── figure_extractor.py (Cropping geological cross-sections & wellbore diagrams)
   ├── vector_store.py (Qdrant vector database with SentenceTransformers)
   └── rag_engine.py (Strict grounded LLM prompt with similarity floor `RAG_MIN_SCORE`)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `backend/routers/wells_map.py`, `src/database.py` | Geopy distance calculation from active well coordinates. |
| **GIS / Map Interface** | 🟡 **PARTIAL** | `ertmac-nwis/src/pages/MapVisualise.jsx` | Basic Leaflet 2D pin map. Does not display subsurface trajectories, fault lines, or formation contours. |
| **Historical DDR / EOWR Parsing** | ✅ **VERIFIED** | `backend/src/unified_parser.py`, `table_parser.py` | Robust 2-pass Vision-Language Model extraction using Qwen2.5-VL on rendered PDF page images. |
| **OCR & Figure Extraction** | ✅ **VERIFIED** | `backend/src/figure_extractor.py`, OpenCV | Automatically detects and crops wellbore schematics, casing diagrams, and lithology tables. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `backend/src/hazard_monitor.py` | Extracts wellbore hazards (Loss, Kick, Stuck Pipe, Packoff) with deterministic severity whitelisting. |
| **RAG Retrieval** | ✅ **VERIFIED** | `backend/src/rag_engine.py`, `vector_store.py` | Qdrant vector retrieval with cosine score floor (rejects queries below threshold to prevent hallucinations). |
| **Hybrid Search** | 🟡 **PARTIAL** | `src/vector_store.py` | Dense vector similarity in Qdrant; lacks sparse BM25 lexical fusion. |
| **Formation Correlation** | ❌ **NOT FOUND** | N/A | No formation thickness scaling or stratigraphic depth synchronization. |
| **Depth Correlation** | 🟡 **PARTIAL** | `src/database.py` | Flat depth range filtering; no TVDSS trajectory projection. |
| **Incident Prediction** | 🟡 **PARTIAL** | `src/hazard_monitor.py` | Displays historical hazards; lacks real-time telemetry matching or forward lookahead risk forecasting. |
| **Knowledge Graph** | ❌ **NOT FOUND** | N/A | No graph topology. |
| **Evidence Citations** | ✅ **VERIFIED** | `src/rag_engine.py`, `routers/review.py` | Deterministic citations linking LLM answers to exact document page IDs and figure crops. |
| **Real-Time Telemetry** | ❌ **NOT FOUND** | N/A | Batch document processing only; no real-time telemetry ingestion. |

---

## 4. Code-Level Investigation & Gaps
1. **Developer-Documented UI Mocks**:
   - As explicitly documented by the repository author in `routers/dashboard.py` and `routers/wells_map.py`, the initial template UI contained hardcoded groundwater monitoring widgets ("1,248 wells", `waterLevel` fields) which the author had to surgically bypass.
2. **Heavy VLM Overhead**:
   - The extraction pipeline passes every single page image through local Ollama Qwen2.5-VL. For large 500+ page EOWR documents, processing takes hours without high-end GPU clusters.
3. **No Drilling Engineering Physics**:
   - The system treats drilling reports purely as text/image documents. It lacks physical models (Eaton pore pressure, ECD, d-exponent, MSE, dogleg severity).

---

## 5. What We Can Learn & PS 121 Differentiation
- **Strengths to Learn From**: Outstanding anti-hallucination design in `rag_engine.py` (strict deterministic similarity threshold, zero LLM invocation when retrieval is empty, deterministic citations). Great figure/table cropping with OpenCV.
- **Our Opportunities**:
  1. Add drilling engineering physics models (PPFG, Eaton method, MSE, Hydraulics).
  2. Implement True Vertical Depth Subsea (TVDSS) and Stratigraphic $\xi(d)$ correlation across dipping formations.
  3. Combine VLM figure extraction with high-speed hybrid text indexing (BM25 + pgvector) for instant search.
