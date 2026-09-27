# SIH 26121 — Open Questions & Future Research Agenda

## 1. Executive Summary
This document outlines the frontier engineering, algorithmic, and organizational questions that extend beyond the hackathon prototype. It defines the ongoing research roadmap for deploying and scaling NWIS across Oil India Limited's operational ecosystem.

---

## 2. The 5 Open Research Questions

```
                               FRONTIER RESEARCH QUESTIONS
┌─────────────────────────────────┬─────────────────────────────────┬─────────────────────────────────┐
│ Q1: FAULT THROW GEOSTEERING     │ Q2: MULTI-RIG EDGE SCALABILITY  │ Q3: CASING FATIGUE CORRELATION  │
│ • Real-time LWD dip updates     │ • 45 concurrent 10-Hz streams   │ • Tripping cycle damage models  │
├─────────────────────────────────┼─────────────────────────────────┼─────────────────────────────────┤
│ Q4: DRILTIME COGNITIVE LOAD     │ Q5: ACTIVE HUMAN FEEDBACK (RLHF)│ RESEARCH HORIZON                │
│ • Alert suppression at ROP>60m/h│ • Driller correction ingestion  │ • 12 to 36 Months Post-SIH      │
└─────────────────────────────────┴─────────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Granular Analysis of Open Questions

### Question 1: Dynamic Stratigraphic Re-Alignment During Fault Crossings
- **The Challenge:** In Upper Assam thrust belts, a drill bit may cross an unmapped sub-seismic fault that displaces formation tops by $\pm 20$ meters vertically.
- **Research Direction:** Integrate real-time LWD Gamma Ray cross-correlation with Dynamic Time Warping (DTW) to dynamically update the stratigraphic ratio $\xi$ and recalculate the Historical Risk Corridor within 30 seconds of crossing a structural boundary.

### Question 2: Multi-Rig Edge Concurrency on Limited Bandwidth
- **The Challenge:** Scaling the platform to monitor all 45 OIL rigs simultaneously over shared, high-latency satellite VSAT connections (256 kbps to 1 Mbps).
- **Research Direction:** Implement edge-side feature aggregation and MQTT/WebSocket binary compression (Protobuf / ETP), transmitting high-bandwidth raw logs only on anomaly triggers while streaming low-bandwidth health pulses during normal drilling.

### Question 3: Coupling Wellbore Hydraulics with Casing Fatigue
- **The Challenge:** Offset well failures often stem from accumulated casing wear and dogleg severity during extended drilling phases.
- **Research Direction:** Couple the cementing hazard model with a historical casing wear accumulation model that factors in rotating hours, dogleg severity, and mud abrasiveness.

### Question 4: Ergonomic Cognitive Load Management During Fast Drilling
- **The Challenge:** In top-hole sections (0–800 m) where ROP can exceed 60 m/hr, the risk corridor updates rapidly. Excessive notifications could overwhelm the driller.
- **Research Direction:** Implement a dynamic notification throttling heuristic: when ROP is high and formation risk is low, alert sensitivity is coarsened; when approaching high-risk depleted intervals, alarm corroboration sensitivity tightens.

### Question 5: Continuous Human Feedback Loop (Active Learning)
- **The Challenge:** When a drilling superintendent overrides an AI alert or adds a field remark (e.g. *"Loss occurred at 3,215m due to induced fracture from high surge pressure, not formation depletion"*), how is that knowledge ingested?
- **Research Direction:** Build an active learning ingestion pipeline where field overrides automatically create verified annotations in PostgreSQL, triggering periodic local model retraining.

---

## 4. Architectural Verdict for SIH 26121

**Verdict:** `[MATURE TECHNICAL VISION]`.
- Demonstrating awareness of these future frontier questions shows the SIH evaluation committee that the team is thinking far beyond the 36-hour hackathon, possessing a mature multi-year vision for Oil India Limited's digital drilling operations.
