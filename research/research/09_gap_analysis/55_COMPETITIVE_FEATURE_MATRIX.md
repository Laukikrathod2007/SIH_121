# SIH 26121 — Comprehensive Competitive Feature Matrix: 40 Capabilities Across 15 Systems

## 1. Executive Summary
This document establishes the master competitive benchmark for SIH Problem Statement 26121. It evaluates 15 platforms—spanning global oilfield service giants (SLB, Halliburton, Baker Hughes, Cognite, Weatherford, NOV, Corva, Peloton), Indian domestic deployments (ONGC, Cairn, Nergyflux, Parallel Minds), open-source repositories (DrillMind, DrillSense), and the proposed **eRTMAC-NWIS**—across **40 granular technical capabilities**.

---

## 2. Platform Comparison Scope

1. **SLB:** Tela Offset Wells Insights & DrillPlan
2. **HAL:** Halliburton OpenWells & Digital Well Program (DWP)
3. **BHI:** Baker Hughes JewelSuite & Drilling Hazard Prevention (DHP)
4. **COG:** Cognite Data Fusion & Know Your Well
5. **WFT:** Weatherford Centro Optimization Platform
6. **NOV:** NOV KAIZEN Intelligent Drilling Optimizer
7. **CRV:** Corva Drilling Real-Time Hazards
8. **PEL:** Peloton WellView Master Reporting
9. **ONG:** ONGC RTDOC + GenAI WIS + DBA
10. **CRN:** Cairn Vedanta Project Nirmaan / PTC
11. **NRG:** Nergyflux DrillSense™
12. **PRL:** Parallel Minds WellSynth AI
13. **DMND:** DrillMind (Open-Source GitHub)
14. **DSNS:** DrillSense (Open-Source GitHub)
15. **NWIS:** eRTMAC-NWIS (Proposed Solution for OIL)

---

## 3. The 40-Feature Master Evaluation Matrix

Legend:
- `●` = Fully Native / Production-Hardened
- `◐` = Partial / Requires Custom Configuration or Manual Add-on
- `○` = Not Supported / Absent

### Cluster 1: Spatial & Dynamic Offset Selection
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 1 | PostGIS Geospatial Radius Query | ● | ● | ● | ● | ● | ◐ | ● | ● | ● | ● | ◐ | ◐ | ● | ◐ | **●** |
| 2 | Dynamic Depth-Dependent Radius | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 3 | Trajectory Curvature Similarity | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 4 | Multi-Criteria Dynamic Relevance ($\Omega$)| ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 5 | Automated Offset Rank Re-sorting | ◐ | ○ | ◐ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |

### Cluster 2: Stratigraphic & Depth Alignment
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 6 | Measured Depth to TVD Conversion | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | **●** |
| 7 | TVDSS Subsea Datum Normalization | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ◐ | ◐ | ◐ | ◐ | **●** |
| 8 | Dynamic Time Warping (DTW) Logs | ● | ◐ | ● | ● | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 9 | Stratigraphic Proportional Ratio ($\xi$)| ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 10| Ahead-of-the-Bit Risk Corridor | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ● | ○ | ◐ | ◐ | ◐ | ○ | ○ | ○ | **●** |

### Cluster 3: Unstructured Document Intelligence & Historical RAG
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 11| Scanned DDR / WCR OCR Extraction | ● | ● | ◐ | ● | ◐ | ○ | ◐ | ◐ | ● | ● | ◐ | ● | ◐ | ◐ | **●** |
| 12| Table & Matrix Structure Parsing | ● | ● | ◐ | ● | ◐ | ○ | ◐ | ◐ | ● | ● | ◐ | ● | ○ | ○ | **●** |
| 13| WITSML Historical Log Parsing | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ◐ | ◐ | **●** |
| 14| Hybrid Retrieval (BM25 + Dense) | ◐ | ◐ | ◐ | ● | ○ | ○ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ◐ | ○ | **●** |
| 15| Direct PDF Bounding Box Evidence Proof| ◐| ◐ | ○ | ● | ○ | ○ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ○ | ○ | **●** |
| 16| Zero-Hallucination Retrieval Guard| ◐ | ◐ | ◐ | ● | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |

