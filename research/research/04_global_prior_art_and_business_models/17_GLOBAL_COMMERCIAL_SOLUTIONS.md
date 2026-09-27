# SIH 26121 — Global Commercial Solutions: Architectural Audit Overview

## 1. Executive Summary
This document provides a comparative landscape analysis of global commercial drilling software, digital well engineering platforms, and oilfield AI systems. It establishes how the global oilfield service giants (SLB, Halliburton, Baker Hughes, Weatherford), independent digital platforms (Cognite, Corva, Peloton), and rig equipment manufacturers (NOV, Nabors) approach the problem of offset well intelligence and real-time decision support.

---

## 2. Macro-Classification of Global Commercial Solutions

Commercial solutions in the drilling intelligence space divide into three distinct generational paradigms:

```
[GENERATION 1: RELATIONAL DATA ARCHIVES (1990s–2010s)]
├── Peloton WellView, Halliburton OpenWells
└── Focus: Structured reporting, morning tour sheets, historical NPT categorization, regulatory compliance.

[GENERATION 2: INTEGRATED PLANNING & REAL-TIME ANALYTICS (2010s–2020s)]
├── SLB DrillPlan / DrillOps, Baker Hughes JewelSuite & WellLink, Weatherford Centro, Corva
└── Focus: Automated well planning, offset selection by proximity/hole size, real-time WITSML surveillance, hydraulic alarms.

[GENERATION 3: COGNITIVE AGENTS & DOCUMENT CONTEXTUALIZATION (2023–Present)]
├── SLB Tela Offset Wells Insights, Cognite Know Your Well, NOV KAIZEN
└── Focus: Multi-modal AI over unstructured PDFs, LLM-driven query copilots, automated lessons-learned extraction, predictive risk mitigation.
```

---

## 3. High-Level Commercial Product Mapping

| Vendor | Primary Product(s) | Primary Domain Focus | Offset Analysis Mechanism | Document Intelligence (NLP/OCR) | Real-Time Telemetry Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SLB** | **Tela Offset Wells Insights** | Offset AI & Risk Mapping | Multi-criteria offset search & clustering | `[YES]` Multi-modal agentic AI for PDFs, DDRs, images | Native connection to DELFI / DrillOps |
| **SLB** | **DrillPlan / DrillOps** | Digital Well Construction | Proximity, trajectory, bit & hole size filtering | `[PARTIAL]` Structured data emphasis; NPT trends | `[YES]` Real-time closed-loop surveillance |
| **Baker Hughes**| **JewelSuite Offset Well Analyzer** | Offset Engineering Analysis | Automated multi-parameter well/section ranking | `[PARTIAL]` Automated data mining across offset runs | Linked via WellLink Real-Time platform |
| **Baker Hughes**| **Drilling Hazard Prevention (DHP)** | Real-Time Risk & Hazards | Dynamic offset hazard mapping & risk register | `[PARTIAL]` Ingests offset hazard logs and geomechanics | `[YES]` Live sensor hazard prediction |
| **Cognite** | **Know Your Well (CDF)** | Industrial Data Contextualization | Knowledge-graph contextualization across wells | `[YES]` Hybrid RAG over WITSML, DDRs, EOWRs | `[YES]` Real-time industrial IoT streaming |
| **Halliburton** | **OpenWells / Digital Well Program**| Well Lifecycle & Planning | Section-by-section offset limit analysis | `[PARTIAL]` InformatiQ AI acquisition integration | Linked via iVRO Real-Time Operations |
| **Weatherford** | **Centro Platform** | Real-Time Well Optimization | Multi-well benchmarking & offset comparison | `[LOW]` Focuses on sensor time-series & telemetry | `[YES]` High-frequency smart alarms |
| **NOV** | **KAIZEN / NOVOS** | Real-Time Optimization & Control | Current vs. offset performance comparison | `[LOW]` Telemetry-centric; physics + ML setpoints | `[YES]` Closed-loop rig automation control |
| **Peloton** | **WellView** | Complete Lifecycle Well Master | Historical query & offset benchmarking | `[PARTIAL]` Structured form entry & master data | Integrated via Peloton Platform APIs |
| **Corva** | **Corva Drilling Platform** | Real-Time Rig Apps & Analytics | Offset curve overlay and geomechanics mapping | `[LOW]` Primarily structured 1-Hz sensor streams | `[YES]` Industry-leading cloud real-time UI |

---

## 4. Reverse-Engineering the Global Product Concepts

Auditing these global commercial offerings reveals five critical industry insights:

1. **"Offset Well Selection" is a Solved Commercial Feature:**
   - Both SLB DrillPlan and Baker Hughes JewelSuite have supported multi-parameter offset well filtering (by hole size, casing program, trajectory type, and spud date) for years.
   - Claiming that *"filtering offset wells by criteria other than distance"* is a novel invention is **false**.
2. **"Institutional Memory via AI" is Actively Commercialized:**
   - SLB Tela and Cognite Know Your Well explicitly market solutions that ingest PDFs, DDRs, and EOWRs to extract lessons learned and answer natural-language drilling questions.
   - Proposing a generic "chatbot over drilling PDFs" is heavily commoditized and non-differentiated.
3. **The Industrial Reality of High License Costs:**
   - Enterprise suites (DELFI, DecisionSpace, Cognite Data Fusion) require multi-million-dollar annual software licensing and vendor lock-in. National oil companies like OIL frequently seek sovereign, tailored platforms that integrate directly into existing assets without recurring international subscription overhead.
4. **The Critical Remaining Integration Gap:**
   - Most commercial giants split capabilities across separate software packages: one software for planning (DrillPlan / JewelSuite), another for daily reporting (OpenWells), another for live surveillance (DrillOps / WellLink), and a separate standalone AI tool for document search (Tela / Cognite).
   - **The true opportunity for NWIS is unified contextual integration:** An agile, lightweight platform running directly alongside eRTMAC that takes the *live drilling state*, dynamically retrieves the *corresponding historical offset interval*, projects an *ahead-of-the-bit risk corridor*, and shows *clickable source report evidence* in a single screen.
