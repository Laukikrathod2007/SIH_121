# SIH 26121 — eRTMAC-NWIS: PPT Pitch Deck & Presentation Script

This document contains ready-to-use slide contents, pitch scripts, and anticipated Q&A defense for the final presentation.

---

## 1. The 1-Minute Elevator Pitch (Opening Statement)

> *"Honorable Judges and Oil India Leaders,  
> When drilling a 3,500-meter well costing tens of crores, the difference between a routine operation and a catastrophic blowout or multi-day Non-Productive Time (NPT) often comes down to one question: **'Has this exact geological interval caused trouble before, and what did we do about it?'**  
> Oil India already has modern real-time monitoring through eRTMAC and decades of rich historical drilling records. But when an engineer is on shift and an anomaly begins, they cannot spend hours sifting through thousands of historical PDF reports.  
> We built **eRTMAC-NWIS (Nearby Wells Intelligence System)**. NWIS is not just a map and not a generic chatbot. It dynamically correlates real-time drilling depth and telemetry with relevant historical offset intervals, detects emerging risk patterns, alerts the engineer **15 to 50 meters before entering a historical hazard corridor**, and shows the exact DDR page and proven mitigation procedure.  
> **Because in drilling engineering, nearby is NOT the same as relevant. NWIS finds the history that matters right now.**"*

---

## 2. Recommended PPT Slide Deck Structure (10-12 Slides)

### Slide 1: Title & Team
* **Title:** eRTMAC-NWIS (Nearby Wells Intelligence System)
* **Subtitle:** An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations
* **Problem ID:** 26121 | **Organization:** Oil India Limited
* **Team Name / Details**

### Slide 2: The Core Problem in Real-World Drilling
* **Key Challenge:** High cost of NPT ($50k–$200k/day), hazards (Lost Circulation, Stuck Pipe, Kicks, Torque Spikes, Cementing Failures).
* **Current State:** Oil India has eRTMAC for live monitoring, but historical knowledge in DDRs/WCRs remains fragmented.
* **The Critical Gap:** Lack of depth-aware, formation-aware historical context at decision time.

### Slide 3: Our Core Philosophy — "Nearby ≠ Relevant"
* Visual comparison:
  * *Well A (2 km away):* Faulted boundary, different formation sequence $\rightarrow$ **Low Relevance**.
  * *Well B (12 km away):* Same formation layer, identical dip angle, prior critical mud loss at 3,248 m $\rightarrow$ **Top Relevant Analog**.
* Dynamic multi-factor relevance ranking (Distance + Formation + Depth Overlap + Trajectory + Hazard History).

### Slide 4: System Architecture & Workflow
* 4-Tier Architecture Diagram (Ingestion $\rightarrow$ Spatial/Vector DB $\rightarrow$ Intelligence Core $\rightarrow$ Operational Cockpit).
* Highlights: PostgreSQL/PostGIS, WITSML compliance, hybrid RAG, anomaly detection.

### Slide 5: Key Innovation 1 — Dynamic Offset Relevance Engine
* 2-Stage Retrieval: Spatial candidate filtering + dynamic 5-weight contextual ranking.
* Scores update in real time as the bit drills deeper.

### Slide 6: Key Innovation 2 — Stratigraphic Correlation & Historical Risk Corridors
* Stratigraphic normalization (TVD + Formation Tops alignment).
* **Historical Risk Corridor:** Grouping offset hazard events into spatial-depth corridors with proactive lead-time warning (e.g. *"15 meters to known loss zone"*).

### Slide 7: Key Innovation 3 — Multi-Signal Hybrid Risk Engine
* Combining 3 independent layers:
  1. Historical Prior (offset incident frequency)
  2. Real-Time Telemetry Anomaly (SPP, Torque, Flow out deviations)
  3. Calibrated ML Classifier
* **4-Pillar Confidence Breakdown:** Decoupling ML probability, Evidence strength, Data quality, and Source grounding.

### Slide 8: Key Innovation 4 — Evidence Grounding & PDF Citation Modal
* Zero hallucination: Every alert links to the exact DDR/WCR report, page number, and historical mitigation playbook (e.g., specific LCM pill blend and pump rate used).
* Human-in-the-Loop decision support.

### Slide 9: Live Operational Cockpit & Replay Demonstration
* Walkthrough screenshots/video of the single-pane Operations Center:
  * Geospatial Map + Dynamic Ranking
  * Wellbore Stratigraphic Track + Risk Corridor
  * Live Telemetry Gauges + Anomaly Trigger
  * Evidence Modal + AI Tool-Calling Copilot

### Slide 10: Standards Compliance & Scalability (OIL Ecosystem Integration)
* Built to interface with Oil India's eRTMAC, DRIVE 2.0, and OT Data Lake.
* WITSML 1.4/2.0 and OSDU data model compatibility.
* On-premise / edge-deployable with Docker & local LLM (Ollama).

### Slide 11: Business Impact & ROI for Oil India Limited
* 25–40% reduction in drilling hazard response time.
* Significant NPT reduction (saving crores per drilling campaign).
* Institutional knowledge retention (senior engineer wisdom captured systematically).

### Slide 12: Conclusion & Future Roadmap
* Summary: Bridging real-time drilling with institutional memory.
* Roadmap: 3D Geocellular model integration, multi-well simultaneous monitoring.

---

## 3. Anticipated Judge Questions & Bulletproof Defense

### Q1: *"How is your solution different from standard GIS mapping or a basic ChatGPT RAG chatbot?"*
* **Defense:**
  1. *GIS limitation:* Standard GIS only knows $(x, y)$ coordinates. NWIS computes multi-dimensional subsurface relevance across $(x, y, z)$ depth, formation stratigraphy, trajectory dogleg, and historical hazard density.
  2. *Chatbot limitation:* Generic RAG hallucinates depth numbers and has no awareness of real-time sensor streams. NWIS uses structured database facts for exact depth intervals, uses RAG strictly for narrative report evidence, and couples it with real-time sensor anomaly detection.

### Q2: *"Can this system automatically control the rig or adjust drilling parameters?"*
* **Defense:**  
  * *No, and by design!* In drilling operations governed by Directorate General of Hydrocarbons (DGH) and Oil Industry Safety Directorate (OISD) standards, safety-critical decisions require qualified engineering judgment. NWIS is an **augmented decision support tool** that provides early warning, evidence, and historical playbooks to empower the Drilling Supervisor.

### Q3: *"How does the system handle areas with very few or no offset wells (Wildcat Wells)?"*
* **Defense:**  
  * Unlike standard ML models that output a false "0% Risk" when no data exists, NWIS explicitly triggers an **"Insufficient Historical Evidence"** status. It falls back to pure sensor anomaly detection and formation prognosis, alerting the engineer to proceed with heightened vigilance.

### Q4: *"How does the system handle directional / inclined wells where Measured Depth (MD) differs from True Vertical Depth (TVD)?"*
* **Defense:**  
  * NWIS computes trajectories using minimum curvature and maps all historical events and formation tops to **True Vertical Depth (TVD)** and **Stratigraphic Normalized Depth** (distance from formation top), preventing false correlations caused by wellbore inclination.
