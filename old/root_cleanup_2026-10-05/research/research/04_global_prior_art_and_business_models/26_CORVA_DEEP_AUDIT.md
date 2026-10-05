# SIH 26121 — Corva: Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** Corva AI LLC (Houston, Texas, USA)
- **Market Position:** The modern benchmark for cloud-native real-time drilling and completion data analytics; widely adopted by North American shale operators and international IOCs.
- **Flagship Digital Platform:** **Corva Drilling Platform** & **Corva App Store**.
- **Primary Domain Focus:** High-frequency real-time sensor analytics, open developer APIs, and collaborative operational dashboards.

---

## 2. Deep Dive: Corva Drilling Platform & Real-Time App Model

Corva revolutionized the upstream software industry by abandoning monolithic desktop software in favor of a modern, cloud-native, web-based micro-app architecture:

```
[CORVA REAL-TIME DRILLING PLATFORM ARCHITECTURE]
Rig Floor Sensors & MWD Feeds (WITS / WITSML 1-Hz to 10-Hz Telemetry)
       │
       ▼ (High-Throughput Kafka / WebSockets Cloud Ingestion Pipeline)
Corva Central Time-Series Cloud Engine (AWS / Kubernetes)
       │
       ▼
Corva Modular Micro-App Ecosystem (100+ Specialized Engineering Apps)
       ├── 1. Real-Time Torque & Drag Modeling (Broomstick plot overlays)
       ├── 2. Drilling Dysfunction & Vibration Monitoring (Stick-slip, whirl)
       ├── 3. Offset Well Comparative Strip Charts (Curve overlays by depth)
       ├── 4. Hazard Avoidance & Geosteering Target Tracking
       └── 5. ROP & Connection Time Benchmarking
       │
       ▼
High-Density, Modern Dark-Mode Operational Web Console
       └── Sub-second latency synchronization between rig cabin and remote office
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Replaces slow, clunky legacy desktop surveillance software with a fast, modern web browser interface that aggregates live rig data and calculates engineering models in real time.
- **Offset Comparison Mechanism:** Allows engineers to select offset wells from a map and overlay their historical gamma ray, ROP, torque, and casing seats directly onto the active well's real-time drilling track.
- **App Store & Developer Center:** Features an open SDK allowing operators to write custom Python/JavaScript micro-apps that run inside the Corva dashboard.
- **UI/UX Excellence:** Recognized as the industry gold standard for **dark-mode, high-density, ergonomic drilling dashboards**.

`[VERIFIED: Corva Drilling Official Portal: https://www.corva.ai]`

---

## 3. Reverse-Engineering Forensic Questionnaire: Corva Platform

| Technical & Operational Question | Corva Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it stream high-frequency real-time rig sensor telemetry?** | **YES** | Industry-leading 1-Hz streaming pipeline with WebSockets. |
| **Does it overlay historical offset curves on the active well?** | **YES** | Provides offset parameter overlays in real time. |
| **Does it ingest unstructured historical scanned PDFs via AI?** | **NO** | Operates strictly on numerical time-series and directional surveys; lacks an automated OCR/NLP pipeline for legacy DDR/WCR documents. |
| **Does it extract qualitative lessons learned from text?** | **NO** | Focuses on numerical and sensor physics, not qualitative narrative intelligence. |
| **Is it deployed at Oil India Limited?** | **NO** | Zero documented deployment inside OIL. |
| **Can it run completely air-gapped on-premise?** | **NO** | Native cloud SaaS platform requiring continuous AWS connectivity. |

---

## 4. UI/UX Design Inspiration & Lessons for NWIS

While Corva does not solve the historical document intelligence problem of PS 26121, **it provides the definitive UI/UX benchmark for how NWIS must present information**:

1. **Anti-AI-Slop Interface:** Avoid generic, empty, toy chatbot screens. NWIS must adopt Corva's high-density, dark-mode, multi-panel layout:
   - Panel A: Active well status, trajectory, and live sensor curves.
   - Panel B: Interactive geospatial offset map with radius filter.
   - Panel C: Dynamic depth-indexed correlation track with approaching risk corridor.
   - Panel D: Searchable institutional memory knowledge base with original document page evidence.
2. **Instant Responsiveness:** Sensor graphs and spatial maps must render smoothly without sluggish reload delays.
3. **Ergonomic Clarity:** Critical alerts must be color-coded according to OISD/API conventions (Red = Critical, Amber = Caution, Green = Normal) with clear lead-time countdowns.
