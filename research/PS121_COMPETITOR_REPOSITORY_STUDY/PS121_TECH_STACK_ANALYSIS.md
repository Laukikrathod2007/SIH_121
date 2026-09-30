# PS 121 — Technology Stack & Architectural Analysis

This document provides an exhaustive technical analysis of the architectures, frameworks, databases, vector stores, and machine learning components utilized across the audited competitor codebases, concluding with the optimal production-grade stack recommended for **PS 121 (SIH 26121)**.

---

## 1. Comparative Technology Stack Overview

| Layer | SIH_2026_PLANNS | DrillMind | PetrolQ | pallavi-eRTMAC-NWIS | DDR_UTAH_FORGE | Recommended PS 121 Stack |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend Framework** | Jinja2 + Vis.js + HTML5 | Vanilla JS + Canvas Sparklines | React 19 + Vite | React 19 + Vite | Streamlit Multi-Page | **React 19 + Vite + TypeScript + Tailwind CSS** |
| **GIS & 3D Visualization**| Vis.js Topology | N/A (Strip charts only) | MapLibre GL + Plotly.js 3D | React-Leaflet 2D | Matplotlib / Static | **MapLibre GL (2D/3D) + Three.js / Plotly (3D Well Trajectory)** |
| **Backend Framework** | FastAPI + Flask Microservices | FastAPI + WebSockets | FastAPI | FastAPI | FastAPI + Streamlit | **FastAPI (Asynchronous REST + WebSockets)** |
| **Relational / Spatial DB**| Flat JSON files | In-Memory / SQLite | PostgreSQL + PostGIS (GeoAlchemy2) | In-Memory / SQLite | In-Memory / Pandas | **PostgreSQL 16 + PostGIS (Spatial Indexing: GIST)** |
| **Vector Store** | ChromaDB (SQLite) | ChromaDB | pgvector (PostgreSQL extension) | Qdrant | ChromaDB | **pgvector (Unified Relational + Spatial + Vector in Postgres)** |
| **Lexical / Sparse Search**| Basic substring / Metadata | BM25 (`rank-bm25`) | Custom BM25 | None | Custom Section Router | **PostgreSQL Full-Text Search (tsvector/BM25) + Qdrant/pgvector** |
| **PDF Ingestion & OCR** | PyMuPDF / pdfplumber | WITSML XML parser | PyMuPDF + EasyOCR | pypdfium2 + Qwen2.5-VL + OpenCV | PyMuPDF + OpenCV Table Fallback | **Dual-Engine: High-Speed PyMuPDF + OpenCV Table Cell Segmenter** |
| **LLM & Reasoning** | Gemini / Qwen2.5 (HF) | OpenAI GPT-4o / Ollama | Gemini / Claude / GPT-4o | Qwen2.5-VL (Ollama) | Local / OpenAI API | **Gemini 2.5 Flash / Pro + Claude 3.5 Sonnet (Structured Output)** |
| **Subsurface ML & Physics**| FastDTW telemetry | PyTorch LSTM + MSE | FastDTW + Eaton PPFG | None | Phase Causality Analyzer | **Eaton PPFG + FastDTW Stratigraphic Log Sync + MSE/ECD Analytics** |
| **Graph Intelligence** | NetworkX (`.gpickle`) | None | NetworkX | None | NetworkX Operational Graph | **NetworkX / PostgreSQL Recursive Graph (Property Graph Schema)** |

---

## 2. Layer-by-Layer Architectural Evaluation

### 2.1 Frontend & Visualization
- **Competitor Patterns**:
  - *Streamlit* (`DDR_UTAH_FORGE`): Excellent for quick data science prototypes, but exhibits sluggish UI state rerenders during live telemetry streaming and lacks fine-grained DOM control for responsive 3D maps.
  - *React + MapLibre GL* (`PetrolQ`): The most modern and performant GIS approach. Enables vector tile rendering, offline raster fallback, and hardware-accelerated 3D terrain pitch.
