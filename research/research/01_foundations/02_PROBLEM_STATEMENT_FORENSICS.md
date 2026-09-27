# SIH 26121 — Problem Statement Forensics & Requirement Decomposition

## 1. Official Metadata
- **Problem Statement ID:** 26121
- **Problem Statement Title:** eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations
- **Organization:** Oil India Limited (OIL)
- **Category:** Software
- **Theme:** Smart Automation / Oil & Gas Digitalization
- **Primary Source Document:** [PROBLEM_STATEMENT.md](file:///d:/Programming/Project%203.0/PS121/PROBLEM_STATEMENT.md) `[PRIMARY-SOURCE]`

---

## 2. Requirement Decomposition Matrix

The official text is forensically broken down into its constituent technical, functional, and operational requirements.

### Requirement 1: Geospatial Nearby Wells Visualization
- **Exact Wording:** *"Display nearby wells on a geospatial map relative to the active well"* (Problem Description §i) and *"Provide an interactive map-based visualization of nearby wells within a user-defined radius"* (Expected Outcome §ii).
- **Requirement Category:** Geospatial / GIS & Spatial Filtering.
- **Underlying Business Problem:** Drilling engineers cannot quickly visualize spatial clustering, directional relationships, and reservoir proximity between the active wellbore and historical penetrations.
- **Expected Inputs:** Active well surface coordinates (Latitude/Longitude, UTM), wellhead locations of historical wells, user-configurable search radius (e.g. 1 km to 50 km), filter criteria (field, formation, well status, vintage).
- **Expected Outputs:** Interactive GIS map rendered with active well center, offset well markers, spatial distance buffers, trajectory traces (2D projection), and clickable metadata cards.
- **Intended User:** Drilling Engineers, Well Planners, eRTMAC Command Centre Engineers, Operations Geologists.
- **Operational Timing:** Pre-drill planning phase AND continuously updated during live drilling operations.
- **Technical Implication:** Spatial indexing (PostGIS / R-Tree / GeoJSON), coordinate system transformations (WGS84, Indian Everest 1956 datum, UTM zones 45N/46N for Assam/Assam-Arakan basin).
- **Validation Implication:** Verification of Euclidean and geodesic distance calculations, handling directional wells where surface location is distant from reservoir bottom-hole location (BHL).
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 2: Automated Ingestion & Information Extraction
- **Exact Wording:** *"Use AI, NLP, OCR, and data analytics to automatically extract and structure information from historical drilling reports and well documents"* (Expected Outcome §i).
- **Requirement Category:** Document Intelligence / Multi-Modal Parsing / OCR / Information Extraction.
- **Underlying Business Problem:** Decades of operational experience are locked in unstructured PDF documents, scanned physical reports, daily logs, and tabular records. Manual extraction takes days or weeks per well.
- **Expected Inputs:** Daily Drilling Reports (DDRs), Well Completion Reports (WCRs), End-of-Well Reports (EOWRs), Mud Logging records, Casing/Cementing tallies, scanned legacy documents.
- **Expected Outputs:** Structured operational entities (depth intervals, formation tops, BHA components, mud weights, NPT events, casing shoes, bit runs, operational narratives) stored in queryable relational/vector schema.
- **Intended User:** Data Engineers, Ingestion Pipelines, Operations Personnel.
- **Operational Timing:** Batch historical ingestion pipeline prior to active operations; incremental daily ingestion as new DDRs arrive.
- **Technical Implication:** Hybrid OCR engine (Tesseract/PaddleOCR/AWS Textract style layout analysis), PDF layout parsing (PyMuPDF/PDFMiner), table extraction (Camelot/Tabula/VLM), entity extraction LLM/NLP pipelines, schema validation.
- **Validation Implication:** Field-level extraction precision, recall, and F1 score against manual ground-truth drilling logs.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 3: Searchable Knowledge Repository & Institutional Memory
- **Exact Wording:** *"Provide instant access to historical drilling experiences and operational events from offset wells"* (Problem Description §ii) and *"Create a searchable knowledge repository of drilling events, lessons learned, operational challenges, and mitigation measures"* (Expected Outcome §iii).
- **Requirement Category:** Information Retrieval / Semantic Search / Institutional Memory.
- **Underlying Business Problem:** When an unexpected event occurs on the rig, personnel rely on personal memory or phone calls to senior engineers. When senior engineers retire or rotate off-shift, institutional knowledge is lost.
- **Expected Inputs:** Natural language queries (e.g. *"Show mud losses in Barail formation with mud weight > 1.35 SG"*), parametric filters (formation, depth, event type, severity).
- **Expected Outputs:** Ranked historical events, summaries of challenges encountered, documented mitigation measures, links to original report pages, and confidence scores.
- **Intended User:** Rig Superintendent, Drilling Supervisor (Company Man), Shift Drilling Engineer, Office Review Team.
- **Operational Timing:** Real-time operational troubleshooting (seconds to minutes) and pre-spud offset review.
- **Technical Implication:** Hybrid retrieval system combining keyword/parametric filtering (SQL/BM25) with dense semantic search (vector embeddings), metadata filtering, and citation grounding.
- **Validation Implication:** Retrieval metrics (Mean Reciprocal Rank - MRR, NDCG@K, Precision@K), zero hallucination rate on operational advice.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 4: Multi-Dimensional Cross-Well Correlation
- **Exact Wording:** *"Correlate drilling parameters, reservoir characteristics, mud losses, kicks, stuck pipe incidents, casing programs, cementing practices, and formation-specific risks across wells"* (Problem Description §iii) and *"Correlate geological, drilling, and reservoir data across wells based on depth and formation"* (Expected Outcome §iv).
- **Requirement Category:** Subsurface Correlation / Cross-Well Analytics / Interval Matching.
- **Underlying Business Problem:** Formations dip, fault, and change thickness across a field. Comparing wells solely by Measured Depth (MD) yields erroneous correlations. Cross-well alignment requires True Vertical Depth Subsea (TVDSS) and stratigraphic markers.
- **Expected Inputs:** Formation tops, lithology descriptions, Well Trajectory surveys (inclination, azimuth, MD, TVD), Mud logs, Log-While-Drilling (LWD/MWD) curves (Gamma Ray, Resistivity).
- **Expected Outputs:** Normalized cross-well interval alignment, structural cross-sections, stratigraphic correlation panels, historical hazard distributions across formations.
- **Intended User:** Operations Geologists, Petrophysicists, Drilling Engineers.
- **Operational Timing:** Pre-drill section planning and dynamic revision while drilling as formation boundaries are penetrated.
- **Technical Implication:** Dynamic Time Warping (DTW) on well logs, stratigraphic alignment engines, TVD/TVDSS conversion from directional surveys, interval-to-interval mapping.
- **Validation Implication:** Geometrical and geological fidelity verified against known marker horizons.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 5: Predictive Risk Analytics Across Five Core Failure Modes
- **Exact Wording:** *"Develop predictive analytics models that can identify potential drilling risks such as mud losses, stuck pipe, overpressure zones, torque spikes, or cementing issues based on historical offset-well behaviour"* (Expected Outcome §v).
- **Requirement Category:** Predictive Analytics / Machine Learning / Domain Risk Modeling.
- **Underlying Business Problem:** Drilling hazards incur catastrophic Non-Productive Time (NPT) costing $50,000 to $500,000+ per incident in rig dayrates, lost equipment, sidetracks, or well abandonment.
- **Specific Hazard Breakdown:**
  1. *Mud Losses (Lost Circulation):* Fractured or depleted sands taking drilling fluid.
  2. *Stuck Pipe:* Differential sticking across porous formations or mechanical sticking from cavings/key seating.
  3. *Overpressure Zones & Kicks:* Influx of formation gas, oil, or water into the wellbore due to underbalanced mud weight.
  4. *Torque Spikes & Stick-Slip:* Torsional vibration, bit balling, or borehole friction threatening BHA failure and drillstring twist-off.
  5. *Cementing Issues:* Channeling, incomplete mud displacement, loss of returns during cementing, or poor zonal isolation.
- **Expected Inputs:** Historical offset hazard occurrences, formation properties, pore pressure/fracture gradient curves, live surface telemetry (WOB, RPM, Torque, SPP, Flow Out, Pit Volume, Mud Weight).
- **Expected Outputs:** Quantitative risk scores (0–100% or Low/Medium/High/Critical) per hazard family, projected depth risk windows, lead-time warnings ahead of the bit.
- **Intended User:** Real-Time Operations Engineers, Drilling Engineers, Directional Drillers.
- **Operational Timing:** Minutes to hours ahead of penetrating the hazardous interval.
- **Technical Implication:** Decoupled specialized model pipelines per risk family (XGBoost/LightGBM for tabular classification, time-series anomaly detection, geomechanical physics bounds).
- **Validation Implication:** Precision, Recall, False Alarm Rate, Area Under Precision-Recall Curve (PR-AUC), and advance warning lead-time.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 6: Proactive Alerts & Actionable Engineering Recommendations
- **Exact Wording:** *"Generate proactive alerts when current drilling operations approach depths or formations where similar challenges were encountered in nearby wells"* (Problem Description §iv) and *"Generate real-time alerts and recommendations to assist drilling engineers in proactive decision-making"* (Expected Outcome §vi).
- **Requirement Category:** Real-Time Alerting / Decision Support / Early Warning Engine.
- **Underlying Business Problem:** Reactive alarms sound only after an incident occurs (e.g. pit gain alarm after kick is already inside casing). Engineers require proactive warnings *before* entering the danger corridor.
- **Expected Inputs:** Real-time drilling telemetry (bit depth, hole depth, current formation, telemetry parameters) compared against the historical offset risk register.
- **Expected Outputs:** Multi-level alerts (Advisory, Caution, Critical Alert), advance notice distance (e.g., *"Approaching Kopili Shale in 35 m; offset wells experienced severe sloughing and pack-offs"*), historical mitigation guidance (recommended mud weight window, trip procedures, LCM on standby).
- **Intended User:** Rig-site Drilling Supervisor (Company Man), eRTMAC Remote Monitoring Engineer.
- **Operational Timing:** Continuous live stream processing during active drilling runs.
- **Technical Implication:** State-aware alerting engine, threshold dampening to prevent alarm fatigue, lead-time calculation based on Rate of Penetration (ROP).
- **Validation Implication:** Timeliness of alert delivery, audit trail linking alert directly to historical report pages.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

### Requirement 7: Unified Decision-Support Dashboard alongside eRTMAC
- **Exact Wording:** *"Present information through a user-friendly dashboard for field and office-based personnel"* (Expected Outcome §vii) and *"Develop an AI/ML-enabled Nearby Wells Intelligence System (NWIS) that acts as a standalone decision-support platform alongside eRTMAC that has institutional memory"* (Expected Outcome §opening).
- **Requirement Category:** Human-Computer Interface (HCI) / Mission-Critical Dashboard.
- **Underlying Business Problem:** Information fragmentation across legacy software, spreadsheets, and paper binders forces engineers to context-switch under high stress.
- **Expected Inputs:** User selections (active well, offset wells, depth slider, alert filter).
- **Expected Outputs:** High-density, dark-mode, responsive operational console displaying:
  1. Active Well Overview & Live Rig Telemetry
  2. Interactive Geospatial Offset Map
  3. Dynamic Depth & Formation Stratigraphic Correlation Track
  4. Real-Time Risk Register & Approaching Risk Corridors
  5. Searchable Institutional Memory Knowledge Base with PDF Page Viewer
  6. Audit trail showing exact justification for every recommendation.
- **Intended User:** Both field personnel (Rig Manager, Company Man, Mud Engineer) and office personnel (eRTMAC Chief Engineer, General Manager Drilling, Asset Geologist).
- **Operational Timing:** 24/7 continuous operation in drilling command centers and rig cabins.
- **Technical Implication:** Web-based responsive frontend (React / Vite / high-density data tables), WebSocket telemetry feeds, embedded PDF viewer with bounding box highlights.
- **Validation Implication:** Ergonomics, usability under low-bandwidth rig connections, sub-second interface responsiveness.
- **Epistemic Classification:** `[VERIFIED]` Explicit PS Requirement.

---

## 3. Explicit vs. Inferred Boundary Matrix

To maintain total fidelity to the problem statement, the system capabilities are partitioned into what OIL explicitly demanded versus what is technically inferred to fulfill those demands:

| Capability Component | Explicit in PS Text | Inferred Technical Requirement | Status & Rationale |
| :--- | :---: | :---: | :--- |
| Geospatial Map with User-Defined Radius | **YES** | No | `[EXPLICIT]` Stated verbatim in Problem Description §i and Outcome §ii. |
| Extract from DDRs, WCRs, Mud Logs via OCR/NLP | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §i and Data Availability §i–ix. |
| Searchable Knowledge Repository of Lessons Learned | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §iii. |
| Cross-Well Correlation by Depth and Formation | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §iv. |
| Predictive Risk for Mud Losses, Stuck Pipe, Kicks, Torque, Cementing | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §v. |
| Proactive Alerts & Recommendations | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §vi. |
| Standalone Platform operating Alongside eRTMAC | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome preamble. |
| User-Friendly Dashboard for Field & Office Personnel | **YES** | No | `[EXPLICIT]` Stated verbatim in Outcome §vii. |
| Dynamic Offset Relevance Weighting (Beyond Distance) | No | **YES** | `[INFERRED]` Necessary because nearest well across fault/structure is technically non-comparable. |
| Historical Risk Corridor Visualization Track | No | **YES** | `[INFERRED]` Visual manifestation of approaching depth-indexed risks required by Outcome §vi. |
| Original Document Page Bounding-Box Evidence Display | No | **YES** | `[INFERRED]` Essential for human-in-the-loop verification in high-risk engineering environments. |
| Decoupled Multi-Model ML Architecture | No | **YES** | `[INFERRED]` Physical impossibility of a single model predicting all 5 distinct risk mechanisms. |
| WITSML / OSDU Data Ingestion Adapter | No | **YES** | `[INFERRED]` Necessary to interoperate seamlessly alongside eRTMAC and industry telemetry feeds. |
| Autonomous Closed-Loop Drawworks/Pump Control | **NO (EXCLUDED)** | **NO (EXCLUDED)**| `[OUT-OF-SCOPE]` NWIS is strictly decision support; autonomous control violates OIL safety protocols. |
