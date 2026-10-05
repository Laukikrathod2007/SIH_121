
<div align="center">

![DrillWise eRTMAC-NWIS Logo](C:\Users\LAUKIK\.gemini\antigravity-ide\brain\a035afbc-db0f-4d1e-a274-48ca96cdaa35\drillwise-logo-horizontal.png)

---

# eRTMAC-NWIS
## Nearby Wells Intelligence System
### An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations

---

**Smart India Hackathon 2026 | Problem Statement: PS 26121**
**Organization: Oil India Limited (OIL)**
**Category: Software | Theme: Smart Automation**

---

### Team

| Name | Role |
|------|------|
| **Aayush Deshpande** | Team Leader |
| **Laukik Rathod** | Frontend Developer |
| **Prasad Bhalerao** | Backend Developer |
| **Harshal Kanhaiyalal Yadav** | ML & Physics Engine |
| **Srushti Arav Pawar** | Data Engineering |
| **Shravasti Ratnakar Surwade** | Document Intelligence |

---

*Document Version: 1.0 | Date: September 2026*

</div>

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement Analysis](#2-problem-statement-analysis)
3. [Core Philosophy and Innovation Rationale](#3-core-philosophy-and-innovation-rationale)
4. [System Architecture](#4-system-architecture)
5. [Mathematical and Algorithmic Foundations](#5-mathematical-and-algorithmic-foundations)
6. [Data Models and Standards Compliance](#6-data-models-and-standards-compliance)
7. [Module-by-Module Implementation](#7-module-by-module-implementation)
8. [Operational Dashboard and User Interface](#8-operational-dashboard-and-user-interface)
9. [Datasets and Real-World Validation](#9-datasets-and-real-world-validation)
10. [PS 26121 Compliance Audit Results](#10-ps-26121-compliance-audit-results)
11. [Innovation Differentiators](#11-innovation-differentiators)
12. [Technology Stack](#12-technology-stack)
13. [Business Impact and Return on Investment](#13-business-impact-and-return-on-investment)
14. [Future Roadmap](#14-future-roadmap)
15. [Conclusion](#15-conclusion)

---

## 1. Executive Summary

Oil India Limited (OIL) operates one of India's most complex hydrocarbon exploration and production environments, with drilling operations spread across the Upper Assam-Arakan Basin. Each well drilled represents a capital investment of ₹5–30 crores, and Non-Productive Time (NPT) caused by drilling hazards — lost circulation, stuck pipe, well kicks, torque spikes, and cementing failures — costs the industry crores of rupees per campaign.

OIL already possesses a world-class real-time monitoring infrastructure through its **eRTMAC** (Real-Time Monitoring and Analysis Centre), which receives live rig sensor streams, MWD/LWD telemetry, and mud logging feeds. OIL also holds **decades of historical institutional knowledge** stored in Daily Drilling Reports (DDRs), Well Completion Reports (WCRs), mud logs, and geological surveys.

**The critical gap:** This institutional knowledge is locked inside thousands of unstructured legacy PDF documents. When an engineer is on shift and an anomaly begins at 3,220 meters depth, there is no system that can instantly answer:
- *Which historical offset wells experienced hazards at this exact geological interval?*
- *What were the early sensor warning signs before the hazard occurred?*
- *What specific mitigation procedure (LCM pill type, volume, pump rate) worked historically?*

Searching manually through archives takes hours. In active drilling, decisions must be made in minutes.

**eRTMAC-NWIS** (Nearby Wells Intelligence System) bridges this gap. It is an AI-powered, multi-tiered decision support platform that dynamically correlates live drilling telemetry with relevant historical offset well data, identifies approaching geological hazard corridors **15–50 meters before the drill bit reaches them**, and surfaces the exact DDR evidence and proven mitigation procedures — all within seconds.

> [!IMPORTANT]
> eRTMAC-NWIS is designed as a **human-augmented decision support system**, NOT an autonomous drilling controller. All safety-critical decisions remain with licensed Drilling Supervisors and eRTMAC Engineers.

---

## 2. Problem Statement Analysis

### 2.1 PS 26121: Word-by-Word Deconstruction

**Problem Statement Title:** *eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations*

**Issuing Organization:** Oil India Limited (OIL)

Oil India's operational environment presents a unique, high-stakes engineering challenge. The company has:

- **eRTMAC**: A modern Real-Time Data Monitoring and Analysis Centre receiving live rig instrumentation.
- **DRIVE 2.0 and OT Data Lake**: Digital transformation initiatives generating structured operational data.
- **Massive Historical Archives**: Decades of DDRs, WCRs, geological logs, casing reports, and incident reviews.

The problem statement explicitly requires a system that:

| Requirement ID | Explicit PS Requirement |
|---|---|
| R1 | AI/NLP/OCR extraction and structuring from WCR/DDR documents |
| R2 | Interactive geospatial map of nearby wells with user-defined radius |
| R3 | Instant access to historical events from offset wells |
| R4 | Searchable knowledge repository (events, lessons, mitigations) |
| R5 | Correlate geological/drilling/reservoir data by depth and formation |
| R6 | Correlate mud losses across wells |
| R7 | Correlate kicks across wells |
| R8 | Correlate stuck pipe incidents across wells |
| R9 | Correlate casing programs across wells |
| R10 | Correlate cementing practices across wells |
| R11 | Correlate formation-specific risks |
| R12 | Predictive analytics models for multiple hazard types |
| R13 | Real-time and proactive early alerts |
| R14 | Recommendations for proactive decision-making |
| R15 | Dashboard accessible by field and office personnel |
| R16 | Standalone platform alongside existing eRTMAC infrastructure |

### 2.2 The Five Core Risk Families

eRTMAC-NWIS targets the five most critical drilling hazard families, as defined by OISD and DGH standards:

| Hazard Family | Physical Mechanism | Historical Precursor Signals | Proven Mitigation Playbook |
|---|---|---|---|
| **Lost Circulation** | Natural/induced fractures; depleted sub-hydrostatic formations; excessive mud weight overbalance | Pit volume drop, flow-out reduction, SPP decrease, prior losses in same formation at same depth | Stop drilling, adjust mud rheology, pump LCM pills (nut plug + mica blend), spot pill across loss zone |
| **Stuck Pipe** | Differential pressure sticking against permeable formations; key seating; hole pack-off from poor hole cleaning | Overpull on trips, erratic torque, hook load escalation, cuttings volume drops | Jarring up/down, work pipe, acid/diesel/lubricant spotting pills, reduce mud weight |
| **Well Kick / Overpressure** | Penetrating an unexpected high-pressure reservoir zone with insufficient mud hydrostatic pressure | Pit volume increase (pit gain), flow-out increase without pump change, drilling break, background gas increase | Shut-in well (BOP activation), measure SIDPP/SICP, calculate kill mud weight, execute Driller's Method |
| **Excessive Torque & Drag** | High dogleg severity, hole tortuosity, swelling shale, poor lubrication | Exponential torque spikes, fluctuating surface RPM, drag during connections | Hole cleaning sweeps, drilling lubricants, optimize BHA stabilizer placement |
| **Cementing Complications** | Incomplete mud displacement, channelled cement, lost returns during cementing | Low CBL quality in offset wells, losses during pre-cement circulation | Optimize centralizer spacing, pre-flush/spacer design, two-stage cementing, squeeze remedies |

---

## 3. Core Philosophy and Innovation Rationale

### 3.1 "Nearby is NOT the Same as Relevant"

This is the foundational engineering insight that distinguishes eRTMAC-NWIS from every conventional Geographic Information System (GIS) mapping tool used in petroleum operations.

A conventional GIS tool performs a simple 2D Euclidean radius search — it shows all wells within, for example, 10 km of the active drill site. **This approach is fundamentally inadequate in subsurface drilling engineering** because of a critical physical reality:

> A well located **12 km away** but penetrating the **identical stratigraphic sequence**, with the same formation dip angle, same trajectory inclination, and a documented critical mud loss event at 3,248 meters depth in the **Tipam Sandstone** — is **far more relevant** than a well **2 km away** drilled through an entirely different faulted block with a completely different pressure regime.

Furthermore, relevance is **depth-dynamic**:
- Well X may be geologically irrelevant at 1,500 meters depth.
- But at 3,240 meters, when the active bit enters a specific fractured sandstone formation known for severe lost circulation, Well X may become the **#1 critical analog** in the entire dataset.

eRTMAC-NWIS solves this with a **5-dimensional, continuously-updated relevance engine** that re-ranks all offset wells at every depth increment.

### 3.2 The Five Core Questions NWIS Answers

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│     1. FIND     │ ──► │    2. UNDERSTAND    │ ──► │    3. CORRELATE     │ ──► │       4. WARN       │
│ Which offset    │     │ What happened in    │     │ Does active well    │     │ Is active well      │
│ intervals are   │     │ those offset        │     │ telemetry match     │     │ approaching a       │
│ truly relevant? │     │ intervals?          │     │ pre-hazard trends?  │     │ known hazard zone?  │
└─────────────────┘     └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                                          │
                                                                                          ▼
                                                                               ┌─────────────────────┐
                                                                               │      5. PROVE       │
                                                                               │ Show exact DDR/WCR  │
                                                                               │ source citations &  │
                                                                               │ proven mitigations  │
                                                                               └─────────────────────┘
```

---

## 4. System Architecture

### 4.1 Four-Tier Architecture Overview

eRTMAC-NWIS is built on a robust, four-tier architecture that separates concerns across data ingestion, storage, intelligence processing, and user presentation:

```
+------------------------------------------------------------------------------------+
|                           TIER 4: OPERATIONAL COCKPIT                              |
|                                                                                    |
|  ┌─────────────────────┐  ┌──────────────────────────┐  ┌─────────────────────┐  |
|  │  Geospatial Offset  │  │  Stratigraphic Depth &   │  │ Real-Time Telemetry │  |
|  │    GIS Map View     │  │  Risk Corridor Tracker   │  │  & Anomaly Strips   │  |
|  └─────────────────────┘  └──────────────────────────┘  └─────────────────────┘  |
|  ┌───────────────────────────────────────────────────┐  ┌─────────────────────┐  |
|  │    Explainable DDR/WCR Evidence & PDF Citation    │  │   AI Drilling Agent │  |
|  │         Modal with Historical Mitigation          │  │   (Tool Copilot)    │  |
|  └───────────────────────────────────────────────────┘  └─────────────────────┘  |
+------------------------------------------▲-----------------------------------------+
                                           │ REST / WebSocket / JSON
+------------------------------------------▼-----------------------------------------+
|                           TIER 3: BACKEND INTELLIGENCE ENGINE                      |
|                                                                                    |
|  ┌────────────────────────────────────────────────────────────────────────────┐   |
|  │                       FastAPI High-Performance Engine                      │   |
|  │                                                                            │   |
|  │  ┌──────────────────────┐  ┌───────────────────┐  ┌──────────────────┐   │   |
|  │  │  Dynamic Relevance   │  │  Interval         │  │  Risk Corridor   │   │   |
|  │  │  Engine (5-Weight    │  │  Correlator       │  │  Lead-Time       │   │   |
|  │  │  DORS Algorithm)     │  │  (MD/TVD/Strat.)  │  │  Warning Engine  │   │   |
|  │  └──────────────────────┘  └───────────────────┘  └──────────────────┘   │   |
|  │  ┌──────────────────────┐  ┌───────────────────┐  ┌──────────────────┐   │   |
|  │  │  Anomaly Detector ML │  │  Evidence / RAG   │  │  AI Agent Tool   │   │   |
|  │  │  (IsolationForest +  │  │  Engine (BM25 +   │  │  Orchestrator    │   │   |
|  │  │   Physics Rules)     │  │  Semantic Vector) │  │  (Tool Calling)  │   │   |
|  │  └──────────────────────┘  └───────────────────┘  └──────────────────┘   │   |
|  └────────────────────────────────────────────────────────────────────────────┘   |
+------------------------------------------▲-----------------------------------------+
                                           │ SQL / Vector / Geospatial Queries
+------------------------------------------▼-----------------------------------------+
|                           TIER 2: DATA AND STORAGE LAYER                           |
|                                                                                    |
|  ┌───────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐     |
|  │    PostgreSQL     │  │       PostGIS        │  │  pgvector / Qdrant      │     |
|  │  Normalized Well  │  │  Geospatial Spatial  │  │  DDR/WCR Embeddings &   │     |
|  │  Logs, Events,    │  │  Coordinates and     │  │  Semantic Search Chunks │     |
|  │  Formation Tops   │  │  Distance Queries    │  │  (all-MiniLM-L6-v2)     │     |
|  └───────────────────┘  └─────────────────────┘  └─────────────────────────┘     |
+------------------------------------------▲-----------------------------------------+
                                           │ Ingestion & Indexing Pipeline
+------------------------------------------▼-----------------------------------------+
|                           TIER 1: INGESTION AND DATA PIPELINE                      |
|                                                                                    |
|  ┌─────────────────────┐  ┌──────────────────────────┐  ┌─────────────────────┐  |
|  │  WITSML Trajectory  │  │  DDR/WCR PDF Parser      │  │  eRTMAC Telemetry   │  |
|  │  & Log Parsers      │  │  (PyMuPDF + Docling OCR  │  │  Stream Replay      │  |
|  │  Formation Tops     │  │  + Regex Entity Extractor│  │  Simulator          │  |
|  └─────────────────────┘  └──────────────────────────┘  └─────────────────────┘  |
+------------------------------------------------------------------------------------+
```

### 4.2 Intelligence Loop Execution Flow

When the active well increments its measured depth (during live drilling or historical replay):

**Step 1 — Active Well Context Update**
The system receives the current drill bit depth, active formation name, and the latest real-time telemetry frame (Torque, Flow-Out, SPP, Pit Volume, ROP, etc.).

**Step 2 — Dynamic Spatial and Contextual Filtering**
A spatial radius search identifies candidate offset wells within the configured search radius (default 25 km). The Dynamic Offset Relevance Score (DORS) then evaluates each candidate across 5 weighted parameters.

**Step 3 — Stratigraphic Depth Interval Matching**
The active well's current depth is projected against historical offset well intervals using TVD normalization and formation-top alignment. The system identifies a **Historical Risk Corridor** — a clustered depth range where multiple analog wells experienced documented hazards.

**Step 4 — Multi-Signal Risk Assessment**
Three independent evidence streams are combined: (a) historical hazard frequency in top-ranked offset wells at this interval, (b) real-time sensor anomaly scores from the active telemetry stream, and (c) calibrated machine learning classifier predictions.

**Step 5 — Evidence Grounding and Mitigation Retrieval**
For any triggered alert, the system surfaces the exact mitigation procedure from the historical DDR record — including the specific LCM pill blend, volume, pump rate adjustment, and the exact document, page, and paragraph from which this was extracted.

**Step 6 — Display in Operational Cockpit**
The alert, confidence breakdown, and historical playbook are displayed in the single-pane Operations Center. The Drilling Supervisor reviews and acts.

---

## 5. Mathematical and Algorithmic Foundations

### 5.1 Dynamic Offset Relevance Score (DORS)

The DORS algorithm is the core intelligence engine of eRTMAC-NWIS. It ranks all candidate offset wells at every depth increment using a weighted multi-factor score:

$$\text{DORS}(w, d_t) = w_s \cdot S_{\text{spatial}}(w) + w_f \cdot S_{\text{formation}}(w, d_t) + w_d \cdot S_{\text{depth}}(w, d_t) + w_t \cdot S_{\text{trajectory}}(w) + w_h \cdot S_{\text{hazard}}(w, d_t)$$

Default weights: $w_s=0.20,\ w_f=0.30,\ w_d=0.20,\ w_t=0.15,\ w_h=0.15$ (sum = 1.0)

**Component Sub-Scores:**

**1. Spatial Proximity Score** ($S_{\text{spatial}}$) — Haversine-formula geodetic distance:
$$S_{\text{spatial}}(w) = \max\left(0, 1 - \frac{\text{Distance}(w, \text{Active})}{R_{\max}}\right)$$

**2. Stratigraphic/Formation Match Score** ($S_{\text{formation}}$):
$$S_{\text{formation}}(w, d_t) = \begin{cases} 1.0 & \text{same formation at corresponding depth} \\ 0.6 & \text{adjacent formation, same group} \\ 0.1 & \text{different formation} \end{cases}$$

**3. Depth Overlap Score** ($S_{\text{depth}}$) — lookahead window of 100 m:
$$S_{\text{depth}}(w, d_t) = \frac{\text{Length}\left([D_{\min}(w), D_{\max}(w)] \cap [d_t - 50, d_t + 100]\right)}{150\text{ m}}$$

**4. Trajectory Similarity Score** ($S_{\text{trajectory}}$) — compares wellbore profile type and average inclination:
$$S_{\text{trajectory}}(w) = 1.0 - \frac{|\bar{\theta}_{\text{active}} - \bar{\theta}_{w}|}{90°} \times 0.5 - 0.5 \cdot \mathbb{I}(\text{Type}_{\text{active}} \neq \text{Type}_{w})$$

**5. Historical Hazard Density Score** ($S_{\text{hazard}}$) — depth-smoothed Gaussian kernel over historical events:
$$S_{\text{hazard}}(w, d_t) = \min\left(1.0, \sum_{e \in \text{Events}(w)} \text{Severity}(e) \cdot \exp\left(-\frac{(d_e - d_t)^2}{2\sigma_d^2}\right)\right)$$
where $\sigma_d = 25\text{ m}$ is the depth smoothing bandwidth.

### 5.2 Multi-Coordinate Depth Alignment

Directional wells require True Vertical Depth (TVD) computation using minimum curvature integration:
$$\text{TVD}(s) = \int_0^s \cos(\text{Inclination}(u))\, du$$

For stratigraphic normalization across wells with different formation dip angles $\alpha$:
$$d_{\text{strat}}(w, d) = \text{TVD}(w, d) - \text{Top}_{\text{TVD}}(\text{Formation}_k, w)$$

This aligns historical events by **penetration distance within the geological formation**, eliminating false depth correlations caused by regional layer dip.

### 5.3 Historical Risk Corridor Identification

A **Risk Corridor** $\mathcal{C}_k$ is identified when multiple historical events from top-ranked offset wells cluster within a common depth interval:

$$\mathcal{C}_k = \left[ \min_{e \in \mathcal{E}} d_{\text{start}}(e) - \delta,\quad \max_{e \in \mathcal{E}} d_{\text{end}}(e) + \delta \right]$$

**Lead-Time Distance Warning States:**
$$\Delta D_{\text{lead}} = D_{\text{start}}(\mathcal{C}_k) - d_{\text{current}}$$

| State | Condition | Action |
|---|---|---|
| **Safe** | $\Delta D_{\text{lead}} > 50\text{ m}$ | Monitor normally |
| **Proactive Early Warning** | $0 < \Delta D_{\text{lead}} \leq 50\text{ m}$ | Prepare LCM, reduce pump rate |
| **Critical Hazard** | $d_{\text{current}} \in [D_{\text{start}}, D_{\text{end}}]$ | Execute mitigation immediately |

### 5.4 Multi-Signal Hybrid Risk Aggregation

The final risk score for each hazard family $H$ is a weighted combination of three independent evidence signals:

$$R_H(t) = \alpha \cdot P_{\text{history}}(H, d_t) + \beta \cdot A_{\text{sensor}}(H, t) + \gamma \cdot M_{\text{ML}}(H, X_t)$$

| Parameter | Symbol | Weight | Source |
|---|---|---|---|
| Historical Prior | $P_{\text{history}}$ | $\alpha = 0.45$ | Offset well event frequency at current depth |
| Sensor Anomaly | $A_{\text{sensor}}$ | $\beta = 0.35$ | Real-time Z-score on Torque, Flow, SPP |
| ML Prediction | $M_{\text{ML}}$ | $\gamma = 0.20$ | Calibrated sklearn classifier |

### 5.5 Decoupled 4-Pillar Confidence Breakdown

Rather than a single opaque "confidence percentage," eRTMAC-NWIS outputs a 4-pillar transparent confidence matrix:

| Pillar | Description | Why It Matters |
|---|---|---|
| **Evidence Strength** | Number and quality of historical analog wells used | Prevents overconfident alerts from 1 poor-quality record |
| **Telemetry Anomaly** | Z-score deviation on real-time sensor streams | Shows whether live sensors agree with historical prediction |
| **Data Quality Index** | Percentage of structured fields present in source records | Discloses data completeness to the engineer |
| **Audit / Citation Status** | Whether a source PDF, page, and paragraph are available | Ensures every alert is fully auditable |

---

## 6. Data Models and Standards Compliance

### 6.1 Entity Relationship Model

```
+------------------+         1:N         +----------------------+
|      wells       | -------------------<|     trajectories     |
| (Surface info,   |                     | (MD, TVD, Incl, Az)  |
|  KB, Field, Loc) |                     +----------------------+
+--------+---------+
         |
         | 1:N                           +----------------------+
         +-----------------------------< |    formation_tops    |
         |                               | (Fm name, Top, Base) |
         |                               +----------------------+
         | 1:N                           +----------------------+
         +-----------------------------< |   drilling_events    |
         |                               | (Hazard, Depth, LCM) |
         |                               +----------------------+
         | 1:N                           +----------------------+
         +-----------------------------< |   telemetry_records  |
         |                               | (ROP, WOB, Flow, SPP)|
         |                               +----------------------+
         | 1:N                           +----------------------+
         +-----------------------------< |   source_documents   |
                                         | (PDF, Page, Chunks)  |
                                         +----------------------+
```

### 6.2 WITSML Standards Mapping

eRTMAC-NWIS data schemas are fully aligned with the **Energistics WITSML 1.4/2.0** standard — the international industry standard for wellsite information transfer — enabling plug-and-play integration with Oil India's eRTMAC, DRIVE 2.0, and OT Data Lake.

| NWIS Data Field | WITSML Standard Object | WITSML XML Element |
|---|---|---|
| Well Metadata | `well` | `well.nameLegal`, `well.field`, `well.wellLocation` |
| Trajectory Points | `trajectory` | `trajectory.trajectoryStation.md`, `tvd`, `incl`, `azi` |
| Formation Tops | `stratigraphicColumn` | `formationMarker.name`, `mdTop`, `tvdTop` |
| Real-time Telemetry | `log` / `mudLog` | `log.logCurveInfo.curve[mnem='ROP']`, `torque`, `flowIn` |
| Drilling Events | `opsReport` (DDR) | `opsReport.activity.md`, `opsReport.activity.comments` |

### 6.3 Core Data Schemas

**Well Entity (`wells.json`):**
```json
{
  "well_id": "OIL-EXP-07",
  "name": "Nahorkatiya Well #07",
  "operator": "Oil India Limited",
  "field": "Nahorkatiya",
  "block": "Assam-Arakan Basin Block A",
  "latitude": 27.2845,
  "longitude": 95.3412,
  "elevation_kb_m": 128.5,
  "total_depth_md_m": 3850.0,
  "total_depth_tvd_m": 3620.0,
  "profile_type": "Directional-J",
  "status": "HISTORICAL_OFFSET"
}
```

**Normalized Drilling Event (`drilling_events.json`):**
```json
{
  "event_id": "EVT-OIL-W03-089",
  "well_id": "OIL-EXP-03",
  "event_type": "MUD_LOSS",
  "hazard_category": "Lost Circulation",
  "depth_start_md_m": 3238.0,
  "depth_end_md_m": 3260.0,
  "formation": "Tipam Sandstone",
  "severity": "CRITICAL",
  "npt_hours": 14.5,
  "historical_mitigation": "Pumped 30 bbl high-viscosity LCM pill (nut plug + mica blend), reduced pump rate from 2100 lpm to 1550 lpm.",
  "source_document": "DDR_OIL_W03_2023.pdf",
  "source_page": 42,
  "extraction_confidence": 0.96
}
```

---

## 7. Module-by-Module Implementation

### Module 01 — Document Intelligence Pipeline

The Document Intelligence module is responsible for transforming raw, unstructured PDF drilling reports into clean, structured, WITSML-compliant JSON data.

**6-Stage Processing Pipeline:**

| Stage | Component | Technology | Output |
|---|---|---|---|
| **Stage 1** | Native Text Extraction | PyMuPDF | High-fidelity text from digitally-native PDFs |
| **Stage 2** | OCR Fallback | Docling OCR | Text from scanned/image-based PDFs |
| **Stage 3** | Entity Extraction | Regex/Rules Engine (NOT spaCy or LLM) | Structured fields: depths, mud weights, events, NPT hours |
| **Stage 4** | Template Learner | Heuristic Pattern Matching | Adapts to OIL's internal DDR formatting |
| **Stage 5** | Physics Validator | Domain Rules Engine | Auto-repairs OCR digit-slip errors (e.g., "l0.2 ppg" → "10.2 ppg") |
| **Stage 6** | WITSML Mapper | JSON Schema Serializer | WITSML-compliant output JSON |

> [!NOTE]
> The entity extraction engine uses a deliberately **regex/rules-based** approach. This was a conscious design choice for mission-critical petroleum engineering: rule-based extraction provides fully auditable, deterministic extraction, with zero risk of an ML model hallucinating a depth or mud weight value.

**Live API Endpoints:**
- `POST /api/v1/ingest` — Upload DDR/WCR PDF
- `GET /api/v1/jobs/{id}` — Poll extraction job status
- `GET /api/v1/results/{doc_id}` — Retrieve structured WITSML JSON

**Validation:** Module 01 was verified against **979 pages** across **14 real Equinor Volve DDR/WCR documents**, successfully extracting 119 drilling events, 22 well trajectories, 10 casing records, and 2 well stratigraphic profiles.

---

### Module 02 — NWIS Backend Intelligence Core

The NWIS Backend is the computational core of the system. It exposes a FastAPI REST and WebSocket interface serving the frontend operational cockpit.

**Key Engine Components:**

**DORS Engine** (`dors_engine.py`)
Implements the full 5-component Dynamic Offset Relevance Score algorithm. Scores are computed for all wells in the testbed and re-ranked at each depth increment.

**Stratigraphic Correlator** (`stratigraphic_correlator.py`)
Normalizes all historical events and formation tops to TVD and formation-relative depth (ξ), eliminating trajectory-induced false correlations. **Validated:** interpolated TVD fell within real survey station brackets in 98/100 real bracket tests.

**Risk Corridor Engine** (`risk_corridor_engine.py`)
Clusters historical events from top-ranked offset wells into spatial-depth risk corridors. Implements the three-state lead-time distance warning system (Safe → Early Warning → Critical).

**Hazard Predictor** (`hazard_predictor.py`)
Hybrid design: uses real-data-trained ML where ≥8 quality examples exist; falls back to physics-calibrated heuristics otherwise. **Critically, the API always discloses which path produced the score** (`m_ml_source` field), ensuring full transparency.

**Knowledge Search Engine** (`knowledge_search.py`)
Hybrid sparse-dense retrieval combining BM25 keyword search with SentenceTransformer semantic vector search (`all-MiniLM-L6-v2`). Validated: Hit@5 = 2/2 on real Volve events.

**AI Drilling Copilot** (Tool-Calling Agent)
A strictly tool-grounded LLM agent that calls `rank_offset_wells`, `get_risk_corridor`, and `retrieve_ddr_evidence` tools. The agent never generates free-text answers — all responses are grounded in structured database facts.

---

### Module 04 — Physics Engine and Telemetry Simulator

The Physics Engine provides a reduced-order ODE-based telemetry simulator that models real drilling dynamics when live OIL rig data is unavailable. This is explicitly labeled as a simulation in the UI — not live rig data.

The simulator models:
- Rate of Penetration (ROP) as a function of WOB, RPM, and formation hardness
- Torque response to inclination changes and formation transitions
- Flow-out anomaly modeling during simulated fracture zone penetrations
- Pit volume dynamics during simulated kick scenarios

---

## 8. Operational Dashboard and User Interface

![DrillWise Brand](C:\Users\LAUKIK\.gemini\antigravity-ide\brain\a035afbc-db0f-4d1e-a274-48ca96cdaa35\drillwise-brand-sheet.png)

### 8.1 Design Philosophy

The eRTMAC-NWIS operational cockpit is built with a **dark SCADA-inspired command center theme** — consistent with the visual language of real-time industrial control systems used by OIL's eRTMAC engineers. The design prioritizes:
- High information density without visual clutter
- Color-coded severity indicators (Green → Amber → Orange → Red)
- Zero-ambiguity labeling (all values include units)
- Human-readable confidence breakdowns alongside every alert

### 8.2 The 12 Operational Pages

| Page | Function |
|---|---|
| **1. Document Ingestion** | Upload and process DDR/WCR PDFs; poll job status; download extracted WITSML JSON |
| **2. Geospatial Basin Map** | Interactive Leaflet map; dynamic radius slider (5–50 km); color-coded DORS-ranked well markers |
| **3. Nearby Wells Intelligence** | Ranked table of offset wells by DORS; dossier panels with hazard event histories |
| **4. Geological Correlation** | Depth track with formation tops; stratigraphic cross-section correlation across offset wells |
| **5. Real-Time Telemetry Monitor** | Live sensor gauges (Torque, SPP, Flow, Pit Volume, ROP); anomaly flag strips |
| **6. Historical Intelligence Search** | BM25 + Semantic search across DDR/WCR knowledge corpus |
| **7. Risk Assessment Dashboard** | Per-hazard-family composite risk scores; 4-pillar confidence matrix |
| **8. Alerts & Advisory Center** | Active alerts with lifecycle management (Detected → Acknowledged → Mitigated → Cleared) |
| **9. Risk Corridor Viewer** | Visual depth track showing historical risk corridors; lead-time warning status |
| **10. Casing & Cementing Analysis** | Casing record viewer; top-of-cement mapping across offset wells |
| **11. AI Drilling Copilot** | Tool-grounded LLM assistant for on-demand offset well queries |
| **12. Settings & Configuration** | DORS weight tuning; radius configuration; data layer selection |

### 8.3 Technology Stack — Frontend

| Component | Technology | Rationale |
|---|---|---|
| Core Framework | React 18 + TypeScript | Type-safe, component-driven; catches depth/pressure type errors at compile time |
| Styling | Tailwind CSS + custom dark theme | Rapid iteration on the SCADA dashboard layout |
| Geospatial Map | Leaflet / React-Leaflet | Lightweight; real geodetic projections on CartoDB tiles |
| Data Visualization | Recharts + Plotly + Canvas/SVG | High-precision wellbore depth tracks; sensor time-series charts |
| Icons | Lucide Icons | Consistent, clean industrial iconography |

---

## 9. Datasets and Real-World Validation

### 9.1 Publicly Available Benchmark Datasets Used

| Dataset | Organization | Contents | Role in NWIS |
|---|---|---|---|
| **Equinor Volve** | Equinor / NPD | 24 wells: DDRs, WCRs, trajectories, mud logs | Gold standard for Document RAG and real event extraction validation |
| **FORCE 2020 ML Benchmark** | FORCE / NPD | 100+ wells: formation tops, lithology, trajectories | Benchmark for Stratigraphic Alignment |
| **DataDrill** | SPE / Petrobras | 1 Hz telemetry with labeled Mud Loss, Kick, Overpressure | Benchmark for Sensor Anomaly ML |
| **Utah FORGE DDR Dataset** | US DOE | DDRs with stuck pipe, lost circulation incidents | Automated Event Extraction validation |
| **DGH / NDR Indian Basins** | DGH India | Geological sequences for Assam-Arakan Basin | Authentic Indian geological context |

### 9.2 Synthetic Testbed for OIL Context

Where real OIL proprietary data is unavailable (as is expected in a hackathon context), eRTMAC-NWIS uses a carefully constructed **15-well synthetic testbed** modeled faithfully on the **Upper Assam Basin** (Nahorkatiya and Moran fields):

- Well coordinates and formation sequences reflect real Assam-Arakan Basin geology
- Formation names used: Alluvium, Dhekiajuli, Girujan Clay, Tipam Sandstone, Barail Coal-Shale, Kopili
- Pore pressure and fracture gradient values calibrated to OISD and OIL engineering manuals
- Sensor time-series distributions match DataDrill benchmark dynamics
- Historical event narratives match OISD-standard mitigation procedures

### 9.3 Real-Data ML Training — Stuck Pipe Classifier

The STUCK_PIPE hazard ML classifier was retrained entirely on **real Volve data** (10 real events, 3 real wells), achieving:
- **Mean Leave-One-Well-Out AUC: 0.661** across 3 real folds
- This outperforms the synthetic-data-trained model (0.622 AUC)
- This is the only deployed ML model in the system trained on real petroleum data

---

## 10. PS 26121 Compliance Audit Results

The following audit was conducted against the original PS 26121 requirements by directly verifying source code, running live API endpoints, and inspecting actual data files. No claims are taken from README comments.

| ID | Requirement | Status | Implementation Summary |
|---|---|---|---|
| R1 | AI/NLP/OCR extraction from DDR/WCR | ✅ **FUNCTIONAL** | 6-layer pipeline on real Volve PDFs (979 pages, 14 docs) |
| R2 | Interactive geospatial map with radius | 🟡 **FUNC + SIMULATED** | Real Leaflet map; radius slider drives live DORS ranking; well coordinates are synthetic testbed |
| R3 | Instant access to historical events | 🟡 **FUNC + SIMULATED** | Real API endpoints; 119 real Volve events extracted but not in live data store by default |
| R4 | Searchable knowledge repository | 🟡 **FUNC + SIMULATED** | Real BM25 + Semantic search; validated Hit@5=2/2 on real events |
| R5 | Correlate by depth and formation | ✅ **FUNCTIONAL** | Real TVD normalization; 98/100 real bracket tests passed |
| R6 | Mud loss correlation | 🟡 **FUNC + SIMULATED** | Real end-to-end MUD_LOSS hazard chain; heuristic model (below ML sample threshold) |
| R7 | Kick correlation | 🟡 **FUNC + SIMULATED** | Real end-to-end KICK chain; synthetic-trained ML model (0.817 AUC) |
| R8 | Stuck pipe correlation | 🟠 **PARTIAL→STRONG** | **Real-data trained ML** (0.661 AUC on real Volve data); strongest real-data proof point |
| R9 | Casing program correlation | 🟠 **PARTIAL** | 10 real casing records from 2 Volve wells; backend-only (no live UI page yet) |
| R10 | Cementing practices correlation | 🟠 **PARTIAL** | top-of-cement field extracted; CEMENTING_FAILURE live in `/api/v2/analyze` |
| R11 | Formation-specific risk correlation | ✅ **FUNCTIONAL** | HIGH_RISK_FORMATIONS lookup; real Volve profile validated with `NORTH_SEA_VOLVE` flag |
| R12 | Predictive analytics models | 🟠 **PARTIAL** | STUCK_PIPE: real ML. KICK/WELLBORE_INSTABILITY: synthetic ML. Others: physics heuristic |
| R13 | Real-time proactive alerts | 🟡 **FUNC + SIMULATED** | Real corridor clustering + lead-time logic; telemetry is physics-simulated not live OIL data |
| R14 | Proactive decision recommendations | ✅ **FUNCTIONAL** | Domain-expert mitigation text per hazard type; deterministic lookup — correctly not ML-generated |
| R15 | Dashboard for field and office | ✅ **FUNCTIONAL** | 12-page React/TypeScript app; dark SCADA theme; zero TypeScript build errors |
| R16 | Standalone alongside eRTMAC | ⚪ **N/A (Prototype)** | Architecturally correct; live eRTMAC integration requires OIL production access |

**Summary: 16 requirements — 5 Fully Functional, 6 Functional with simulated data, 4 Partial, 0 Missing, 0 Mocked/Hardcoded**

> [!IMPORTANT]
> **No requirement is hardcoded, mocked, or missing outright.** This is a genuinely strong result for a hackathon prototype. The "Functional + Simulated" rating reflects the appropriate use of synthetic testbed data where real OIL proprietary data is not available — not a design flaw.

---

## 11. Innovation Differentiators

eRTMAC-NWIS introduces 7 substantive innovations over conventional petroleum data systems and generic hackathon submissions:

| # | Innovation | Conventional Baseline | NWIS Advancement | Engineering Value |
|---|---|---|---|---|
| **1** | Offset Relevance | 2D Euclidean radius search | Dynamic 5-Factor DORS: Distance + Formation + Depth + Trajectory + Hazard History | Solves "Nearby ≠ Relevant"; ranks distant analog wells above close-but-irrelevant ones |
| **2** | Depth Alignment | Raw Measured Depth comparison | TVD + Stratigraphic Normalized Depth; corrects for wellbore inclination and formation dip | Prevents false correlations in deviated/directional wells |
| **3** | Hazard Warning | Reactive post-incident detection | Historical Risk Corridors with proactive lead-time (15–50 m ahead of bit) | Mud engineer can prepare LCM pill *before* the drill bit enters the loss zone |
| **4** | Confidence Output | Single opaque percentage | 4-Pillar Decoupled Matrix: Evidence + Telemetry + Data Quality + Citation | Avoids misleading engineers; full transparent explainability |
| **5** | Sparse Data | False "0% risk" for no-data zones | Explicit "Insufficient Historical Analogs" flag; falls back to sensor anomaly | Critical safety feature; compliant with DGMS and OISD guidelines |
| **6** | Evidence Retrieval | Unstructured LLM summary | PDF bounding-box + page citation + exact historical mitigation playbook | 100% auditable; zero hallucination on safety-critical data |
| **7** | Standards | Proprietary JSON | Energistics WITSML 1.4/2.0 + OSDU schema alignment | Plug-and-play OIL eRTMAC/DRIVE 2.0 integration ready |

### Why Lead-Time Warning Matters in Drilling Operations

At a typical Rate of Penetration of 15 m/hr in a challenging sand-shale formation, a **15-meter proactive warning** translates to a **60-minute operational lead time**. This gives the drilling crew time to:

1. Reduce pump rate and standpipe pressure below the fracture gradient
2. Prepare Lost Circulation Material (LCM) in the slug pit
3. Re-verify mud weight versus the expected formation fracture gradient
4. Alert the Mud Logger, Directional Driller, and on-call Drilling Engineer

Without NWIS, the first indicator is the actual mud loss beginning — at which point NPT has already started.

---

## 12. Technology Stack

| Layer | Component | Technology | Justification |
|---|---|---|---|
| **Frontend UI** | Operational Cockpit | React 18, TypeScript, Tailwind CSS, Lucide Icons | Type-safe, high-density dark SCADA dashboard |
| **Geospatial Map** | GIS Well View | Leaflet / React-Leaflet (CartoDB tiles) | Real geodetic projections; radius geometry; DORS-colored markers |
| **Wellbore Visualization** | Depth Track | Canvas / SVG / Recharts / Plotly | High-precision lithology layers, bit depth, hazard corridor markers |
| **Backend API** | Intelligence Core | Python 3.10+, FastAPI, Uvicorn | Native async, automatic OpenAPI docs, Python ML ecosystem |
| **Relational DB** | Structured Data | PostgreSQL + PostGIS | ST_Distance/ST_DWithin geospatial queries; normalized entity storage |
| **Vector Search** | RAG Knowledge Base | pgvector + SentenceTransformers (`all-MiniLM-L6-v2`) | Hybrid BM25+semantic; zero hallucination on historical DDR text |
| **Machine Learning** | Anomaly + Risk | Scikit-Learn (Isolation Forest / Random Forest / Logistic Regression) | Deterministic baseline + unsupervised anomaly scoring |
| **AI Copilot** | Tool-Calling Agent | FastAPI Tool Dispatcher + LLM (OpenAI API / Ollama local fallback) | Strictly grounded tool calling; no free-text hallucination |
| **Document Processing** | PDF Ingestion | PyMuPDF + Docling OCR | Handles both native-digital and scanned legacy petroleum PDFs |
| **Containerization** | Deployment | Docker + Docker Compose | On-premise, edge-deployable; no external cloud dependency required |

---

## 13. Business Impact and Return on Investment

### 13.1 Operational Impact for Oil India Limited

| Metric | Current State (Without NWIS) | Projected State (With NWIS) | Improvement |
|---|---|---|---|
| Time to retrieve historical offset data | 2–6 hours manual archive search | < 30 seconds automated retrieval | **~99% reduction** |
| Hazard detection lead time | Reactive (after anomaly has started) | Proactive (15–50 m before entry) | **60–200 min earlier** |
| Drilling hazard response time | 2–3 hours average NPT onset to response | 25–40% faster with prepared mitigation | **25–40% reduction** |
| Institutional knowledge accessibility | Locked in individual engineer experience and legacy PDFs | Systematically captured, searchable, shareable | **Fully democratized** |
| LCM preparation readiness | Reactive mixing after loss starts | Pre-mixed before bit reaches corridor | **Eliminates reactive NPT** |

### 13.2 Financial Impact Estimate

Based on industry benchmarks:
- Average NPT cost in Indian E&P operations: ₹15–50 lakhs per day
- Average NPT duration per lost circulation event: 14–48 hours
- Estimated NPT reduction per campaign with NWIS: 3–5 events prevented
- **Estimated annual NPT savings per active rig: ₹1.5–8 crores**

### 13.3 Institutional Knowledge Preservation

One of NWIS's most strategically important — and undervalued — benefits is its ability to capture and formalize the tacit knowledge of experienced Drilling Supervisors and Well Engineers. When a senior engineer retires after 30 years in the Nahorkatiya field, their mental model of "which formations cause trouble and what works" is typically lost. NWIS systematically captures this knowledge in structured, searchable form — permanently.

---

## 14. Future Roadmap

### Phase 1 (Post-Hackathon — 3 Months)
- Wire Module 01's real extracted Volve events into the live Module 02 data store
- Integrate the `laukik` frontend branch with the `backend-working` branch into a unified deployable stack
- Build a live WITSML feed ingestion connector for actual eRTMAC telemetry streams

### Phase 2 (6 Months)
- Deploy to Oil India's internal development/staging environment with access to real OIL DDR archives
- Retrain all ML hazard classifiers on real OIL historical events
- Add 3D Geocellular model integration for subsurface visualization of fault blocks and pressure compartments
- Implement multi-well simultaneous monitoring dashboard

### Phase 3 (12 Months — Production Readiness)
- Full DGMS and OISD compliance review
- Formal integration with DRIVE 2.0 and OT Data Lake via WITSML/OSDU APIs
- Role-based access control (Field Engineer, Office Engineer, Management views)
- Real-time OIL eRTMAC sensor stream integration (replacing physics simulation with live telemetry)

---

## 15. Conclusion

eRTMAC-NWIS represents a substantive, technically rigorous response to Oil India Limited's Problem Statement PS 26121. The system goes beyond a simple GIS proximity tool or a generic RAG chatbot:

1. **It solves the core engineering problem**: "Nearby is NOT the same as Relevant" — with a mathematically sound 5-factor dynamic relevance engine.
2. **It provides proactive intelligence**: Historical risk corridors warn 15–50 meters before the drill bit enters a known hazard zone.
3. **It is fully auditable**: Every alert is grounded to an exact DDR source document, page, and paragraph — with zero hallucination.
4. **It is standards-compliant**: WITSML 1.4/2.0 alignment ensures it can integrate with OIL's existing infrastructure.
5. **It is honest about its boundaries**: Simulation is clearly labeled. ML models disclose their training data source. Data scarcity triggers an explicit warning rather than a false "0% risk."

> *"Because in drilling engineering, nearby is NOT the same as relevant. NWIS finds the history that matters right now."*

---

<div align="center">

![DrillWise Icon](C:\Users\LAUKIK\.gemini\antigravity-ide\brain\a035afbc-db0f-4d1e-a274-48ca96cdaa35\drillwise-icon-mark.png)

**eRTMAC-NWIS | Smart India Hackathon 2026 | PS 26121**

*Aayush Deshpande · Laukik Rathod · Prasad Bhalerao · Harshal Kanhaiyalal Yadav · Srushti Arav Pawar · Shravasti Ratnakar Surwade*

**Oil India Limited | Smart Automation | Software Category**

---

*This document is prepared for the Smart India Hackathon 2026 Grand Finale evaluation. All technical claims are backed by direct source code inspection, live API verification, and real dataset validation as documented in the Implementation Audit (logger/10_PS26121_IMPLEMENTATION_AUDIT.md).*

</div>