- **PS 121 Recommendation**: Use **React 19 + Vite + TypeScript + Tailwind CSS** with **MapLibre GL** for geospatial mapping and **Plotly.js / Three.js** for 3D wellbore trajectory visualization.

### 2.2 Relational Data & Spatial Indexing
- **Competitor Patterns**:
  - *Flat Files / SQLite* (`SIH_2026_PLANNS`, `DrillMind`, `pallavi`): Extremely fragile, cannot handle concurrent multi-user writes, lacks spatial indexing, and requires full-file in-memory loading.
  - *PostgreSQL + PostGIS* (`PetrolQ`): Production standard. Allows high-speed spatial indexing (`GIST`), bounding-box queries, and distance calculations directly inside SQL.
- **PS 121 Recommendation**: **PostgreSQL 16 + PostGIS**. All spatial geometries (wellhead locations, 3D bottom-hole coordinates, field boundaries, and regional fault lines) must be stored in standard spatial columns with `GIST` indexes.

### 2.3 Vector Database & Hybrid RAG Architecture
- **Competitor Patterns**:
  - *Isolated ChromaDB / FAISS* (`DrillMind`, `DrillSense`, `SIH_2026_PLANNS`): Disconnects the vector store from the relational database. Performing a query that filters by well, depth range, and formation requires a slow two-step join between Python memory and ChromaDB.
  - *pgvector* (`PetrolQ`): Co-locates vector embeddings directly within the relational database tables, enabling single-query hybrid filters:
    ```sql
    SELECT chunk_id, content, 1 - (embedding <=> :query_vec) AS sim
    FROM ddr_chunks
    WHERE well_id IN (:offset_well_ids)
      AND formation = :target_formation
      AND depth_tvdss BETWEEN :depth_min AND :depth_max
    ORDER BY embedding <=> :query_vec LIMIT 5;
    ```
- **PS 121 Recommendation**: **pgvector** inside PostgreSQL. Delivers atomic consistency, unified backups, and zero-latency metadata pre-filtering.

### 2.4 Document Extraction & Table OCR
- **Competitor Patterns**:
  - *Vision-Language Model per Page* (`pallavi`): Using Qwen2.5-VL on every page achieves high accuracy on complex layout pages, but takes 10–20 seconds per page (hours for a 500-page EOWR).
  - *Pure Digital Scraping* (`PetrolQ`, `SIH_2026_PLANNS`): Extremely fast (< 1s per PDF), but fails completely on scanned reports, tables with borders, or rotated schematics.
  - *Hybrid Layout + OCR Fallback* (`DDR_UTAH_FORGE`): Best practice. Uses fast digital text extraction first, evaluates OCR quality, and falls back to OpenCV contour segmentation only when tables or scans are detected.
- **PS 121 Recommendation**: Adopt the **Dual-Engine Hybrid Pipeline** inspired by `DDR_UTAH_FORGE`:
  1. Fast digital extraction via `PyMuPDF` with bounding-box extraction.
  2. OpenCV morphological line detection for complex casing/mud tables.
  3. Selective Vision-LLM fallback for unstructured diagrams, well schematics, and poor-quality scanned pages.

---

## 3. Subsurface Domain Physics & Analytics Stack
- **Pore Pressure & Fracture Gradient**: Eaton method calculation engine parameterized by normal compaction trend (NCT) from sonic/resistivity logs.
- **3D Trajectory Engine**: Minimum Curvature Method calculating Measured Depth (MD), Inclination (Inc), and Azimuth (Az) into True Vertical Depth (TVD), TVD Subsea (TVDSS), Northing, Easting, and Dogleg Severity (DLS).
- **Stratigraphic Synchronization**: Dynamic Time Warping (`FastDTW`) on standardized petrophysical log curves (Gamma Ray, Resistivity) + dimensionless interval normalization $\xi(d)$.
- **Real-Time Telemetry Processing**: WebSocket streaming endpoint with rolling sparkline buffers, MSE (Mechanical Specific Energy) calculation, and z-score anomaly detection.
