# Competitor Repository Audit: suryanshkota07-AROH (AROH Drilling Intelligence)

## 1. Repository Metadata
- **Repository**: `suryanshkota07-AROH`
- **URL**: `https://github.com/suryanshkota07-oss/AROH-drilling-intelligence.git`
- **Owner**: suryanshkota07-oss
- **Project**: AROH Drilling Intelligence (SIH 2026 PS 26121)
- **Category**: Direct Competitor
- **Relevance**: High (Clean deterministic analog matching and risk prediction AI algorithms)
- **Primary Language**: Python (FastAPI, Pydantic, NumPy)
- **Files Inspected**: 73 files across `ai/`, `backend/`, `data/`.

---

## 2. Architecture & Tech Stack Reconstructed
```
[FastAPI Backend: `backend/main.py`]
        │
        ▼
[AI Algorithms Layer (`ai/`)]
   ├── analogue_matching.py (Deterministic multi-factor analog scoring)
   ├── evidence_retrieval.py (Evidence-oriented document chunk retrieval)
   └── risk_ahead.py (Forward depth hazard projection)
        │
        ▼
[Data Layer (`data/`)]
   ├── `wells.json` (Well metadata & coordinates)
   ├── `formation_intervals.json` (Formation top/bottom markers)
   ├── `drilling_events.json` (Structured historical hazards)
   └── `evidence_records.json` (Ground truth evidence items)
```

---

## 3. Verified vs Mock vs Claimed Breakdown

| Capability / Feature | Implementation Status | Evidence / Code Path | Notes & Findings |
| :--- | :--- | :--- | :--- |
| **Nearby Well Discovery** | ✅ **VERIFIED** | `ai/analogue_matching.py` L20-30 | Multi-factor weighted score: `formation (0.30)`, `trajectory (0.25)`, `proximity (0.20)`, `depth (0.15)`, `drilling (0.10)` with 25 km cutoff. |
| **GIS & Subsurface Mapping** | 🟡 **PARTIAL** | `backend/main.py` | JSON coordinate endpoints; lacks interactive 3D map. |
| **Historical DDR Parsing** | 🟡 **PARTIAL** | `data/drilling_events.json` | Pre-parsed JSON events; lacks direct PDF OCR ingestion. |
| **NLP Event Extraction** | ✅ **VERIFIED** | `data/` schema | Structured hazard logging (losses, kicks, stuck pipe). |
| **RAG Retrieval** | ✅ **VERIFIED** | `ai/evidence_retrieval.py` | Deterministic score-ranked evidence retrieval. |
| **Formation Correlation** | 🟡 **PARTIAL** | `ai/analogue_matching.py` | Formation interval matching; lacks dip-corrected stratigraphic thickness scaling $\xi(d)$. |
| **Depth Correlation** | 🟡 **PARTIAL** | `ai/analogue_matching.py` | Linear depth proximity score. |
| **Ahead-of-the-Bit Risk** | ✅ **VERIFIED** | `ai/risk_ahead.py` | Forward risk projection along depth interval. |
| **Evidence Citations** | ✅ **VERIFIED** | `ai/evidence_retrieval.py` | Strict citation linking to evidence record IDs. |

---

## 4. Code-Level Investigation & Observations
1. **Mathematical Cleanliness**:
   - `suryanshkota07-AROH` features an exceptionally clean, well-tested Python module for analog matching with explicit multi-factor weighting (`WEIGHTS = {"formation": 0.30, "trajectory": 0.25, "proximity": 0.20, "depth": 0.15, "drilling_characteristics": 0.10}`).
2. **Open Subsurface Challenges**:
   - Data is stored in static JSON files (`data/wells.json`, `data/formation_intervals.json`), lacking relational/spatial database persistence.

---

## 5. Key Architectural Takeaways for PS 121
- **To Adopt**: The multi-factor analog scoring weights and clean separation of `analogue_matching`, `evidence_retrieval`, and `risk_ahead`.
- **To Advance**: Scale the algorithm from static JSON into PostGIS spatial queries and True Stratigraphic Normalization ($\xi$).
