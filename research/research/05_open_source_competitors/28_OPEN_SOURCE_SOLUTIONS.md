# SIH 26121 — Open-Source Solutions & Public Energy AI Ecosystem

## 1. Executive Summary
This document investigates the open-source software ecosystem in drilling engineering, energy AI, and subsurface data processing. It audits publicly accessible codebases, community tools, and benchmarks released by energy companies (e.g. Equinor) and academic consortia, establishing the state of open prior art relevant to PS 26121.

---

## 2. Landscape of Open-Source Energy Software

Unlike consumer tech, upstream oil and gas software has historically been proprietary and closely guarded. Over the past decade, however, open data releases (such as Equinor's Volve field disclosure) and open-source initiatives have created a foundational tier of community software:

```
[OPEN-SOURCE ENERGY SOFTWARE ECOSYSTEM]
├── Subsurface Data Parsers & Standards
│   ├── Welly / Lasio (Python LAS log parsing & curve manipulation)
│   ├── Stripr / Petropy (Petrophysical curve calculations & lithology)
│   └── OSDU Open-Source Data Platform (SDKs, core schemas, ingestion workers)
│
├── Drilling Visualization & Dashboard Frameworks
│   ├── Equinor Webviz (Modular Dash/Plotly dashboard framework for subsurface data)
│   └── WellborePath (Python 3D trajectory calculation & minimum curvature)
│
└── AI & Document Intelligence Pipelines
    ├── DrillMind (Volve real-time anomaly detection & DDR agentic Q&A)
    ├── DrillSense (SFT & RAG for daily drilling reports on FastAPI/React)
    ├── DDR_UTAH_FORGE (Geothermal DDR OCR and NPT extraction pipeline)
    └── DrillScribe (DDR structuring pipeline for OIL eRTMAC Project DRIVE)
```

---

## 3. Detailed Audit of Core Open-Source Repositories

### 1. DrillMind (GitHub: ArokyaMatthew/DrillMind)
- **Dataset:** Equinor Volve real operational field dataset.
- **Architectural Components:**
  - Streams real Volve 1-Hz sensor data (hookload, torque, SPP, ROP).
  - Automated rig-state classification (drilling, tripping, reaming, connection).
  - Real-time anomaly detection flagging deviations before incident escalation.
  - Hybrid retrieval (BM25 keyword + dense vector search) over Volve DDR PDFs.
  - Multi-agent conversational system answering plain-English drilling questions.
- **Classification:** `[PROTOTYPE / OPEN-SOURCE RESEARCH]`.
- **Relevance to NWIS:** Validates the feasibility of running real-time telemetry anomaly detection in parallel with a DDR document retrieval engine.

### 2. DrillSense (GitHub: poetabdullah/DrillSense)
- **Architecture:** React + Tailwind CSS frontend paired with a FastAPI backend deployed on GCP.
- **Technical Capabilities:**
  - Ingests daily drilling reports (DDRs) and generates automated summaries.
  - Combines Supervised Fine-Tuning (SFT) and Retrieval-Augmented Generation (RAG) for domain-specific Q&A.
  - Generates contextual operational anomaly alerts.
- **Classification:** `[PROTOTYPE / DEMO]`.
- **Relevance to NWIS:** Demonstrates that modern web frameworks (React/FastAPI) provide sufficient throughput for domain RAG and drilling report summarization.

### 3. DDR_UTAH_FORGE (GitHub: djimrastephane/DDR_UTAH_FORGE)
- **Dataset:** Public Utah FORGE geothermal well archive (Well 16A(78)-32).
- **Architectural Pipeline:**
  - Ingests scanned DDR PDFs from geothermal drilling.
  - Executes OCR and layout parsing to extract structured drilling facts.
  - Categorizes Non-Productive Time (NPT) events.
  - Implements hybrid BM25 + dense retrieval with a lightweight dashboard.
  - Explicitly includes engineering disclaimers regarding automated OCR errors.
- **Classification:** `[PROTOTYPE / REPRODUCIBLE PIPELINE]`.
- **Relevance to NWIS:** Direct proof-of-concept for extracting structured NPT facts from scanned historical daily reports.

### 4. DrillScribe (GitHub Public Ecosystem)
- **Context:** Specifically targets **Oil India's eRTMAC Drilling Command Centre** under **Project DRIVE**.
- **Scope:** Ingests and structures daily drilling reports (DDRs) for automated archiving and summary generation.
- **Classification:** `[PROTOTYPE / DEMO]`.
- **Relevance to NWIS:** Proves that Indian hackathon and academic teams are actively exploring DDR automation for Oil India Limited.

---

## 4. Strengths and Systematic Flaws in Existing Open-Source Projects

Auditing these public codebases reveals critical patterns:

| Open-Source Project | What It Successfully Demonstrates | Systematic Weaknesses & Omissions |
| :--- | :--- | :--- |
| **DrillMind** | Excellent rig-state classification and Volve telemetry integration. | Lacks dynamic offset relevance ranking; does not correlate active well depth with offset geological intervals; no ahead-of-the-bit risk corridor. |
| **DrillSense** | Clean UI and fast DDR summarization using fine-tuned LLMs. | Operates as a generic "chat with PDF" tool; lacks geospatial map, subsurface geomechanics, and real-time telemetry synchronization. |
| **DDR_UTAH_FORGE** | Robust OCR extraction of structured NPT events from messy PDFs. | Single-well archive only; lacks cross-well correlation, multi-well map, and predictive risk scoring ahead of the bit. |

---

## 5. Strategic Conclusions for NWIS
1. **Open-Source Validates Key Building Blocks:** Codebases like `DrillMind` and `DDR_UTAH_FORGE` prove that Python libraries (PyMuPDF, LangChain/LlamaIndex, FAISS, scikit-learn, FastAPI) can reliably implement the low-level parsing and retrieval tasks required by PS 26121.
2. **The Open-Source Gap:** None of these projects synthesize the complete, closed-loop workflow demanded by OIL: **Map + Dynamic Offset Ranking + Stratigraphic Interval Correlation + 5 Risk Models + Ahead-of-the-Bit Risk Corridor + Document Evidence**.
3. **NWIS Architecture Role:** NWIS synthesizes these isolated open-source concepts into an integrated, production-grade decision-support platform tailored to Oil India Limited's operational realities.
