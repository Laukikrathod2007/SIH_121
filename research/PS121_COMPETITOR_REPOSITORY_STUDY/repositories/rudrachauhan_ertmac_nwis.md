# Competitor Repository Audit: rudrachauhan12999-eRTMAC-NWIS

## 1. Repository Metadata
- **Repository**: `rudrachauhan12999-eRTMAC-NWIS`
- **URL**: `https://github.com/rudrachauhan12999/eRTMAC-NWIS.git`
- **Owner**: rudrachauhan12999
- **Project**: eRTMAC-NWIS Nearby Wells Intelligence System (SIH 2026 PS 26121)
- **Category**: Direct Competitor
- **Relevance**: High (Complete FastAPI + MongoDB backend with dedicated API modules for alerts, documents, events, formations, RAG, risk, and telemetry)
- **Primary Language**: Python (FastAPI, Motor, MongoDB, Pydantic), TypeScript (React, Vite, Bun)
- **Files Inspected**: 150 files across `backend/app/api/`, `backend/app/db/`, `frontend/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React + Vite + TypeScript + Tailwind CSS]
   ├── Well Map & Offset Radius Selector (`wells.py`)
   ├── Formations & Lithology Inspector (`formations.py`)
   ├── Risk Evaluation & NPT Metrics (`risk.py`)
   └── Grounded RAG Assistant (`rag.py`)
        │
        ▼ (FastAPI REST API: `backend/app/main.py`)
[Backend API Layer (`backend/app/api/`)]
   ├── alerts.py (Threshold & hazard alerts)
   ├── documents.py (Document storage & metadata search)
   ├── events.py (Historical drilling events & NPT tracker)
   ├── formations.py (Subsurface formation boundaries)
   ├── rag.py (Hybrid RAG query endpoint)
   ├── risk.py (Multi-parameter risk prediction: depth, mud weight, formation)
   └── telemetry.py (Real-time telemetry ingestion)
        │
        ▼
[Data Layer (MongoDB via Motor AsyncIO)]
   └── Repositories: `wells_repo`, `events_repo`, `formations_repo`, `documents_repo`
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `backend/app/api/wells.py` | MongoDB geospatial queries on wellhead locations. |
| **GIS & Subsurface Mapping** | 🟡 **PARTIAL** | `frontend/src/` | 2D map viewer; lacks 3D trajectory and fault block overlay. |
| **Historical DDR Parsing** | 🟡 **PARTIAL** | `backend/app/api/documents.py` | Document upload and indexing; text extraction without full PDF OCR layout segmentation. |
| **OCR Processing** | ❌ **NOT FOUND** | N/A | Basic text extraction. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `backend/app/api/events.py` | Structured event logging with NPT duration and severity codes. |
| **RAG Retrieval** | ✅ **VERIFIED** | `backend/app/api/rag.py` | Hybrid RAG endpoint connecting indexed documents to LLM reasoning. |
| **Formation Correlation** | 🟡 **PARTIAL** | `backend/app/api/formations.py` | Stores formation intervals; no dip-aware thickness scaling $\xi(d)$. |
| **Depth Correlation** | 🟡 **PARTIAL** | `backend/app/api/risk.py` | Depth filtering on raw values. |
| **Incident Prediction** | ✅ **VERIFIED** | `backend/app/api/risk.py` | Evaluates risk score given depth, mud weight (SG), formation, and well ID. |
| **Knowledge Graph** | ❌ **NOT FOUND** | N/A | Relational MongoDB collections; no property graph. |
| **Evidence Citations** | ✅ **VERIFIED** | `backend/app/api/rag.py` | Returns document source references in RAG response. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `backend/app/api/telemetry.py` | Telemetry endpoint accepting streaming parameter updates. |

---

## 4. Code-Level Investigation & Observations
1. **Modular Backend Design**:
   - Highly organized FastAPI codebase with clean separation across routers (`alerts`, `documents`, `events`, `formations`, `rag`, `risk`, `telemetry`, `wells`) and async MongoDB repositories.
2. **Open Subsurface Challenges**:
   - Depth and formation correlation are handled via discrete lookup intervals rather than continuous 3D trajectory interpolation.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt**: Clean API modularization separating alerts, formations, telemetry, and risk.
- **To Advance**: Utilize PostgreSQL + PostGIS + pgvector (instead of MongoDB) to combine spatial geometry, relational integrity, and vector search in a single atomic database.
