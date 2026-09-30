# Competitor Repository Audit: Physics0070-nwis

## 1. Repository Metadata
- **Repository**: `Physics0070-nwis`
- **URL**: `https://github.com/Physics0070/nwis.git`
- **Owner**: Physics0070
- **Project**: NWIS — Nearby Wells Intelligence System (SIH 2026 PS 26121)
- **Category**: Direct Competitor
- **Relevance**: High (Direct submission with complete PostgreSQL schema, telemetry replay, and model profiling)
- **Primary Language**: Python (FastAPI, SQLAlchemy, Alembic, PostgreSQL), React
- **Files Inspected**: 100+ files across `backend/app/`, `artifacts/profiling/`, `NWIS_SIH2026_IdeaSubmission_v6.pdf`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React + REST API]
   ├── Geospatial Well Map & Formation Track Viewer
   ├── Telemetry Replay & Anomaly Monitor (`replay.py`)
   └── Decision Support & Engineer Feedback Loop (`intelligence.py`)
        │
        ▼ (FastAPI REST API: `backend/app/main.py`)
[Application Services Layer (`backend/app/services/`)]
   ├── intelligence.py (Risk scoring, anomaly detection, engineer feedback)
   ├── document_search.py (Passage matching & semantic retrieval)
   ├── risk.py (Multi-factor drilling risk calculator)
   └── replay.py (Step-by-step depth & telemetry playback)
        │
        ▼
[Data Layer (PostgreSQL + SQLAlchemy + Alembic)]
   ├── Models: `Well`, `WellEmbedding`, `DrillingEvent`, `RiskAlert`, `TelemetrySample`, `EngineerAction`
   └── Alembic Migrations: `20260907_0000_initial_schema.py`
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `backend/app/api/routes/wells.py` | Geospatial and relational offset well queries from PostgreSQL. |
| **GIS & Subsurface Mapping** | 🟡 **PARTIAL** | `backend/app/api/routes/wells.py` | Returns wellhead lat/lon coordinates; lacks full 3D trajectory and fault block overlay. |
| **Historical DDR Parsing** | ✅ **VERIFIED** | `artifacts/profiling/document_ingestion.json` | Parsed public well reports into structured `DrillingEvent` records. |
| **OCR Processing** | 🟡 **PARTIAL** | `artifacts/profiling/document_reextraction.json` | Text-layer extraction with basic OCR fallback. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `backend/app/models/base.py` | Structured event storage with NPT duration and severity classification. |
| **RAG Retrieval** | ✅ **VERIFIED** | `backend/app/services/document_search.py` | Embedding-based passage matching against stored document chunks. |
| **Hybrid Search** | 🟡 **PARTIAL** | `backend/app/services/document_search.py` | Vector search + metadata filtering; lacks dynamic mathematical RRF fusion. |
| **Formation Correlation** | 🟡 **PARTIAL** | `backend/app/api/routes/intelligence.py` | Formation string matching; lacks dip-corrected stratigraphic thickness scaling $\xi(d)$. |
| **Depth Correlation** | 🟡 **PARTIAL** | `_sample_near_depth()` in `intelligence.py` | Matches telemetry sample closest to depth; uses flat Measured Depth (MD). |
| **Incident Prediction** | ✅ **VERIFIED** | `backend/app/services/risk.py` | Multi-factor risk calculation combining offset events, anomaly scores, and mud weight. |
| **Engineer Feedback Loop** | ✅ **VERIFIED** | `intelligence.py` L30-65 | Explicit engineer feedback tracking (`accepted`, `rejected`, `investigating`, `resolved`) stored in `EngineerAction` model. |
| **Evidence Citations** | ✅ **VERIFIED** | `PassageMatchOut` in `schemas/models.py` | Returns matched document passages with page numbers and relevance scores. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `backend/app/api/routes/replay.py` | Database-backed time-depth telemetry playback. |

---

## 4. Code-Level Investigation & Observations
1. **Strong Data Engineering**:
   - `Physics0070-nwis` has one of the cleanest PostgreSQL relational schemas in the competition, with explicit Alembic migrations and structured models (`Well`, `DrillingEvent`, `RiskAlert`, `EngineerAction`).
2. **Actionable Engineer Feedback Loop**:
   - Implements an explicit feedback mechanism allowing drilling engineers to accept or reject AI recommendations, recording human decisions into the database.
3. **Open Subsurface Challenges**:
   - Relies on raw depth matching in `_sample_near_depth()`, which does not account for structural formation dip or 3D wellbore deviation.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt**: Adopt the robust relational database schema structure and the engineer feedback audit trail (`EngineerAction`).
- **To Advance**: Layer 3D True Vertical Depth Subsea (TVDSS) conversion, Stratigraphic Normalization $\xi(d)$, and PostGIS fault block isolation on top of the relational model.
