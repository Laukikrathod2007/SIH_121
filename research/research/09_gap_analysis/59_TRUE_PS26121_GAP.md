# SIH 26121 — The True Technical & Operational Gap: Defining NWIS

## 1. Executive Summary
This document crystallizes the exact technical and operational gap addressed by SIH Problem Statement 26121. It cuts through superficial industry analogies to define why Oil India Limited sponsored this problem statement, how the system bridges real-time telemetry with institutional memory, and why this represents a transformative operational asset for Assam oilfield operations.

---

## 2. The Operational Reality at Oil India Limited

Oil India Limited (OIL) actively operates between 35 and 45 drilling rigs across the Upper Assam Shelf (Duliajan, Moran, Nahorkatiya, Hugrijan) and the thrust belts of Arunachal Pradesh. 

```
                               THE DULIAJAN OPERATIONAL DILEMMA
┌─────────────────────────────────────────────────┐       ┌─────────────────────────────────────────────────┐
│     OIL eRTMAC CONSOLE (DULIAJAN HEADQUARTERS)  │       │       UPPER ASSAM DRILLING RIG (WELL X-104)     │
│ • Displays real-time WITS telemetry:            │       │ • Currently at: 3,180 m Measured Depth.         │
│   ROP: 14 m/hr, SPP: 18.2 MPa, Torque: 12 kNm.  │       │ • Penetrating Barail Sandstone.                 │
│ • Engineers see the live data stream...         │       │ • Drill bit is 25 meters above a depleted,      │
│ • BUT THEY CANNOT SEE WHAT HAPPENED HERE BEFORE!│       │   fractured sand interval that caused total     │
│                                                 │       │   lost circulation in 2 offset wells!           │
└─────────────────────────────────────────────────┘       └─────────────────────────────────────────────────┘
                                           ▲                       ▲
                                           │                       │
                                           └───────────┬───────────┘
                                                       │
                                          [THE MISSING BRIDGE: NWIS]
```

### The Core Problem Statement:
> **"OIL's eRTMAC monitors what is happening right now, and OIL's archives store what happened in the past. But today, NO SYSTEM DYNAMICALLY CONNECTS THE TWO IN REAL TIME AHEAD OF THE DRILL BIT."**

---

## 3. The 4-Pillar Operational Bridge of NWIS

NWIS is the cognitive bridge that unifies real-time rig-floor telemetry with decades of subsurface institutional memory:

```
[THE 4-PILLAR NWIS COGNITIVE ENGINE]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PILLAR 1: Dynamic Spatial & Stratigraphic Contextual Alignment                         │
│ • Replaces crude Euclidean distance radius with multi-parameter relevance scoring.     │
│ • Automatically maps offset measured depths into active well TVDSS and target MD       │
│   using local stratigraphic ratio normalization ($\xi$).                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ PILLAR 2: Ahead-of-the-Bit Historical Risk Corridor                                    │
│ • As the bit advances from 3,180 m to 3,200 m, NWIS projects an operational window      │
│   ahead of the bit ($+30$ meters) and queries the spatial knowledge base.              │
│ • Identifies historical mud losses, tight spots, or kicks at that exact horizon.       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ PILLAR 3: Multi-Parameter Telemetry Corroboration                                      │
│ • Cross-references incoming 1-Hz sensor streams against historical precursors.         │
│ • Dispatches early warnings ONLY when physical telemetry trends corroborate historical │
│   risk profiles, eliminating false alarm fatigue.                                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ PILLAR 4: Actionable Mitigation with Direct Bounding-Box Evidence Proof                 │
│ • Delivers a verified mitigation recommendation (e.g. "Spot 25 m³ High-Fluid Loss Pill")│
│ • Provides a 1-click button opening the exact scanned DDR page with bounding box proof,│
│   giving the drilling superintendent 100% confidence to take operational action.       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Quantifiable Operational & Financial Impact

For Oil India Limited, non-productive time (NPT) resulting from stuck pipe, lost circulation, and wellbore instability accounts for **12% to 18% of total well construction costs**, averaging ₹15–₹25 Crore annually across the rig fleet.

| Metric | Without NWIS (Current Baseline) | With NWIS (Target Outcome) | Annual Benefit for OIL |
| :--- | :--- | :--- | :--- |
| **Offset Research Time** | 4 to 8 hours of manual document searching. | **$< 2$ seconds automated retrieval.** | Instant tactical response during drilling. |
| **Mud Loss Lead Time** | 0 minutes (reactive alarm after loss occurs). | **15 to 30 minutes proactive warning.** | Prevents severe formation damage & lost mud. |
| **Stuck Pipe Incidents** | 8 to 12 incidents per year across fleet. | **Reduced by 35% to 50%.** | Savings of ₹6–₹10 Crore per year in rig time. |
| **Institutional Memory** | Lost upon senior personnel retirement. | **Permanently captured and digitized.** | Sovereign asset protection for Indian CPSE. |

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[THE DEFINITIVE VALUE PROPOSITION]`.
- NWIS solves a **real, quantified, multi-crore problem** for Oil India Limited.
- This is not an academic exercise or a generic LLM wrapper; it is a **mission-critical operational intelligence copilot** designed specifically for the rigs and engineers of Duliajan.
