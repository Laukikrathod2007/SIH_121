# SIH 26121 — Halliburton: Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** Halliburton (Landmark Software & Services)
- **Market Position:** One of the "Big Three" global oilfield service providers; dominant in well construction software, cementing, and directional drilling.
- **Flagship Digital Platform:** **DecisionSpace 365** (Cloud-native enterprise E&P platform).
- **Primary Solutions Audited:**
  1. **OpenWells** (Industry benchmark for daily drilling operations and well lifecycle reporting)
  2. **Digital Well Program (DWP)** & **Digital Well Construction**
  3. **iVRO (integrated Virtual Real-Time Operations)**
  4. **Landmark Well Plan** (Active hydraulics engine inside Oil India Limited)
  5. **InformatiQ Acquisition** (AI-driven offset well analytics)

---

## 2. Deep Dive: OpenWells Operations Software

For over two decades, Halliburton's **OpenWells** has served as the global oil and gas industry's primary system of record for wellsite operational reporting:

```
[HALLIBURTON OPENWELLS FUNCTIONAL ARCHITECTURE]
Rig Floor Tour Sheets & Daily Operations Logs
       │
       ▼
OpenWells Structured Relational Database (EDM - Engineer's Data Model)
       │
       ├── Daily Drilling Reports (DDR) / Mud Reports / Casing Tallies / Bit Records
       ├── Standardized IADC / NPT Event Categorization (Time-breakdown per operation)
       └── Technical Limit & Best Practices Tracking
       │
       ▼
Engineering Analytics & Benchmarking Modules
       ├── Section-by-Section Offset Performance Comparison
       ├── Cumulative Cost & Operational Time vs. Depth Tracking
       └── Lessons-Learned Historical Retrieval (Keyword/Category Search)
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Eliminates paper morning reports; establishes a rigorous, standardized digital operational log across all company and contractor rigs.
- **Target Users:** Rig-site Drilling Supervisors (Company Men), Drilling Superintendents, Asset Performance Engineers.
- **Offset Well Comparison:** Allows engineers to query historical wells by hole section (e.g. 12-1/4" section) to benchmark ROP, bit hours, and NPT occurrences.
- **Limitation:** OpenWells is fundamentally a **structured data repository**. It relies on humans to fill in structured forms. It does not automatically parse unstructured scanned PDFs or freehand historical text via AI/OCR.

`[VERIFIED: Halliburton OpenWells Portal: https://www.halliburton.com/en/products/digital-well-operations/openwells-software]`

---

## 3. Deep Dive: Digital Well Program (DWP) & InformatiQ AI Integration

To modernize well planning, Halliburton introduced the **Digital Well Program** on DecisionSpace 365:
- **Cross-Disciplinary Digital Workspace:** Connects operators, drilling contractors, and service companies on a shared cloud data model.
- **InformatiQ Acquisition:** Halliburton acquired **InformatiQ**, a specialized software firm, specifically to incorporate cloud-native **AI-driven offset-well analysis** into the Digital Well Program.
- **Offset Analytics Capabilities:** Ingests historical offset well data to calculate statistical drilling parameter envelopes (safe WOB, RPM, and flow rate ranges) and automate engineering calculation handoffs.

`[VERIFIED: Halliburton Acquisition Press Release: https://www.halliburton.com/en/about-us/press-release/halliburton-acquires-informatiq-to-expand-cloud-native-digital-capabilities]`

---

## 4. Deep Dive: iVRO & Landmark Well Plan in Oil India Limited

### 1. iVRO (integrated Virtual Real-Time Operations)
Halliburton's iVRO platform acts as a remote surveillance command center suite:
- Connects thousands of archived historical wells with live rig telemetry streams.
- Combines predictive drilling engineering models with real-time sensor alarms.

### 2. Landmark Well Plan — Verified Active Deployment in OIL
- **Direct Primary Evidence:** In its official 2024–25 Annual Report, **Oil India Limited explicitly states that it utilizes Landmark Well Plan software** for real-time mud-hydraulics, surge/swab, and well control analysis.
- **Architectural Implication for NWIS:**
  - OIL engineers are already trained on and trust Halliburton's Landmark physical modeling equations.
  - NWIS should **not attempt to recreate basic mud hydraulics from scratch**.
  - Instead, NWIS must position itself as the **cognitive institutional memory and offset hazard engine** that feeds contextual historical constraints into OIL's existing Landmark and eRTMAC workflows.

`[VERIFIED: OIL Annual Report 2024-25; Halliburton Landmark Disclosures]`

---

## 5. Reverse-Engineering Forensic Questionnaire: Halliburton Stack

| Technical & Operational Question | Halliburton Capability Status | Detailed Engineering Reality |
| :--- | :--- :--- | :--- |
| **Does it track historical drilling events and NPT?** | **YES** | OpenWells is the global standard for IADC-coded NPT tracking. |
| **Does it correlate offset wells by hole section?** | **YES** | OpenWells benchmarks technical limits across offset hole sections. |
| **Does it ingest unstructured historical scanned PDFs via AI?** | **PARTIAL** | InformatiQ integration adds NLP/offset intelligence; core OpenWells remains form-centric. |
| **Does it project live dynamic risk corridors ahead of the bit?** | **PARTIAL** | DWP projects planned risk profiles; real-time dynamic projection requires full iVRO suite. |
| **Is it deployed inside Oil India Limited today?** | **YES (PARTIAL)** | Landmark Well Plan is actively deployed; enterprise DWP/InformatiQ suite is not verified at OIL. |
| **Can it run as a standalone sovereign microservice alongside eRTMAC?** | **NO** | Deeply locked into Halliburton's proprietary DecisionSpace 365 / EDM architecture. |

---

## 6. Conclusions for SIH 26121
1. **Halliburton Validates the Problem Space:** Halliburton's acquisition of InformatiQ proves that even the global market leader in drilling software recognized that structured databases alone were insufficient and required AI-powered offset-well intelligence.
2. **The OpenWells Data Opportunity:** Because OpenWells is widely used across the industry (and in Indian assets), historical drilling reports follow OpenWells/IADC structural conventions. NWIS parsers can exploit this structural regularity to achieve near-100% extraction precision on DDR forms.
3. **Complementing Landmark at OIL:** By positioning NWIS as an agile decision-support companion that complements OIL's active Landmark Well Plan setup, the solution avoids redundant physical modeling and targets the unaddressed institutional memory gap.
