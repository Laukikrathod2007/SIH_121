# SIH 26121 — Oil India Limited: eRTMAC Deep Architectural Audit

## 1. Executive Summary & Identity
- **System Name:** eRTMAC (Enhanced Real-Time Monitoring & Analytics Center)
- **Operator:** Oil India Limited (OIL)
- **Primary Facility Location:** Drilling Headquarters, Duliajan, Dibrugarh, Assam, India.
- **Official Definition:** A centralized command and surveillance center designed to monitor multi-rig drilling operations in real time using high-frequency sensor telemetry, mud logging feeds, and drilling engineering analytics to enhance safety, improve ROP, and minimize Non-Productive Time (NPT).
- **Current Evolution:** OIL is actively upgrading to **eRTMAC 2.0**, transition from an on-premise monitoring room to a cloud-native, Software-as-a-Service (SaaS) unified command platform.
- **Evidence Base:**
  - Official OIL Technology Page: [Technology and Innovation \| Oil India Limited](https://www.oil-india.com/leveraging-technology) `[PRIMARY-SOURCE]`
  - OIL Tender Document: Tender No. CDH6605P21: *"Hiring of Services for Real-Time Monitoring & Analytics Centre (eRTMAC)"* `[PRIMARY-SOURCE]`
  - OIL BSE/NSE Regulatory Disclosures: FY 2024–25 digital roadmap `[PRIMARY-SOURCE]`

---

## 2. Technical Capabilities of eRTMAC (What It Already Does)

Based on official procurement documentation (Tender CDH6605P21) and technology releases, eRTMAC is already equipped with substantial real-time infrastructure:

```
[eRTMAC EXISTING ARCHITECTURAL STACK]
Rig Floor Sensors & Surface Instrumentation (WOB, RPM, Torque, SPP, Mud Flow, Pits)
       │
       ▼ (WITS Level 0 Serial / WITSML XML over TCP/IP)
Rig-Site Data Aggregation Unit (Mud Logging Unit - MLU)
       │
       ▼ (VSAT / 4G / Terrestrial Fiber Telemetry Stream)
eRTMAC Central Ingestion Server & Telemetry Database (Duliajan Center)
       │
       ├── [Real-Time 24/7 Visualization Console]
       │   ├── Multi-screen driller's strip chart (time & depth tracks)
       │   ├── Real-time hydraulics calculation (ECD, Annular Velocity)
       │   └── Instantaneous threshold alarms (e.g. Pit Volume Gain > 1 m³, SPP Drop > 15 bar)
       │
       ├── [Drilling Operations Repository]
       │   ├── Centralized telemetry storage (time-indexed and depth-indexed)
       │   └── Historical well parameter store (well trajectories, casing programs)
       │
       └── [Post-Well Review & Benchmarking Modules]
           ├── Rate of Penetration (ROP) benchmarking across bit runs
           └── Post-well action reviews and NPT event logging
```

### Audited Core Functions:
1. **Multi-Rig Concurrent Monitoring:** Concurrently ingests real-time feeds from 10 to 20+ active drilling and workover rigs operating across Assam, Rajasthan, and offshore blocks.
2. **Standardized Protocol Ingestion:** Full support for **WITS (Wellsite Information Transfer Specification)** and **WITSML (v1.4.1.1)** for data exchange between service contractors (Baker Hughes, SLB, Halliburton, Weatherford) and OIL servers.
3. **Hydraulics & Well Control Integration:** Integration with Landmark (Halliburton) **Well Plan** suite for real-time hydraulics modeling, surge/swab pressure estimation, and well control monitoring.
4. **24/7 Engineer Supervision:** Staffed around the clock by experienced petroleum engineers and mud logging specialists to assist the field Company Man during drilling complications.

`[VERIFIED: OIL Tender CDH6605P21; OIL Annual Report 2024-25]`

---

## 3. The eRTMAC 2.0 Cloud Modernization Program

In corporate filings and technology roadmaps, OIL has detailed the migration toward **eRTMAC 2.0**:
- **Cloud-Native SaaS Deployment:** Shifting central compute from isolated physical workstations in Duliajan to a secure private/hybrid cloud architecture with multi-region failover.
- **Broadband Rig Connectivity:** Upgrading remote rigs with high-throughput satellite terminals and industrial IoT edge gateways.
- **Enterprise System Interoperability:** Integrating real-time drilling streams with OIL's SAP ERP, GIS subsurface databases, and asset management platforms under the **Project DRIVE 2.0** digitalization master plan.

`[VERIFIED: BSE India Regulatory Filings 2024-25; OIL Digital Footprint Portal]`

---

## 4. What eRTMAC Does NOT Do (The Critical Functional Gap)

Despite its advanced surveillance capabilities, eRTMAC possesses major structural blind spots that explain why Problem Statement 26121 was created:

| Capability | eRTMAC Current State | NWIS Proposed Capability | Gap Impact |
| :--- | :--- | :--- | :--- |
| **Real-Time Data Telemetry** | `[VERIFIED]` Streams live WOB, Torque, SPP, Flow, ROP. | Consumes eRTMAC live streams via API/WITSML. | eRTMAC excels here; NWIS reuses this feed. |
| **Unstructured Document Ingestion** | `[DOES NOT EXIST]` Cannot read or parse unstructured PDFs, DDRs, WCRs. | `[CORE NWIS]` AI/NLP/OCR pipeline extracts structured facts from text and scanned PDFs. | Historical knowledge remains trapped in PDF archives. |
| **Offset Well Relevance Ranking** | `[DOES NOT EXIST]` Wells are static records; no dynamic offset ranking algorithm. | `[CORE NWIS]` Multi-parameter ranking (distance, formation, trajectory, hazard history). | Engineers manually guess which offsets are relevant. |
| **Dynamic Interval Correlation** | `[DOES NOT EXIST]` Does not dynamically align active depth to offset geological intervals. | `[CORE NWIS]` Stratigraphic and depth-matching correlation engine (TVDSS/formation). | Fails to recognize that 3,200m in Well A matches 3,240m in Well B. |
| **Historical Risk Corridors** | `[DOES NOT EXIST]` Displays only active well depth; no projection of offset hazards. | `[CORE NWIS]` Renders approaching hazard zones 20–50m ahead of the active bit. | Rigs enter known loss/stuck-pipe zones without warning. |
| **Proactive Lead-Time Warnings** | `[REACTIVE ONLY]` Alarms trigger *after* a parameter spikes (e.g. pit gain alarm). | `[PROACTIVE]` Early warning triggers *before* the bit penetrates the dangerous formation. | Eliminates avoidable reactive emergencies. |
| **Evidence-Backed Mitigation** | `[DOES NOT EXIST]` No linkage between alarms and historical remedial actions. | `[CORE NWIS]` Displays exact historical mitigation with clickable original document page citations. | Engineers must guess remedial action under extreme time pressure. |

---

## 5. Architectural Relationship: NWIS "Alongside" eRTMAC

The Problem Statement specifically defines NWIS as:
> *"an AI/ML-enabled Nearby Wells Intelligence System (NWIS) that acts as a standalone decision-support platform alongside eRTMAC that has institutional memory."*

This phrasing is deliberate and architecturally vital:
- **NWIS does NOT replace eRTMAC:** eRTMAC remains the primary real-time operational telemetry and rig surveillance command platform.
- **NWIS acts as the "Cerebral Cortex / Institutional Memory":** It listens to eRTMAC's active well telemetry (Well ID, Bit Depth, Formation Top, Sensor Values) and injects contextual historical intelligence, offset precedents, and proactive risk corridors back to the eRTMAC dashboard and rig-site supervisors.

```
┌────────────────────────────────────────────────────────┐
│             OIL eRTMAC Command Centre                  │
│  (Real-Time Rig Telemetry, High-Speed Sensor Curves)   │
└──────────────────────────┬─────────────────────────────┘
                           │ Active Well State:
                           │ (Well X, Depth: 3,220m, Formation: Barail)
                           ▼
┌────────────────────────────────────────────────────────┐
│                  eRTMAC-NWIS Platform                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Institutional Memory Engine                      │  │
│  │ (DDR/WCR AI-Extracted Knowledge Base)            │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Dynamic Offset Relevance & Interval Aligner      │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Multi-Hazard Predictive Risk Models              │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Proactive Early Warning & Evidence Audit Engine  │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │ Proactive Risk Corridor +
                           │ Evidence-Backed Mitigation
                           ▼
┌────────────────────────────────────────────────────────┐
│    Unified Decision Console (Field & Command Center)   │
│  "Approaching Barail Loss Zone in 18 m (Offset W-03)   │
│   Mitigation: Pre-treat mud with 30 kg/m³ LCM pill"     │
└────────────────────────────────────────────────────────┘
```
