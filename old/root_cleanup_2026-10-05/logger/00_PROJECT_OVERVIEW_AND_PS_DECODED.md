# SIH 26121 — eRTMAC-NWIS: Project Overview & Problem Statement Decoded

**Problem Statement ID:** 26121  
**Title:** eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations  
**Organization:** Oil India Limited (OIL)  
**Category:** Software | **Theme:** Smart Automation  
**Target User:** Drilling Supervisors, Drilling Engineers, eRTMAC Monitoring Analysts, Subsurface G&G Teams  

---

## 1. Executive Summary & Problem Decomposition

### The Real-World Operational Context
Oil India Limited (OIL) operates exploration and production assets across key basins (such as the Upper Assam Basin / Assam-Arakan Basin). Drilling complex wells incurs enormous capital expenditure ($5M–$30M+ per well) and severe operational hazards (lost circulation, pipe sticking, kicks/blowouts, extreme torque/drag, casing failures). Non-Productive Time (NPT) costs the industry millions of dollars annually.

### What OIL Already Has vs. The Critical Missing Layer
* **What OIL Already Has:**
  * **eRTMAC** (Real Time Data Monitoring and Analysis Centre) receiving real-time rig surface instrumentation, MWD/LWD telemetry, mud logging feeds, and mud parameters.
  * **Digital Initiatives:** DRIVE 2.0, Command and Control Centre, OT Data Lake.
  * **Massive Historical Archives:** Decades of Daily Drilling Reports (DDRs), Well Completion Reports (WCRs), Mud Logs, geological logs, casing reports, and incident reviews.
* **The Critical Gap:**
  * Historical offset well data is siloed in legacy PDFs, databases, and unstructured reports.
  * When an active well is drilling through a specific formation at 3,220 meters depth, engineers cannot instantaneously know:
    * *Which historical offset wells experienced hazards at this exact geological interval?*
    * *What were the precursor telemetry signatures before the hazard occurred?*
    * *What exact mitigation (e.g. LCM formulation, pill volume, mud weight adjustment) worked historically?*
  * Searching manually through archives takes hours or days—during active drilling, decisions must be made in minutes.

---

## 2. Core Philosophy: "Nearby is NOT the Same as Relevant"

Conventional GIS tools simply perform a geographic radius circle (e.g., show wells within 10 km). In subsurface drilling engineering, **this is inadequate**:
* A well **12 km away** with identical stratigraphy, formation dip, trajectory inclination, and reservoir pressure regime is **far more relevant** than a well **2 km away** drilled through an entirely different faulted block or stratigraphic sequence.
* Relevance is **dynamic and interval-specific**: Well X may be irrelevant at 1,500 m, but becomes the **#1 critical analog** at 3,240 m when entering a specific sandstone formation known for severe loss zones.

---

## 3. The 4 Core Questions NWIS Answers for the Drilling Team

```text
  ┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
  │     1. FIND     │ ──► │    2. UNDERSTAND    │ ──► │    3. CORRELATE     │ ──► │       4. WARN       │
  │ Which offset    │     │ What happened in    │     │ Does active well    │     │ Is active well      │
  │ intervals are   │     │ those offset        │     │ telemetry match     │     │ approaching a       │
  │ truly relevant? │     │ intervals?          │     │ pre-hazard trends?  │     │ known hazard zone?  │
  └─────────────────┘     └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                                             │
                                                                                             ▼
                                                                                  ┌─────────────────────┐
                                                                                  │      5. PROVE       │
                                                                                  │ Show exact DDR/WCR  │
                                                                                  │ source citations &  │
                                                                                  │ proven mitigations  │
                                                                                  └─────────────────────┘
```

---

## 4. The 5 Core Risk Families Targeted by PS 26121

| Hazard Family | Physical Mechanism | Historical Precursors / Offset Indicators | Historical Mitigation / Playbook |
|---|---|---|---|
| **1. Lost Circulation (Mud Loss)** | Natural/induced fractures, depleted sub-hydrostatic formations, high overbalance pressure. | Pit volume drop, flow-out reduction, SPP decrease, previous offset losses in same formation. | Stop drilling, adjust mud rheology/density, pump Lost Circulation Material (LCM) pills (medium/coarse blends), spot pill. |
| **2. Stuck Pipe (Differential / Mechanical)** | Differential pressure sticking against permeable formations, key seating, hole pack-off from poor hole cleaning. | Overpull on trips, erratic torque, hook load escalation, cuttings volume drops. | Jarring up/down, working pipe, acid/diesel/lubricant spotting pills, reducing mud weight, back-reaming. |
| **3. Overpressure / Well Kick** | Penetrating an unexpected high-pressure reservoir zone; formation pressure > hydrostatic mud pressure. | Pit volume increase ("pit gain"), flow-out increase without pump change, drilling break (sudden ROP jump), background gas increase. | Shut-in well (BOP activation), measure SIDPP/SICP, calculate kill mud weight, execute Driller's Method or Wait & Weight. |
| **4. Excessive Torque & Drag** | High dogleg severity, hole doglegs, tortuosity, swelling shale/sloughing, poor lubrication. | Exponential torque spikes, fluctuating surface RPM, drag during connections. | Hole cleaning sweeps, adding drilling lubricants, optimizing BHA stabilizer placement, controlled ROP. |
| **5. Casing / Cementing Complications** | Incomplete mud displacement, channelled cement, lost returns during cementing, flash set. | Low cement bond log (CBL) quality in offset wells, losses during circulation prior to cementing. | Optimize centralizer spacing, pre-flush/spacer volume design, two-stage cementing, squeeze cementing remedies. |

---

## 5. Human-in-the-Loop Decision Support

NWIS is strictly designed as an **augmented decision support platform**, NOT an autonomous robotic drilling controller.
* It alerts drilling supervisors and eRTMAC engineers **15–50 meters before entering historical risk corridors**.
* It displays clear confidence metrics and the exact PDF page/paragraph evidence so licensed engineers make authoritative, well-informed calls with zero guesswork.
