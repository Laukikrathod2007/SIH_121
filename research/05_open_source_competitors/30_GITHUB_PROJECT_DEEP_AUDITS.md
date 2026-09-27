# SIH 26121 — GitHub Project Deep Audits: Codebase Forensic Inspection

## 1. Executive Summary
This document conducts a deep forensic inspection of four prominent public GitHub repositories operating in the drilling AI, DDR document intelligence, and real-time telemetry domain: **DrillMind**, **DrillSense**, **DDR_UTAH_FORGE**, and **DrillScribe**. It inspects their data pipelines, database schemas, prompt engineering, ML models, and operational limitations to identify reusable architectural patterns and critical pitfalls to avoid.

---

## 2. Deep Audit 1: DrillMind (ArokyaMatthew/DrillMind)

### Repository Metadata:
- **Repository URL:** [https://github.com/ArokyaMatthew/DrillMind](https://github.com/ArokyaMatthew/DrillMind)
- **Tagline:** *"Watches live drilling data, flags trouble before it becomes an incident, and answers plain-English questions about the well — built entirely on Equinor's real Volve field data."*
- **Primary Data:** Equinor Volve Field 1-Hz time-series telemetry and Volve DDR PDF records.

### Codebase & Architectural Inspection:
- **Telemetry Pipeline:** Python-based streaming worker simulating real-time telemetry playback from Volve CSV files.
- **Rig-State Engine:** Implements a rule-based and tree-based rig-state classifier distinguishing between:
  - *Rotary Drilling:* Pumps ON, Top Drive RPM > 30, WOB > 3 tonnes, ROP > 0.
  - *Slide Drilling:* Pumps ON, Top Drive RPM = 0, WOB > 3 tonnes.
  - *Tripping (POOH/RIH):* Pumps OFF, Top Drive RPM = 0, Hook Load moving.
  - *Connection:* Pumps OFF, Bit off bottom, stationary string.
- **Anomaly Detection:** Rolling Z-score and statistical variance thresholds on Standpipe Pressure (SPP) and Torque to detect washouts and pack-offs.
- **Document RAG Pipeline:** LangChain-based vector retrieval using OpenAI embeddings combined with BM25 keyword matching over extracted DDR text.
- **Multi-Agent Orchestrator:** Uses LangChain agent routing to dispatch user queries to either the live sensor SQL database or the DDR document vector store.

### Key Limitations Discovered in Code:
1. *Fixed-Radius Assumption:* Does not perform spatial or stratigraphic offset relevance ranking.
2. *Disconnected Depth Indexing:* The document search does not synchronize dynamically with the active bit depth in the streaming simulation.
3. *Single-Field Constraint:* Hardcoded to the Volve North Sea offshore well schema; cannot ingest onshore Indian multilateral well records without refactoring.

---

## 3. Deep Audit 2: DrillSense (poetabdullah/DrillSense)

### Repository Metadata:
- **Repository URL:** [https://github.com/poetabdullah/DrillSense](https://github.com/poetabdullah/DrillSense)
- **Tagline:** *"AI-powered visual intelligence system for drilling operations. Combines SFT & RAG to summarize drilling reports, answer domain-specific queries, and generate anomaly alerts."*
- **Stack:** React + Tailwind CSS (Frontend), FastAPI (Backend), Google Cloud Platform (Vertex AI).

### Codebase & Architectural Inspection:
- **Frontend Architecture:** Modern, responsive React dashboard utilizing Tailwind CSS for card layouts and status indicators. Includes clean multi-tab navigation between Reports, Query Engine, and Alerts.
- **Backend & ML Pipeline:** FastAPI endpoints serving asynchronous inference requests. Uses a fine-tuned LLM (Supervised Fine-Tuning - SFT) trained on drilling operations terminology paired with a RAG vector retriever.
- **Report Summarization:** Extracts daily operational summaries, footage drilled, mud weight checks, and bit hours into standardized JSON payloads.

### Key Limitations Discovered in Code:
1. *No Geospatial Component:* Contains zero map visualization or spatial distance calculation.
2. *No Time-Series Sensor Stream:* Operates exclusively on daily text reports; completely blind to real-time high-frequency (1-Hz) telemetry.
3. *No Cross-Well Interval Correlation:* Summarizes reports in isolation; cannot correlate hazards across multiple wells by formation top or depth.

---

## 4. Deep Audit 3: DDR_UTAH_FORGE (djimrastephane/DDR_UTAH_FORGE)

### Repository Metadata:
- **Repository URL:** [https://github.com/djimrastephane/DDR_UTAH_FORGE](https://github.com/djimrastephane/DDR_UTAH_FORGE)
- **Tagline:** *"DDR intelligence pipeline for the public Utah FORGE geothermal well archive (FORGE 16A(78)-32)."*
- **Primary Data:** Scanned Daily Drilling Reports from the Utah Frontier Observatory for Research in Geothermal Energy (FORGE).

### Codebase & Architectural Inspection:
- **Document Ingestion Pipeline:**
  - Converts multi-page scanned PDF reports into high-resolution PNG images.
  - Applies Tesseract OCR and layout analysis to parse tabular operational headers and free-form 24-hour narrative logs.
- **Information Structuring:** Uses regex and heuristic rules to extract daily footage, bit runs, BHA component lists, and NPT event descriptions.
- **Hybrid Retrieval System:** Implements rank-fusion combining BM25 keyword matching with dense sentence-transformers embeddings.
- **Engineering Quality Safeguards:** The author explicitly logs confidence flags on extracted numerical fields, noting that OCR character misreads (e.g. reading `1.35 SG` as `1.85 SG`) can create severe engineering errors.

### Key Limitations Discovered in Code:
1. *Single Well Focus:* Engineered specifically for the FORGE 16A(78)-32 well; lacks multi-well cross-correlation algorithms.
2. *No Predictive Risk Models:* Extracts past events, but does not train machine learning models to predict upcoming risks in an active well.
3. *Static Dashboard:* Basic data exploration interface without live streaming simulation capabilities.

---

## 5. Deep Audit 4: DrillScribe (Targeting OIL Project DRIVE)

### Repository Metadata & Scope:
- **Ecosystem Focus:** Specifically created by developers targeting **Oil India's eRTMAC Drilling Command Centre** under **Project DRIVE**.
- **Core Function:** Ingests daily drilling reports (DDRs) and well tour sheets from OIL operational areas, structuring operations into standardized relational records and morning executive summaries.
- **Relevance:** Proves that extracting structured facts from Oil India's specific DDR formats is a recognized, high-priority operational requirement within the hackathon community.

---

## 6. Code Synthesis: Reusable Patterns vs. Pitfalls to Avoid

The comparative code analysis across all four repositories is synthesized below:

| Feature / Architecture Component | DrillMind | DrillSense | DDR_UTAH_FORGE | DrillScribe | **eRTMAC-NWIS Target** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Real-Time Telemetry Streaming** | ✅ Python Streamer | ❌ None | ❌ None | ❌ None | ✅ **WITSML/WebSocket Streamer** |
| **Automated Rig-State Engine** | ✅ Rule-Based | ❌ None | ❌ None | ❌ None | ✅ **State Machine Engine** |
| **Scanned PDF Layout OCR** | ⚠️ Naive Text | ⚠️ PDFMiner | ✅ Tesseract + Layout | ⚠️ Text parser | ✅ **PyMuPDF + Layout OCR** |
| **Hybrid RAG (BM25 + Dense)** | ✅ Yes | ⚠️ Dense only | ✅ Yes | ❌ None | ✅ **Hybrid BM25 + pgvector** |
| **Geospatial Map & Radius Search** | ❌ None | ❌ None | ❌ None | ❌ None | ✅ **Leaflet / PostGIS Engine** |
| **Dynamic Stratigraphic Correlation**| ❌ None | ❌ None | ❌ None | ❌ None | ✅ **Formation & TVDSS Aligner** |
| **Ahead-of-Bit Risk Corridor Track**| ❌ None | ❌ None | ❌ None | ❌ None | ✅ **Signature NWIS Track** |
| **Original PDF Bounding-Box Proof** | ❌ None | ❌ None | ⚠️ Snippet only | ❌ None | ✅ **Embedded PDF Page Viewer** |
