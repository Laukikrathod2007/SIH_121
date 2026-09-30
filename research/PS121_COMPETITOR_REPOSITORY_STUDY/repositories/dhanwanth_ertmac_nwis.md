# Competitor Repository Audit: dhanwanth-eRTMAC-NWIS

## 1. Repository Metadata
- **Repository**: `dhanwanth-eRTMAC-NWIS`
- **URL**: `https://github.com/dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support.git`
- **Owner**: dhanwanth-dh
- **Project**: eRTMAC-NWIS — AI-Powered Offset Well Decision Support Platform
- **Category**: **Active Direct Competitor** (Latest Commit: 2026-09-26 — 2 days ago)
- **Relevance**: Very High (One of the most feature-complete fullstack implementations in the competition)
- **Primary Language**: Python (FastAPI, Scikit-learn, XGBoost, Joblib), React 19 (Tailwind CSS, Lucide Icons)
- **Files Inspected**: 45+ backend & frontend files across `backend/api/`, `backend/models/`, `backend/services/`, `backend/trained_models/`, `frontend/src/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[Frontend: React 19 + Tailwind CSS + Lucide Icons]
   ├── Live Monitoring Dashboard (`LiveMonitoring.jsx`, `useLiveData.js`)
   ├── Risk Analytics & Anomaly Gauges (`RiskAnalytics.jsx`)
   ├── Offset Well Comparison Matrix (`WellComparison.jsx`, `NearbyWells.jsx`)
   ├── Document Intelligence & Historical Events (`Documents.jsx`, `HistoricalEvents.jsx`)
   └── AI Decision Support Assistant (`AIAssistant.jsx`)
        │
        ▼ (FastAPI REST API: `backend/main.py`)
[Unified Real-Time Decision Engine (`backend/services/decision_engine.py`)]
   ├── similarity_service.py (6-Factor deterministic analog matching engine)
   ├── nearby_well_service.py (Haversine spatial offset radius queries)
   ├── alert_service.py (Real-time threshold and anomaly alerts)
   └── recommendation_service.py (Step-by-step operational mitigation protocols)
        │
        ▼
[Pre-Trained Machine Learning Models (`backend/trained_models/`)]
   ├── XGBoost Multi-Hazard Classifiers:
   │     ├── `xgb_mud_loss.joblib` (Lost circulation probability)
   │     ├── `xgb_stuck_pipe.joblib` (Pipe sticking probability)
   │     ├── `xgb_overpressure.joblib` (Abnormal pore pressure probability)
   │     ├── `xgb_torque_spike.joblib` (Stick-slip / mechanical binding)
   │     └── `xgb_cementing_issue.joblib` (Zonal isolation / channeling)
   ├── Isolation Forest: `isolation_forest.joblib` (Unsupervised telemetry anomaly detection)
   └── Time-Series Predictors: `timeseries_rop_m_hr.joblib`, `timeseries_standpipe_pressure_psi.joblib`, `timeseries_torque_knm.joblib`
        │
        ▼
[Data Layer (CSV Data Store: `backend/data/`)]
   └── `wells.csv`, `well_trajectory.csv`, `historical_events.csv`, `historical_drilling.csv`, `live_drilling_stream.csv`
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `services/nearby_well_service.py` | Haversine distance with exponential decay weighting ($e^{-d/12.0}$). |
| **GIS & Subsurface Mapping** | 🟡 **PARTIAL** | `frontend/src/components/WellMap.jsx` | 2D map viewer for offset wells; lacks 3D trajectory rendering. |
| **Historical DDR Parsing** | 🟡 **PARTIAL** | `services/document_processor.py` | Loads structured CSV/JSON historical event records; lacks PDF OCR engine. |
| **OCR Processing** | ❌ **NOT FOUND** | N/A | Assumes tabular CSV inputs. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `backend/data/historical_events.csv` | Structured multi-hazard event taxonomy (MUD_LOSS, STUCK_PIPE, KICK). |
| **RAG Retrieval** | 🟡 **PARTIAL** | `services/retrieval_service.py` | Keyword & similarity retrieval over historical document summaries. |
| **6-Factor Analog Matching**| ✅ **VERIFIED** | `services/similarity_service.py` L15-60 | Multi-factor weighted score: `Geographic (20%)`, `Formation (20%)`, `Depth (15%)`, `Lithology (15%)`, `Drilling Profile (15%)`, `Event Profile (15%)`. |
| **Trained ML Models** | ✅ **VERIFIED** | `backend/trained_models/*.joblib` | 5 trained XGBoost classifiers + Isolation Forest + 3 Time-series regressors. |
| **Actionable Recommendations**| ✅ **VERIFIED** | `services/recommendation_service.py` | Generates 4-step concrete operational mitigations (pump rate adjustments, LCM pill formulations, trip tank checks). |
| **Stratigraphic Normalization**| ❌ **NOT FOUND** | `similarity_service.py` L35-40 | Compares total depth differences ($|TD_{\text{act}} - TD_{\text{off}}|$) rather than formation thickness scaling $\xi(d)$. |
| **Real-Time Telemetry** | ✅ **VERIFIED** | `api/realtime.py`, `live_drilling_stream.csv` | Telemetry stream endpoint feeding anomaly detector. |

---

## 4. Code-Level Investigation & Observations
1. **Outstanding Engineering Strengths to Learn From**:
   - **XGBoost Multi-Hazard Ensemble**: Separate specialized models for mud loss, stuck pipe, overpressure, and torque spikes rather than a single generic risk score.
   - **Actionable Operational Guidance**: `recommendation_service.py` outputs specific engineering numbers (e.g. "Reduce main mud pump output to 2150–2250 LPM to lower ECD; line up 40 bbl coarse calcium carbonate LCM pill") rather than generic advice.
2. **Identified Technical Limitations / Open Challenges**:
   - **Depth Slicing**: Evaluates total depth difference ($1.0 - \frac{|\Delta TD|}{1800}$) rather than true stratigraphic interval normalization $\xi(d)$.
   - **Data Storage**: Backed by flat CSV files (`backend/data/`) loaded into memory rather than a spatial PostgreSQL + PostGIS database.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt as Code Inspiration**:
  1. The multi-hazard XGBoost classifier approach (`xgb_mud_loss`, `xgb_stuck_pipe`, `xgb_overpressure`).
  2. The concrete 4-step operational recommendation format (`operational_steps` array with priority and confidence scores).
- **To Advance Beyond Competitor**:
  1. Migrate from flat CSV files to PostgreSQL + PostGIS + pgvector.
  2. Implement True Stratigraphic Normalization $\xi(d)$ across regional dip.
  3. Integrate multi-modal PDF OCR for direct document ingestion.
