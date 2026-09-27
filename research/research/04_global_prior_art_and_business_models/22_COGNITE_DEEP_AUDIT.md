# SIH 26121 — Cognite: Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** Cognite AS (Headquartered in Oslo, Norway; US Hub in Houston, Texas)
- **Market Position:** Global pioneer in industrial DataOps, contextualization, and industrial Generative AI.
- **Flagship Digital Platform:** **Cognite Data Fusion (CDF)**.
- **Primary Solution Audited:** **Know Your Well** & **Cognite Drilling & Wells Contextualization**.

---

## 2. Deep Dive: Cognite "Know Your Well"

Cognite's **Know Your Well** is one of the most prominent industrial demonstrations of using modern AI, Knowledge Graphs, and RAG to solve the institutional memory crisis in drilling:

```
[COGNITE DATA FUSION: "KNOW YOUR WELL" PIPELINE]
Fragmented Subsurface & Drilling Archives (27,000+ Wells, 2.6M Documents)
       │
       ▼
Cognite Data Fusion (CDF) Automated Contextualization Engine
       ├── Entity Matching (Connecting well names across formats)
       ├── Document OCR & Semantic Parsing (DDRs, EOWRs, Schematics)
       ├── Time-Series & Depth-Series Synchronization (WITSML, LAS)
       └── Industrial Knowledge Graph (Linking Well → Formation → Event → Document)
       │
       ▼
Cognite "Know Your Well" Interface & AI Copilot
       ├── Natural Language Semantic Search over Drilling History
       ├── Instant Discovery of Lessons Learned & Recurring NPT Causes
       ├── Cross-Well Parametric Filtering (Depth, Formation, Casing)
       └── Reduction of Reliance on Individual Senior Engineer Memory
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Directly addresses "institutional amnesia" where historical drilling experiences are siloed across disconnected PDF folders, databases, and retiring engineers' memories.
- **The Volve Benchmark Demonstration:** Cognite publicly demonstrated Know Your Well using the open Equinor **Volve field dataset**, ingesting **20 wells and approximately 1.5 million data points**, including WITSML time-series, DDRs, and End-of-Well Reports.
- **Enterprise-Scale Implementation:** Cognite documented an industrial deployment contextualizing over **27,000 wells and 2.6 million documents**, linking well trajectories, casing seats, and historical drilling hazards into a queryable knowledge graph.
- **Destruction of Simplistic Novelty Claims:** The phrase *"creating institutional memory for drilling operations"* is an established commercial marketing and engineering concept popularized by Cognite years ago.

`[VERIFIED: Cognite Hub Drilling & Wells Portal: https://hub.cognite.com/drilling-wells-443/welcome-to-the-drilling-wells-group-on-cognite-hub-4996; Cognite OSDU Case Study: https://www.cognite.com/en/extend-your-osdu-data-platform-into-valuable-data-products]`

---

## 3. Cognite Data Fusion Architecture & OSDU Integration
- **Industrial Knowledge Graph:** Rather than dumping text into a generic vector database, CDF constructs an explicit property graph connecting industrial assets:
  - $\text{Wellbore} \xrightarrow{\text{penetrates}} \text{Formation} \xrightarrow{\text{contains}} \text{Hazard Interval} \xrightarrow{\text{documented in}} \text{DDR Page}$.
- **OSDU Data Platform Alliance:** Cognite is a primary commercial partner of the Open Group OSDU Forum. CDF acts as an accelerated contextualization layer on top of OSDU-standard data models.

---

## 4. Reverse-Engineering Forensic Questionnaire: Cognite Stack

| Technical & Operational Question | Cognite Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it solve the institutional memory problem in drilling?** | **YES** | Primary design objective of "Know Your Well". |
| **Does it ingest both WITSML time-series and PDF DDRs?** | **YES** | Demonstrated across the 20-well Volve benchmark. |
| **Does it use Knowledge Graphs and Semantic Search?** | **YES** | Employs an industrial property graph linked to vector embeddings. |
| **Does it predict real-time drilling dysfunctions (stick-slip, torque)?** | **PARTIAL** | Stronger on contextual search, historical analytics, and static risk registers than on high-frequency (10-Hz) downhole vibration physics. |
| **Does it display live "Historical Risk Corridors" ahead of the bit?** | **PARTIAL** | Shows offset events by depth, but dynamic live corridor projection during active drilling is custom-configured. |
| **Is it deployed in India?** | **YES** | Formally deployed at **Cairn Oil & Gas (Vedanta)** via the SLB-Cognite alliance. |
| **Is it deployed at Oil India Limited?** | **NO** | Zero documented deployment inside OIL. |
| **Can an operator procure it cheaply for a single field?** | **NO** | High-cost enterprise SaaS platform requiring enterprise data lake onboarding. |

---

## 5. Conclusions for SIH 26121

1. **Cognite is the Architectural Reference for Institutional Memory:** The conceptual workflow of *PDF → OCR → Entity Extraction → Graph/Relational Linking → Natural Language Search* in PS 26121 mirrors the Cognite CDF blueprint.
2. **The High-Cost Enterprise Dilemma:** Cognite Data Fusion is built for massive multinational energy corporations with budgets for enterprise-wide data transformation. It is not an agile, standalone drilling decision-support tool.
3. **The NWIS Value Proposition:** NWIS adopts the architectural lessons of Cognite (knowledge structuring, hybrid retrieval, domain entities), but packages them into a lightweight, sovereign, standalone microservice platform designed specifically to bolt onto Oil India's eRTMAC system.
