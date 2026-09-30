# PS 121 — Competitor Repository Audit & Technical Intelligence Study

**SIH 26121 — eRTMAC-NWIS: AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations**

---

## Executive Overview

This study represents a repository-first code audit and competitive intelligence investigation conducted for **PS 121 (SIH 26121)**. All candidate repositories were downloaded, inspected at the source-code level, filtered to remove empty scaffolds and non-domain prototypes, and synthesized into an actionable architectural roadmap.

A total of **12 high-value competitor and domain benchmark codebases** have been retained in `research/competitors/` for direct technical inspiration.

---

## Study Directory Structure

```
research/PS121_COMPETITOR_REPOSITORY_STUDY/
│
├── README.md                              # This master index and executive synthesis
│
├── repositories/                          # Individual deep-dive repository audits
│   ├── dhanwanth_ertmac_nwis.md           # dhanwanth (5 XGBoost models, Isolation Forest, Decision Engine)
│   ├── physics0070_nwis.md                # Physics0070 (PostgreSQL + Alembic, Replay, EngineerAction)
│   ├── vidhiii1711_drillx.md              # vidhiii1711 (Team DrillX fullstack, 20+ telemetry params, Vercel)
│   ├── petrolq.md                         # PetrolQ (PostGIS, MapLibre GL offline, AHP RAG, Eaton PPFG)
│   ├── drillmind.md                       # DrillMind (Multi-agent RTOC, RRF BM25+Vector, PyTorch LSTM)
│   ├── pallavi_ertmac_nwis.md             # pallavi-eRTMAC-NWIS (Qwen2.5-VL 2-pass VLM, OpenCV, Qdrant)
│   ├── tech_nitin_wellwise.md             # tech-nitin (Three.js 3D subsurface layer explorer + CSS2D callouts)
│   ├── sih_2026_planns.md                 # NWIS-Sentinel (FastAPI + Flask + ChromaDB + FastDTW)
│   ├── rudrachauhan_ertmac_nwis.md        # rudrachauhan (FastAPI + MongoDB modular routers)
│   ├── invo_coder19_drill_iq.md           # invo-coder19 (React 19, TanStack Router, Offset Relevance Score)
│   ├── suryanshkota07_aroh.md             # suryanshkota07 (Deterministic 5-factor analog matching, risk ahead)
│   ├── ddr_utah_forge.md                  # DDR_UTAH_FORGE (Deep PDF Layout, OCR Quality, Phase Causality)
│   └── volve_drilling.md                  # Volve Dataset & SPWLA (Standard WITSML XML & LAS benchmark)
│
├── PS121_COMPETITOR_MATRIX.md             # Detailed capability comparison matrix
├── PS121_GAP_ANALYSIS.md                  # File-and-line code gaps and open domain challenges
├── PS121_TECH_STACK_ANALYSIS.md           # Comparative stack analysis (DB, GIS, Vector, ML, Ingestion)
├── PS121_USP_ANALYSIS.md                  # Core USPs with code evidence & defensibility analysis
├── PS121_ARCHITECTURE_OPPORTUNITIES.md    # End-to-end intelligence chain & white space discovery
└── SOURCES.md                             # Curated repository URLs, clone paths, and commit timestamps
```

---

## Key Technical Inspirations Identified from Competitor Code

Since our core implementation has not been written yet, the audited repositories provide concrete architectural building blocks:

1. **Machine Learning & Decision Engine** (from `dhanwanth-dh/eRTMAC--NWIS`):
   - 5-hazard XGBoost classifier suite (`xgb_mud_loss`, `xgb_stuck_pipe`, `xgb_overpressure`, `xgb_torque_spike`, `xgb_cementing_issue`).
   - Concrete 4-step operational action protocols in recommendations.
2. **Relational Data Modeling & Audit Trail** (from `Physics0070/nwis` & `vidhiii1711/eRTMAC-NWIS`):
   - Production PostgreSQL schema with Alembic migrations and the `EngineerAction` feedback model (`accepted`, `rejected`, `investigating`, `resolved`).
   - Comprehensive multi-channel telemetry schema (20+ parameters).
3. **3D Subsurface Visualization** (from `tech-nitin/wellwise`):
   - Three.js 3D subsurface geological layer rendering with OrbitControls and CSS2D callout annotations anchored to wellbore depths.
4. **Geospatial & Drilling Physics** (from `PetrolQ`):
   - PostGIS spatial radius queries (`ST_DWithin`), offline MapLibre raster tiles, and Eaton PPFG pore pressure calculations.
5. **Multi-Agent RAG & Hybrid Retrieval** (from `DrillMind` & `suryanshkota07-AROH`):
   - Specialist agent orchestration (`DrillingAgent`, `HistoricalAgent`, `SafetyAgent`) and Reciprocal Rank Fusion (RRF $k=60$) combining BM25 ($w=0.3$) and dense vector ($w=0.7$).
6. **Multi-Modal Document Extraction** (from `DDR_UTAH_FORGE` & `pallavi-a11y/eRTMAC-NWIS`):
   - PyMuPDF layout analysis preserving bounding boxes, OpenCV morphological table border detection, and anti-hallucination score thresholds.

---

## Open Technical White Space for PS 121

Across all audited repositories, three critical subsurface challenges remain completely unaddressed:
- **Stratigraphic Normalization ($\xi(d)$)**: All competitors correlate on raw Measured Depth (MD), creating discrepancies in dipping strata ($3^\circ-15^\circ$). We will design dimensionless formation coordinate scaling $\xi(d) = \frac{d_{\text{tvdss}} - Z_{\text{top}}}{Z_{\text{base}} - Z_{\text{top}}}$.
- **Fault-Block Structural Gating**: All competitors compute proximity via 2D surface distance without fault isolation. We will implement PostGIS fault polygon intersection checks (`ST_Crosses`) with structural barrier weighting ($\beta_{\text{fault}}$).
- **1-Click Interactive PDF Provenance**: Competitors output plain text citations. We will link normalized bounding-box coordinates to an interactive PDF canvas viewer highlighting exact source tables/sentences.
