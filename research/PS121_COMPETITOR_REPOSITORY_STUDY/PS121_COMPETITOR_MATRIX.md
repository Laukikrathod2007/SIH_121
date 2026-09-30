# PS 121 — Competitor Capability Matrix

This matrix provides a strictly evidence-grounded capability comparison across the active direct competitor and domain repositories for **SIH 26121 (eRTMAC-NWIS)**.

### Legend:
- ✅ **Verified**: Actually implemented in inspected source code with functional logic.
- 🟡 **Partial / Mock**: Incomplete implementation, rule-based heuristic, or relying on static/synthetic mock data.
- ❌ **Not Found**: Feature is absent from the codebase.
- 🔴 **Placeholder**: Empty function, TODO, or stub without logic.

---

## 1. Active Direct Competitors Matrix (Committed in Recent Cycle)

| Capability / Dimension | dhanwanth (2026-09-26) | Physics0070 (2026-09-08) | vidhiii1711 (2026-09-23) | rudrachauhan (2026-09-20) | PetrolQ (2026-09-24) | pallavi (2026-09-27) | SIH_PLANNS (2026-09-22) | Proposed PS 121 Target Design |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Nearby Well Discovery** | ✅ (Haversine 6-factor) | ✅ (Postgres SQL) | ✅ (Mongo distance) | ✅ (Mongo query) | ✅ (PostGIS ST_DWithin) | ✅ (Geopy distance) | 🟡 (2D Haversine) | **3D Subsurface Proximity + Fault-Block Barrier Gating** |
| **GIS & Subsurface Mapping** | 🟡 (Leaflet 2D) | 🟡 (2D plot) | 🟡 (2D map) | 🟡 (2D map) | ✅ (MapLibre offline) | 🟡 (Leaflet 2D) | 🟡 (Vis.js graph) | **MapLibre GL 2D/3D + Three.js Subsurface Formations** |
| **3D Trajectory Calculation** | 🟡 (Raw MD/TVD) | 🟡 (Raw depth) | 🟡 (MD/TVD log) | 🟡 (Raw depth) | 🟡 (Basic Min Curv) | ❌ | ❌ | **Minimum Curvature $(MD,Inc,Az) \to (TVD,TVDSS,N,E,DLS)$** |
| **Historical Ingestion Engine**| 🟡 (CSV loader) | ✅ (Doc profiling) | 🟡 (JSON seed) | 🟡 (Doc endpoints) | 🟡 (PyMuPDF text) | ✅ (Qwen2.5-VL VLM) | ✅ (10 sample JSONs) | **Dual-Engine: High-Speed PyMuPDF + OpenCV Table Segmenter** |
| **Scanned OCR & Table Layout** | ❌ | 🟡 (Basic OCR) | ❌ | ❌ | 🟡 (EasyOCR) | ✅ (pypdfium+OpenCV) | 🟡 (Text extract) | **Hierarchical Table Cell Geometry + Confidence Gating** |
| **Drilling Event / NPT Model** | ✅ (XGBoost 5-models) | ✅ (Event schema) | ✅ (25-param telemetry)| ✅ (Event repo) | ✅ (Regex classifier) | ✅ (Whitelist parser) | ✅ (Regex + LLM) | **IADC / BSEE Normalized Drilling Ontology + Severity Scoring** |
| **Hybrid RAG Retrieval** | 🟡 (Summary search) | ✅ (Passage matching) | 🟡 (LLM prompt) | ✅ (Hybrid RAG) | ✅ (AHP BM25+pgvector)| ✅ (Qdrant vector) | 🟡 (Chroma vector) | **Dynamic $\Omega$-Reranking (Dense Vector + BM25 + Stratigraphic $\xi$)** |
| **Stratigraphic $\xi$ Normalization**| ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **Dimensionless Depth $\xi(d) = \frac{d_{tvdss}-Top}{Thickness} \in [0,1]$ across Dip** |
| **Ahead-of-Bit Lookahead Corridor**| 🟡 (Rule lookup) | 🟡 (Depth sample) | 🟡 (Early warning URL)| 🟡 (Risk predict) | 🟡 (Static Horizons) | ❌ | ❌ | **Autonomous $+50\text{m}$ to $+200\text{m}$ Predictive Risk Projection** |
| **PPFG Mud Window & Hydraulics** | 🟡 (Telemetry check) | ❌ | 🟡 (Pore pressure col)| ❌ | ✅ (Eaton PPFG) | ❌ | ❌ | **Dynamic Mud Window Margins ($MW_{act}-PP, FG-ECD$)** |
| **Decision Logging / Audit Trail**| 🟡 (Alert service) | ✅ (EngineerAction) | ✅ (DecisionLog) | 🟡 (Risk history) | 🟡 (Dossier export) | 🟡 (Review UI) | 🟡 (Briefing output)| **Structured Audit Trail Recording Operator Actions & Rationale** |
| **1-Click Visual PDF Provenance**| ❌ | 🟡 (Passage match) | ❌ | 🟡 (Doc ref) | 🟡 (Page text cite) | ✅ (Page crops) | ❌ | **Interactive PDF Canvas with Glowing Bounding-Box Overlays** |
| **Real-Time Telemetry & Anomaly**| ✅ (Isolation Forest) | ✅ (Replay service) | ✅ (Drilling stream) | ✅ (Telemetry stream) | 🟡 (Simulator) | ❌ | ✅ (FastDTW sequence)| **Multi-Channel Anomaly Detection + FastDTW Alignment** |

---

## 2. Key Codebase Insights & Inspiration Sources

1. **`dhanwanth-dh/eRTMAC--NWIS-Nearby-Wells-Intelligence-Offset-Decision-Support`**:
   - **Inspiration to Adopt**: Multi-hazard XGBoost classifier suite (`xgb_mud_loss`, `xgb_stuck_pipe`, `xgb_overpressure`, `xgb_torque_spike`, `xgb_cementing_issue`), Isolation Forest anomaly detection, and concrete 4-step operational action protocols.
2. **`Physics0070/nwis`**:
   - **Inspiration to Adopt**: Robust PostgreSQL database schema with explicit Alembic migrations and the `EngineerAction` feedback model (`accepted`, `rejected`, `investigating`, `resolved`).
3. **`tech-nitin/wellwise`**:
   - **Inspiration to Adopt**: High-fidelity Three.js 3D subsurface geological layer rendering with CSS2D callout annotations anchored to trajectory depths.
4. **`PetrolQ`**:
   - **Inspiration to Adopt**: PostGIS spatial queries (`ST_DWithin`), offline MapLibre raster tiles, and Eaton PPFG pore pressure calculations.
5. **`DrillMind`**:
   - **Inspiration to Adopt**: Multi-agent specialist architecture (`DrillingAgent`, `HistoricalAgent`, `SafetyAgent`) and BM25 + Dense Vector Reciprocal Rank Fusion (RRF $k=60$).
6. **`DDR_UTAH_FORGE`**:
   - **Inspiration to Adopt**: Multi-page layout segmentation, OCR quality confidence scoring, and OpenCV morphological table line detection.
