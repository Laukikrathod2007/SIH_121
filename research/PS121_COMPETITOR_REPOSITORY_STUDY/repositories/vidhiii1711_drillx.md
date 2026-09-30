# Competitor Repository Audit: vidhiii1711-eRTMAC-NWIS (Team DrillX)

## 1. Repository Metadata
- **Repository**: `vidhiii1711-eRTMAC-NWIS`
- **URL**: `https://github.com/vidhiii1711/eRTMAC-NWIS.git`
- **Owner**: vidhiii1711 (Team DrillX — Team ID 120811)
- **Project**: eRTMAC-NWIS Nearby Wells Intelligence System (SIH 2026 PS 26121)
- **Category**: Direct Competitor
- **Relevance**: High (Fullstack web platform with live Vercel deployment)
- **Primary Language**: JavaScript (Node.js/Express, React, Tailwind CSS, MongoDB)
- **Files Inspected**: 176 files across `backend/controllers/`, `backend/data/`, `frontend/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React + Tailwind CSS + Lucide Icons (Vercel Deployed)]
   ├── Geospatial Well Map & Formation Selector
   ├── Real-time Early Warning Dashboard (`earlyWarningController.js`)
   ├── WellMind Copilot Chat (`wellmindController.js`)
   └── Decision Log & Audit History (`DecisionLogController.js`)
        │
        ▼ (Express.js REST API: `backend/server.js`)
[Backend Controllers Layer (`backend/controllers/`)]
   ├── earlyWarningController.js (Live ML telemetry warning forwarder)
   ├── riskController.js (Formation & mud weight risk evaluation)
   ├── wellController.js (Well CRUD & offset query)
   └── wellmindController.js (LLM query assistant)
        │
        ▼
[Data Layer (MongoDB + Static JSON Datasets)]
   ├── `backend/data/drilling_timeseries_balanced.json` (Time-series telemetry)
   ├── `backend/data/formations.json` (Formation top intervals)
   └── `backend/data/event_log.json` (Historical kicks, losses, and fishing jobs)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `backend/controllers/wellController.js` | MongoDB spatial distance and field-based offset well lookup. |
| **GIS & Subsurface Mapping** | 🟡 **PARTIAL** | `frontend/src/` | Interactive map component; 2D surface wellhead markers. |
| **Historical DDR Parsing** | 🟡 **PARTIAL** | `backend/seed.js`, `data/event_log.json` | Pre-parsed JSON events loaded into MongoDB; lacks on-the-fly PDF OCR. |
| **OCR Processing** | ❌ **NOT FOUND** | N/A | No PDF OCR pipeline in the Node backend. |
| **NLP Event Extraction** | 🟡 **PARTIAL** | `data/event_log.json` | Categorized historical events (`Kick_Label`, `Fishing_Label`, `Mud_Loss`). |
| **RAG Retrieval** | 🟡 **PARTIAL** | `controllers/wellmindController.js` | Direct LLM API query over database summaries; no standalone vector store (pgvector/Qdrant). |
| **Formation Correlation** | 🟡 **PARTIAL** | `data/formations.json` | Relies on predefined formation JSON boundaries; no dip-aware thickness scaling $\xi(d)$. |
| **Depth Correlation** | 🟡 **PARTIAL** | `earlyWarningController.js` | Uses raw `Depth_MD` and `Depth_TVD` columns. |
| **Incident Prediction** | ✅ **VERIFIED** | `earlyWarningController.js` L10-40 | Calls an external ML microservice endpoint (`ML_REALTIME_WARNING_URL`) with 25+ parameters. |
| **Decision Log Audit** | ✅ **VERIFIED** | `DecisionLogController.js` | Persists operator actions and recommendations in MongoDB. |
| **Evidence Citations** | 🟡 **PARTIAL** | `controllers/wellmindController.js` | Text citations linking to database event IDs. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `data/drilling_timeseries.json` | Time-series telemetry replay with 20+ drilling channels. |

---

## 4. Code-Level Investigation & Observations
1. **Fullstack Integration**:
   - Clean separation of concerns between Express controllers and React UI, with working authentication (`authController.js`), decision logging, and live deployment configuration.
2. **Heavy Telemetry Schema**:
   - Features a rich telemetry schema (ROP, WOB, RPM, Torque, SPP, Flow Rate, Mud Weight, PV, YP, Hook Load, Pore Pressure).
3. **Open Subsurface Challenges**:
   - The ML warning service is decoupled as an external URL (`http://localhost:8000/realtime-warning`). Data correlation across wells relies on pre-populated JSON arrays rather than dynamic 3D spatial trajectory calculations.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt**: Clean operator decision logging (`DecisionLogController`) and comprehensive multi-parameter telemetry schemas.
- **To Advance**: Unify the ML and physical models (Eaton PPFG, Stratigraphic $\xi(d)$ sync) directly inside the backend service with PostGIS spatial indexing.