### Cluster 4: Real-Time Telemetry & Multi-Hazard Prediction
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 17| 1-Hz WITS / WITSML Streaming | ● | ● | ● | ● | ● | ● | ● | ◐ | ● | ● | ● | ● | ● | ● | **●** |
| 18| Automated Rig State Machine (FSM)| ● | ● | ● | ● | ● | ● | ● | ◐ | ● | ● | ● | ● | ◐ | ◐ | **●** |
| 19| Real-Time Mechanical Specific Energy|● | ● | ● | ● | ● | ● | ● | ◐ | ● | ● | ● | ● | ● | ● | **●** |
| 20| Mud Loss Early Warning ($> 15$ min)| ◐ | ◐ | ● | ◐ | ● | ◐ | ● | ○ | ◐ | ◐ | ◐ | ○ | ○ | ○ | **●** |
| 21| Differential Sticking Risk Predict| ● | ● | ● | ◐ | ● | ◐ | ● | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | **●** |
| 22| Mechanical Pack-Off Detection | ● | ● | ● | ◐ | ● | ● | ● | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | **●** |
| 23| Pore Pressure & Kick Early Influx| ● | ● | ● | ◐ | ● | ◐ | ● | ○ | ● | ◐ | ◐ | ○ | ○ | ○ | **●** |
| 24| Stick-Slip & Torsional FFT Spectral|●| ● | ● | ◐ | ● | ● | ● | ○ | ◐ | ◐ | ◐ | ○ | ○ | ○ | **●** |
| 25| Cementing Standoff / Slurry Channel|●| ● | ● | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 26| Decoupled Independent Hazard Models| ◐| ◐| ● | ◐ | ● | ◐ | ● | ○ | ◐ | ◐ | ◐ | ○ | ○ | ○ | **●** |

### Cluster 5: Explainability, Uncertainty & Decision Support
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 27| Real-Time TreeSHAP Attribution | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 28| Conformal Prediction Intervals | ○ | ○ | ◐ | ◐ | ○ | ○ | ◐ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | **●** |
| 29| Aleatoric vs. Epistemic Separation| ◐| ◐ | ◐ | ◐ | ○ | ○ | ◐ | ○ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 30| Historical Mitigation Recommendations|●|●| ● | ● | ● | ◐ | ● | ◐ | ● | ● | ◐ | ◐ | ○ | ○ | **●** |
| 31| Casing Burst Safety Cross-Check | ● | ● | ● | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | ○ | ○ | **●** |
| 32| Single Human-in-the-Loop Sign-Off| ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ○ | ○ | **●** |

### Cluster 6: Deployment, Sovereignty & System Economics
| # | Feature / Capability | SLB | HAL | BHI | COG | WFT | NOV | CRV | PEL | ONG | CRN | NRG | PRL | DMND| DSNS| NWIS |
| :-| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 33| Air-Gapped Local Rig Execution | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ◐ | ● | ◐ | ● | ◐ | ● | ● | **●** |
| 34| Zero Public Cloud SaaS Lock-in | ○ | ○ | ○ | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ● | ◐ | ● | ● | **●** |
| 35| DGH NDR Indian Data Sovereignty | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ● | ● | ● | ○ | ○ | **●** |
| 36| Complementary Standalone eRTMAC | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ○ | **●** |
| 37| Open Postgres / PostGIS Storage | ○ | ○ | ○ | ◐ | ○ | ○ | ○ | ○ | ◐ | ◐ | ◐ | ◐ | ● | ● | **●** |
| 38| Zero Per-Well Proprietary License| ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ○ | ◐ | ◐ | ● | ● | **●** |
| 39| Sub-Second Edge Alarm Latency | ● | ● | ● | ◐ | ● | ● | ● | ○ | ● | ● | ● | ◐ | ◐ | ◐ | **●** |
| 40| One-Click PDF Bounding Box Viewer| ◐| ◐| ○ | ● | ○ | ○ | ○ | ○ | ◐ | ◐ | ○ | ◐ | ○ | ○ | **●** |

---

## 4. Key Comparative Insights

1. **Global Service Cartels (SLB, HAL, BHI):** Exceptionally strong in physics simulations and proprietary engineering suites, but severely burdened by **cloud lock-in (DELFI, Landmark Cloud), multi-crore annual license fees, and closed proprietary databases**.
2. **Indian Operator In-House Solutions (ONGC RTDOC, Cairn):** Highly practical and field-validated, but developed as custom point solutions tightly coupled to their internal IT ecosystems rather than modular products.
3. **Open-Source Repositories (DrillMind, DrillSense):** Excellent proof-of-concept scripts, but lack real-time WITSML streaming, stratigraphic normalization, explainability (SHAP/Conformal), and production-grade UI ergonomics.
4. **The eRTMAC-NWIS Advantage:** Combines the **algorithmic rigor** of commercial solutions with **open data standards (PostGIS/WITSML)**, **strict air-gapped sovereignty**, **zero-hallucination document page proof**, and **seamless integration alongside OIL's Duliajan eRTMAC facility**.
