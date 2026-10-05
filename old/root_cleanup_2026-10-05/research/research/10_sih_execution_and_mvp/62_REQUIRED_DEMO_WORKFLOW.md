# SIH 26121 — Required Demonstration Workflow: 15-Stage Presentation Narrative

## 1. Executive Summary
This document establishes the minute-by-minute, 15-stage demonstration script for the 10-minute SIH Grand Finale evaluation. It synchronizes live telemetry playback, spatial offset alignment, predictive corridor activation, SHAP explainability, and one-click PDF proof into an unassailable engineering narrative that directly addresses the concerns of Oil India Limited evaluators.

---

## 2. 15-Stage Demonstration Timeline

```
                                  10-MINUTE DEMO NARRATIVE FLOW
  0:00 ────────────────── 2:00 ────────────────── 5:00 ────────────────── 8:00 ────────────────── 10:00
   │                       │                       │                       │                       │
   ▼                       ▼                       ▼                       ▼                       ▼
  ACT I: THE HOOK        ACT II: SPATIAL ALIGN   ACT III: CORRIDOR ALARM  ACT IV: PDF PROOF       ACT V: ROI & CLOSE
  • Upper Assam Context   • PostGIS Map           • 1 Hz Telemetry Play    • Bounding Box Reveal   • ₹20 Cr Savings
  • Duliajan Dilemma      • TVDSS Stratigraphy    • TreeSHAP Attribution   • Tool-Augmented Chat   • Air-Gapped Arch
```

---

## 3. Minute-by-Minute Operational Script

### Act I: The Operational Hook & Problem Statement (0:00 – 1:30)
- **Stage 1 (Operational Context):** Present the live rig scenario: *"Well Moran NH-104 is drilling at 3,180 m in Upper Assam, targeting the Barail reservoir at 3,450 m. OIL's Duliajan eRTMAC is monitoring live WITS telemetry."*
- **Stage 2 (The Fatal Blind Spot):** *"eRTMAC sees the current ROP and pump pressure, but they are blind to the fact that 25 meters ahead lies a severe lost circulation zone that swallowed ₹45 Lakhs in mud on offset wells."*

### Act II: Dynamic Spatial & Stratigraphic Alignment (1:30 – 3:30)
- **Stage 3 (PostGIS 3D Map View):** Switch to the NWIS dashboard. An interactive 3D map displays Well NH-104 and 15 nearby legacy wells in Moran field.
- **Stage 4 (Dynamic Relevance Ranking):** Show the active offset list. As the bit advances, the system recalculates relevance scores $\Omega(w, z)$, promoting Well NH-09 and Well NH-12 to the top based on formation dip and stratigraphy.
- **Stage 5 (Stratigraphic Normalization):** Demonstrate how offset measured depths are converted into active well target depths via TVDSS ratio ($\xi = 1.042$), preventing the "Measured Depth Trajectory Trap."

### Act III: The Ahead-of-the-Bit Risk Corridor & Early Warning (3:30 – 6:00)
- **Stage 6 (Forward Corridor Activation):** The bit reaches 3,205 m. The **Historical Risk Corridor** ahead of the bit ($3,205 - 3,235\text{ m}$) turns Amber: *"Approaching Depleted Barail Sand 4. Historical Hazard: Total Lost Circulation."*
- **Stage 7 (Live Telemetry Replay):** Start streaming 1-Hz telemetry. Standpipe pressure begins a subtle decay ($\Delta SPP = -280\text{ kPa}$ over 40 seconds) and flow-out delta drifts negative ($-95\text{ L/min}$).
- **Stage 8 (Multi-Parameter Corroboration):** The decoupled LightGBM engine corroborates the telemetry trend with the historical risk corridor, elevating the alert to **Red Tier-1 Warning: Impending Mud Loss**.
- **Stage 9 (TreeSHAP Explanation):** The alert card opens to reveal the TreeSHAP attribution: Flow Deficit (+44%), SPP Drop (+32%), Barail Proximity (+24%).

### Act IV: One-Click Bounding-Box Proof & Agentic Chat (6:00 – 8:30)
- **Stage 10 (The Proof Click):** Click *"Verify Historical Evidence"*.
- **Stage 11 (PDF Bounding Box Reveal):** The system opens the scanned 2018 Daily Drilling Report (DDR #42) of Well NH-09, with a yellow bounding box highlighting: *"Lost 45 m³ mud at 3,228 m. Spotted 20 m³ mica/calcium carbonate LCM pill. Losses cured."*
- **Stage 12 (Zero-Hallucination Verification):** Emphasize: *"The drilling supervisor does not have to trust our AI model; they can see the exact signed DDR from 6 years ago!"*
- **Stage 13 (Tool-Augmented Natural Language Query):** Ask the chatbot: *"What LCM pill was used in NH-09 and will it exceed our casing burst pressure?"* The orchestrator calls verified tools and delivers a safe, calculated recommendation in 2 seconds.

### Act V: Business Case, Architecture & Closing Defense (8:30 – 10:00)
- **Stage 14 (Sovereignty & Architecture):** Show that the entire stack runs locally on Docker without external cloud calls, respecting DGH NDR data sovereignty.
- **Stage 15 (Financial ROI & Summary):** Conclude with quantifiable business impact: *"By eliminating 4 stuck pipe or total loss events per year, NWIS saves Oil India Limited over ₹15–₹25 Crore annually."*
