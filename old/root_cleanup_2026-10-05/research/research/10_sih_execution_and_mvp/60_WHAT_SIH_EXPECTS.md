# SIH 26121 — What Smart India Hackathon & Oil India Limited Expect Us to Build

## 1. Executive Summary
This document provides a forensic analysis of what the Smart India Hackathon (SIH) evaluators, Ministry of Petroleum & Natural Gas (MoPNG) officials, and senior drilling superintendents from **Oil India Limited (Duliajan)** expect to see in a winning submission for **Problem Statement 26121**. It strips away academic hand-waving to establish the exact technical deliverables, the rigorous cross-examination criteria, and the operational proof required to win 1st place.

---

## 2. Forensic Breakdown: Explicit vs. Inferred SIH Requirements

```
                               PS 26121 REQUIREMENT FORENSICS
┌────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ EXPLICIT REQUIREMENTS (Written in PS 26121)            │ INFERRED TECHNICAL REALITIES (Required to Work)        │
├────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. Map nearby offset wells.                            │ • PostGIS spatial radius query with true 3D deviation. │
│ 2. Access historical drilling experience instantly.   │ • OCR/NLP ingestion of unstructured scanned DDR PDFs.  │
│ 3. Correlate drilling/geological/reservoir parameters. │ • Stratigraphic normalization (TVDSS ratio ξ) not MD.  │
│ 4. Identify historical problems at relevant depths.    │ • Dynamic Ahead-of-the-Bit Risk Corridor projection.   │
│ 5. Predict potential risks & generate proactive alerts.│ • Multi-parameter sensor corroboration (SPP, Flow).    │
│ 6. Recommend mitigations based on past experience.     │ • Verified engineering countermeasures (LCM recipes).  │
│ 7. Provide a usable dashboard for field/office crews.  │ • Low-latency, dark-mode, air-gapped industrial UI.    │
│ 8. Operate alongside OIL's existing eRTMAC center.     │ • Ingest standard WITS0/WITSML streams from MLUs.      │
└────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. The 3 Jury Personas & Their Disqualification Traps

SIH panels for upstream energy problem statements are uniquely composed of three distinct evaluators:

```
[THE SIH 26121 EVALUATION TRIAD]
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ 1. OIL DRILLING SUPERINTENDENT  │ 2. eRTMAC / IT SYSTEMS HEAD     │ 3. MoPNG / ACADEMIC SPECIALIST  │
│ (25+ Yrs Duliajan Experience)   │ (Enterprise Data & Networks)    │ (Data Sovereignty & ML Rigor)   │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│ • Skeptical of AI wrappers.     │ • Focuses on streaming WITSML.  │ • Tests data provenance & FTO.  │
│ • Will test borehole geometry.  │ • Rejects cloud lock-in.        │ • Demands uncertainty bounds.   │
│ • "Do you know Barail coal?"    │ • "Does it crash with 10 wells?"│ • "Are you using public APIs?"  │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

### The 4 Fatal Anti-Patterns That Trigger Immediate Disqualification:
1. **The "Toy Streamlit Wrapper":** Uploading a static CSV, running a generic Scikit-learn `.predict()` script, and displaying a plain text box. Evaluator reaction: *"This is a 2nd-year college assignment, not a drilling decision-support platform."*
2. **The "Raw Measured Depth Fallacy":** Searching offset wells within $\pm 50$ meters of raw measured depth. Evaluator reaction: *"You don't understand basic borehole geometry. In deviated wells, your alert is 200 meters off-target!"*
3. **The "Hallucinating Chatbot":** Asking an ungrounded LLM how to cure stuck pipe without providing sensor numbers or telemetry corroboration. Evaluator reaction: *"Drilling superintendents will never trust a generic chatbot with a ₹50 Crore rig."*
4. **The "Multi-Agent Swarm Debate":** Demonstrating 3 agents arguing in a loop for 35 seconds. Evaluator reaction: *"A gas kick surfaces in 90 seconds. Your system took 35 seconds just to agree on what question was asked!"*

---

## 4. The Exact Technical Deliverables Expected in the Demo

To secure 1st place, the system must demonstrate **6 concrete production-grade capabilities**:

