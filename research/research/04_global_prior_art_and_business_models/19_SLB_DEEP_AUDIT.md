# SIH 26121 — SLB (Schlumberger): Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** SLB (formerly Schlumberger Limited)
- **Market Position:** The world's largest oilfield services and energy technology company.
- **Flagship Digital Platform:** **DELFI Cognitive E&P Environment** (Cloud-native platform built on Google Cloud / Azure).
- **Primary Solutions Audited:**
  1. **Tela Offset Wells Insights** (Agentic AI for offset well document intelligence)
  2. **DrillPlan** (Digital well construction planning solution)
  3. **DrillOps** (On-rig and remote drilling operations automation suite)
  4. **Performance Insights** (Multi-well operational benchmarking)

---

## 2. Deep Dive: Tela Offset Wells Insights

**Tela Offset Wells Insights** is arguably the single closest commercial equivalent to the core vision outlined in PS 26121.

```
[SLB TELA OFFSET WELLS INSIGHTS ARCHITECTURE]
Unstructured Documents (PDFs, Scanned Reports, DDRs, EOWRs, Images)
       │
       ▼
Multimodal Parsing & Agentic AI Ingestion Pipeline
       │
       ├── Entity & Event Extraction (NPT events, loss zones, casing seats)
       ├── Natural Language Semantic Indexing
       └── Geographical & Stratigraphic Tagging
       │
       ▼
Interactive Offset Wells Intelligence Dashboard
       ├── 1. Geospatial Risk Occurrence Map (Visualizing historical incidents)
       ├── 2. NPT Distribution Analytics (By risk family and drilling phase)
       ├── 3. Conversational AI Assistant (Natural-language querying of offset records)
       └── 4. Lessons-Learned Register (Automated surfacing of historical mitigations)
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Eliminates the hundreds of hours engineers spend manually reading historical well reports and PDFs to discover offset drilling hazards.
- **Target Users:** Well Planners, Asset Drilling Engineers, Operations Geologists.
- **Data Consumed:** Historical Daily Drilling Reports (DDRs), End-of-Well Reports (EOWRs), Mud Logging Reports, incident logs, casing tallies, and unstructured scanned PDFs.
- **NLP / Document Intelligence:** Employs domain-tuned Large Language Models (LLMs) and multi-agent workflows to synthesize text, extract numerical parameters from tables, and generate structured summaries.
- **Geospatial Mapping:** Maps risk occurrences geographically, allowing users to select an area of interest and view historical complication heatmaps.
- **Conversational Search:** Allows engineers to ask: *"What were the primary causes of stuck pipe in the Cretaceous sandstone in block 7?"* and returns cited answers.

`[VERIFIED: SLB Official Product Portal: https://www.slb.com/products-and-services/delivering-digital-at-scale/artificial-intelligence-solutions/innovation-factori/tailored-solutions/tela-agentic-ai-assistant-for-offset-wells-insights]`

---

## 3. Deep Dive: SLB DrillPlan (Digital Well Construction)

While Tela focuses on unstructured historical reports, **DrillPlan** automates structured well engineering planning:
- **Offset Well Database Search:** Scans structured historical databases to identify relevant offset wells based on user-defined criteria:
  - Distance / geographic proximity.
  - Hole size and casing program compatibility.
  - Well trajectory type (vertical, S-curve, horizontal).
  - Bit types and directional steering BHA (RSS vs. mud motor).
  - Spud date and operating contractor vintage.
- **Probabilistic Time-Depth (T-D) Curves:** Automatically generates P10, P50, and P90 time-depth projections by learning from historical drilling performance across the selected offset set.
- **Automated Validation:** Validates hydraulic limits, casing burst/collapse ratings, and kick tolerances against regional offset pressure gradients.

`[VERIFIED: SLB DrillPlan Product Sheets & Technical Disclosures]`

---

## 4. Deep Dive: SLB DrillOps (Real-Time Execution & Automation)

DrillOps handles the active rig execution phase:
- **Live Ingestion:** Consumes 1-Hz to 10-Hz high-frequency sensor streams from rig surface instrumentation and downhole MWD/LWD telemetry.
- **Automation Modes:** Features both Advisory Mode (delivering recommendations to driller) and Control Mode (interfacing directly with rig cyber-chairs to execute automated drilling sequences).
- **Real-Time Dysfunction Mitigation:** Identifies stick-slip and bit vibration in real time and automatically trims WOB and RPM setpoints.

---

## 5. Reverse-Engineering Forensic Questionnaire: SLB Stack

| Technical & Operational Question | SLB Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it rank offset wells beyond simple distance?** | **YES** | DrillPlan uses hole size, trajectory, vintage, and BHA parameters. |
| **Does it ingest unstructured DDRs/WCRs and PDFs?** | **YES** | Tela Offset Wells Insights is explicitly built for multi-modal report ingestion. |
| **Does it use OCR on legacy scanned documents?** | **YES** | Tela processes scanned PDF reports and graphical image logs. |
| **Does it use LLMs / RAG for drilling queries?** | **YES** | Tela uses agentic AI copilots for natural language Q&A. |
| **Does it predict stuck pipe and kicks in real time?** | **YES** | DrillOps and Performance Insights run real-time anomaly detection. |
| **Does it display dynamic "Historical Risk Corridors" ahead of live bit?** | **PARTIAL** | Shows risk maps and historical NPT distributions, but interval-ahead-of-bit corridor projection is split across DELFI modules. |
| **Does it show clickable bounding-box evidence to original PDF pages?** | **UNVERIFIED** | Summarizes lessons learned and provides document citations; specific UI bounding-box overlay is not publicly demonstrated. |
| **Can an operator run it completely offline on-premise without cloud?** | **NO** | DELFI and Tela are cloud-native SaaS solutions tightly coupled to hyperscalers (GCP/Azure). |
| **Does it require multi-million dollar DELFI ecosystem lock-in?** | **YES** | Requires enterprise subscription to the proprietary SLB DELFI environment. |

---

## 6. Indian Market Penetration & OIL Deployment Audit

- **SLB Indian Corporate Presence:** Massive presence in India with corporate offices in Mumbai, regional operational bases in Barmer, Dehradun, and Duliajan (Assam), and global tech centers in Pune. `[VERIFIED]`
- **Customer Contracts in India:** Extensive service contracts with ONGC, Cairn Oil & Gas, and Oil India Limited for directional drilling, wireline logging, testing, and Petrel software licensing. `[VERIFIED]`
- **Tela Offset Wells Deployment in India:**
  - *Status:* `[NOT DOCUMENTED]`.
  - While SLB actively markets DELFI in India, there is zero public evidence that Oil India Limited or ONGC has procured or deployed the Tela Offset Wells Insights agentic platform.

---

## 7. Conclusions for SIH 26121

1. **Avoid Claiming Conceptual Monopoly:** Saying *"Nobody in the world has built an AI offset-well platform"* is definitively disproven by SLB Tela.
2. **The High-Cost SaaS Barrier:** SLB Tela is an expensive, closed-source cloud SaaS solution requiring data migration to DELFI. For an Indian PSU like OIL managing sensitive sovereign data in Assam, an indigenous, standalone platform operating on-premise alongside eRTMAC is strategically compelling.
3. **The Target Differentiator:** Focus on tight, lightweight integration with eRTMAC live streams, instant interval-ahead-of-the-bit risk corridor visualization, and zero-hallucination original document page proof.
