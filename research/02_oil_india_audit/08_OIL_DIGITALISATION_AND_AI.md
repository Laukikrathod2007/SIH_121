# SIH 26121 — Oil India Limited: Digitalisation Roadmap & AI Initiatives

## 1. Executive Summary
This document provides an audit of Oil India Limited's corporate digital transformation strategy, focusing on **Project DRIVE**, **Project DRIVE 2.0**, drilling software suites, operational data lake initiatives, and emerging Artificial Intelligence (AI) and Machine Learning (ML) adoption across upstream workflows.

---

## 2. Project DRIVE & DRIVE 2.0 Master Plan

OIL's enterprise digitalization program is branded internally as **Project DRIVE** (*Digital Readiness for Innovation and Value Enhancement*) and its successor **DRIVE 2.0**:
- **Core Vision:** Transform OIL into a digitally driven, data-centric Maharatna energy enterprise by integrating subsurface, surface, drilling, and business management operations.
- **Key Pillars of DRIVE 2.0:**
  1. *Subsurface Digitalization:* Automated 3D seismic interpretation, cloud-hosted petrophysical modeling, and unified geological database integration.
  2. *Drilling & Well Operations:* Remote surveillance via eRTMAC, intelligent well planning, predictive maintenance of rig equipment, and automated drilling reporting.
  3. *Production & Pipeline SCADA:* Real-time IoT monitoring across oil collecting stations (OCS), central gas gathering stations (CGGS), and the 1,157 km Naharkatiya-Barauni crude oil pipeline.
  4. *Enterprise Data Lake:* Consolidation of Operational Technology (OT) sensor data and Information Technology (IT) enterprise records into a centralized repository.

`[VERIFIED: OIL Digital Footprint Official Portal; OIL Annual Reports 2023-24, 2024-25]`

---

## 3. Current Drilling Software & Digital Engineering Portfolio

Oil India Limited does not rely on ad-hoc spreadsheets for core well planning. Its active engineering portfolio includes industry-standard commercial suites:

| Domain | Software Solution | Primary Application & Capabilities | Evidentiary Status |
| :--- | :--- | :--- | :--- |
| **Real-Time Mud Hydraulics** | Landmark (Halliburton) **Well Plan** | Surge/swab pressure calculation, equivalent circulating density (ECD) modeling, nozzle optimization, well control kick simulations. | `[VERIFIED: OIL Annual Report 2024-25]` |
| **Wellbore Trajectory & Directional Design** | Landmark **COMPASS** / SLB **Sysdrill** | 3D wellpath trajectory planning, anti-collision risk scanning, dogleg severity control. | `[VERIFIED: OIL Engineering Tenders]` |
| **Remote Rig Telemetry & Surveillance** | **eRTMAC 1.0 / 2.0** | Real-time multi-rig data acquisition, WITS/WITSML ingestion, 24/7 centralized monitoring. | `[VERIFIED: OIL Tender CDH6605P21]` |
| **Subsurface G&G Analytics** | Petrel (SLB) / DecisionSpace (Halliburton) | Seismic interpretation, reservoir structural modeling, formation top mapping. | `[VERIFIED: OIL Geosciences Recruitment & Tenders]` |
| **Daily Reporting & Rig Administration** | Internal SAP ERP & Rig Tour Sheet System | Daily cost tracking, equipment inventory, drilling contractor invoicing, operational logs. | `[VERIFIED: OIL Annual Report 2024-25]` |

---

## 4. Current AI, ML, and Advanced Analytics Initiatives

OIL's official disclosures outline specific areas where AI/ML and Generative AI technologies are currently being researched, piloted, or deployed:

### 1. Geoscience & Subsurface (G&G) Analytics
- Application of machine learning models for automated fault identification on 3D seismic cubes in the Upper Assam basin.
- AI-driven log-facies classification and synthetic log generation (e.g. predicting missing sonic or shear logs from Gamma Ray and Resistivity).

### 2. Intelligent Well Planning & Rig Scheduling
- Algorithms for optimizing rig movement sequences across clustered drilling locations to reduce rig move time and carbon footprint.
- Drill-bit performance analytics correlating rock unconfined compressive strength (UCS) with bit dull grades to recommend optimized cutter structures.

### 3. Frontier Offshore & Deepwater Real-Time Telemetry
- Operational deployment of high-frequency satellite monitoring on deepwater exploration drilling in the **Andaman Offshore Basin**, **Mahanadi Basin**, and deep frontier wells in **Jodhpur (Rajasthan)**.
- Real-time mud-hydraulics monitoring used dynamically to manage narrow drilling margins in ultra-deep HPHT wells.

`[VERIFIED: OIL Annual Report 2024-25; OIL Technology Briefs]`

---

## 5. Verified Reality vs. Publicly Unknown Matrix

To maintain strict truthfulness, the table below delineates what is verified from primary sources versus what remains internal or unknown:

| Feature / System Component | Status | Evidentiary Basis |
| :--- | :---: | :--- |
| **OIL operates 24/7 eRTMAC monitoring centre in Duliajan** | `[VERIFIED]` | Official technology disclosures and annual reports. |
| **OIL uses Landmark Well Plan for real-time mud hydraulics** | `[VERIFIED]` | Stated verbatim in Annual Report 2024-25. |
| **OIL has live telemetry from Andaman, Rajasthan, Mahanadi** | `[VERIFIED]` | Stated verbatim in Annual Report 2024-25. |
| **OIL is developing cloud-native eRTMAC 2.0** | `[VERIFIED]` | BSE/NSE regulatory filings 2024–25. |
| **OIL has an automated AI system for offset well DDR extraction** | `[DOES NOT EXIST]` | Proven absent: PS 26121 was created specifically to solve this. |
| **OIL has a live AI stuck-pipe / mud loss early warning platform** | `[DOES NOT EXIST]` | Proven absent: PS 26121 explicitly solicits predictive models for this. |
| **Exact internal database schemas and server IP configurations** | `[UNKNOWN]` | Confidential operational data; not publicly disclosed. |
| **Exact internal alert threshold limits for every field** | `[UNKNOWN]` | Varies by field asset and drilling contractor. |

---

## 6. Strategic Takeaways for NWIS Architecture

1. **Do not propose what OIL already has:** Proposing basic real-time telemetry streaming or standard hydraulic calculations is redundant, as OIL already has eRTMAC and Landmark Well Plan.
2. **Align with Project DRIVE 2.0:** Position NWIS as the cognitive institutional memory layer that complements eRTMAC 2.0, ingests data from OIL's Mud Logging Units, and exposes REST/WITSML APIs compatible with enterprise cloud architecture.
3. **Target the Missing Link:** The core value of NWIS lies exclusively in **contextual historical retrieval**, **dynamic offset interval correlation**, and **lead-time-aware predictive early warnings** grounded in verified historical precedents.
