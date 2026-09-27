# SIH 26121 — National Oilwell Varco (NOV): Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** NOV Inc. (formerly National Oilwell Varco)
- **Market Position:** The world's largest manufacturer of drilling rig equipment (top drives, drawworks, mud pumps, iron roughnecks) and rig automation operating systems.
- **Flagship Digital Platforms:**
  1. **KAIZEN™ Intelligent Drilling Optimizer (IDO)**
  2. **NOVOS™ Rig Operating System**

---

## 2. Deep Dive: NOV KAIZEN™ Intelligent Drilling Optimizer

NOV's **KAIZEN** represents one of the most technologically advanced commercial examples of comparing live drilling conditions against offset well data:

```
[NOV KAIZEN INTELLIGENT DRILLING OPTIMIZER]
Live Rig High-Frequency Sensor Stream (WOB, RPM, Torque, Vibration, SPP)
       │
       ▼
KAIZEN Real-Time Environmental Recognition Engine
       ├── Continuously evaluates current downhole cutting efficiency
       ├── Compares active well conditions against offset well performance
       └── Detects formation transitions, lithological changes, and dysfunction onset
       │
       ▼
Automated Optimization & Closed-Loop Control Loop
       ├── Advisory Mode: Displays recommended WOB/RPM setpoints to driller
       └── Control Mode: Writes setpoints directly to NOVOS rig control cyber-chair
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Mitigates real-time drilling dysfunctions (stick-slip, bit bounce, whirl) and maximizes Rate of Penetration (ROP) by dynamically adjusting drilling parameters based on offset machine learning benchmarks.
- **Offset Comparison in Real Time:** Actively pulls historical offset drilling performance to establish baseline expectations for rock drillability and mechanical specific energy (MSE).
- **Advisory vs. Closed-Loop Control:**
  - *Advisory Mode:* Presents recommended setpoints on the driller's console screen.
  - *Autonomous Control Mode:* Interfaces with the **NOVOS** rig operating system to take direct digital control of the top drive speed and drawworks brake, autonomously steering the bit along the optimal operating curve.

`[VERIFIED: NOV KAIZEN Portal: https://www.nov.com/products/kaizen-intelligent-drilling-optimizer]`

---

## 3. Deep Dive: NOVOS Rig Operating System
- **Architectural Nature:** NOVOS is not a desktop analytics tool; it is an industrial programmable logic controller (PLC) operating system installed directly on rig machinery.
- **App Ecosystem:** Allows third-party software developers to deploy containerized software algorithms ("apps") onto the rig floor to automate pipe connections, friction tests, and auto-drilling.

---

## 4. Reverse-Engineering Forensic Questionnaire: NOV Stack

| Technical & Operational Question | NOV Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it compare active drilling with offset wells?** | **YES** | Core advertised capability of KAIZEN. |
| **Does it execute autonomous closed-loop rig control?** | **YES** | Interacts directly with top drives and drawworks via NOVOS. |
| **Does it ingest unstructured historical PDF documents (DDRs/WCRs)?** | **NO** | Operates strictly on numerical rig sensor telemetry; zero document NLP capabilities. |
| **Does it extract lessons learned and operational narratives?** | **NO** | Focuses on mechanical cutting physics, not qualitative institutional memory. |
| **Is autonomous control what Oil India asked for in PS 26121?** | **NO (EXCLUDED)** | PS 26121 explicitly requests human-in-the-loop decision support, not autonomous rig control. |

---

## 5. Critical Domain Boundary: Decision Support vs. Autonomous Control

Understanding the fundamental distinction between **NOV KAIZEN** and **eRTMAC-NWIS** is vital for the SIH technical presentation:

```
[AUTONOMOUS CONTROL (NOV KAIZEN / NOVOS)]
Goal: Replace human driller reaction with closed-loop machine control of WOB/RPM.
Data: High-frequency surface sensors (10–100 Hz).
Focus: Mechanical rate of penetration, vibration damping, robotic automation.
Scope: The immediate 5 seconds of bit rotation.

[COGNITIVE DECISION SUPPORT (eRTMAC-NWIS)]
Goal: Augment human engineers with contextual institutional memory.
Data: Multi-source (PDF reports, WCRs, DDRs, geological tops, telemetry).
Focus: Subsurface hazard corridors, loss zones, kicks, stuck pipe, mitigations.
Scope: The next 10 to 50 meters ahead of the bit and historical precedent.
```

---

## 6. Conclusions for SIH 26121
1. **Never Confuse Decision Support with Rig Automation:** An inexperienced hackathon team might propose *"our AI will autonomously control the rig."* This is a severe operational violation. Rig control requires SIL-rated industrial hardware (like NOVOS) and strict regulatory certification. NWIS is strictly an engineering decision-support platform.
2. **KAIZEN Confirms Offset Value:** NOV’s substantial investment in KAIZEN proves that real-time comparison with historical offset wells is an established, high-value industrial discipline.
3. **The Clear Operational Boundary for NWIS:** NWIS focuses on the **cognitive and geological domain**—helping engineers anticipate approaching formations, understand historical risks, and review proven offset mitigations with verifiable document evidence.