### Deliverable 1: Live Telemetry Replay Engine
* A WebSocket-driven simulator streaming 1-Hz WITS data (ROP, WOB, RPM, Torque, Standpipe Pressure, Flow In, Flow Out, Total Pit Volume).
* Simulates Well Moran NH-104 drilling from 3,180 m to 3,215 m in Upper Assam.

### Deliverable 2: Geospatial & Stratigraphic Offset Selector
* An interactive 3D map plotting the active wellhead and 15 historical offset wells in the Moran/Nahorkatiya field.
* Automatically recalculates offset relevance scores $\Omega(w, z)$ as the bit penetrates new geological horizons, converting offset measured depths into active well TVDSS via stratigraphic ratio $\xi$.

### Deliverable 3: Ahead-of-the-Bit Historical Risk Corridor
* As the bit reaches 3,205 m, a dynamic forward window ($+30$ m) projects into the Barail formation and flashes Amber: *"Approaching Depleted Barail Sand 4. Historical Hazard: Total Lost Circulation in 2 Offset Wells."*

### Deliverable 4: Multi-Parameter Telemetry Corroboration
* Rather than triggering false alarms from pump noise, the system waits for telemetry slopes to corroborate historical risks: Standpipe pressure decays by 280 kPa and Flow-out delta drops by 95 L/min.
* Instantly escalates to **Red Tier-1 Alarm: Impending Lost Circulation**.

### Deliverable 5: TreeSHAP Attribution & Conformal Uncertainty Bounds
* Displays an explainability card showing the top 3 physical driving features (Flow Deficit +44%, SPP Drop +32%, Barail Proximity +24%).
* Presents a 90% Conformal Prediction corridor, proving statistically calibrated confidence.

### Deliverable 6: 1-Click Bounding-Box Historical Document Proof
* The driller clicks *"Verify Historical Evidence"*.
* An embedded PDF viewer opens the scanned 2018 Daily Drilling Report (DDR #42) of offset well NH-09, with a yellow bounding box highlighting the exact sentence: *"Lost 45 m³ mud at 3,228 m. Spotted 20 m³ mica/calcium carbonate LCM pill. Losses cured."*

---

## 5. Defense Script: Handling Jury Cross-Examination

During the live Q&A, the evaluators will pressure-test the team with domain-specific questions:

| Jury Question | The Winning Technical Answer |
| :--- | :--- |
| *"Why shouldn't Oil India simply buy SLB Tela or Corva?"* | *"SLB Tela requires multi-crore annual USD subscriptions, locks OIL into the DELFI cloud, and violates DGH NDR data sovereignty mandates. Corva requires streaming unencrypted telemetry to US servers. NWIS is 100% sovereign, runs air-gapped at Duliajan eRTMAC, and has zero recurring per-well SaaS fees."* |
| *"How do you handle wells with different inclination angles?"* | *"We reject raw Measured Depth. We convert offset survey stations to TVDSS, normalize depth using the stratigraphic ratio $\xi = \Delta \text{TVD}_{active} / \Delta \text{TVD}_{offset}$, and invert through the active well's Minimum Curvature survey to project the exact ahead-of-the-bit target MD."* |
| *"What happens if the satellite VSAT connection drops during a storm?"* | *"NWIS deploys an edge-first architecture. The local industrial IPC on the rig floor maintains a cached corridor model and continues running 1-Hz hazard prediction completely offline."* |
| *"How do you prevent the AI from hallucinating fake drilling advice?"* | *"The LLM does zero mathematical calculations and zero ungrounded retrieval. It acts purely as a deterministic orchestrator calling verified Python tools. Every recommendation is anchored to a signed PDF page with bounding box coordinates."* |

---

## 6. Business ROI Case for Oil India Limited

* **Direct NPT Elimination:** Preventing just 4 stuck pipe or lost circulation events per year saves Oil India Limited between **₹15 Crore and ₹25 Crore** in rig day rates, mud rebuilds, and sidetracks.
* **Institutional Memory Protection:** Permanently captures and digitizes decades of Upper Assam field experience from retiring senior superintendents.
* **100% Indian Data Sovereignty:** Fully compliant with MoPNG, DGH NDR, and OISD-STD-187 guidelines.
