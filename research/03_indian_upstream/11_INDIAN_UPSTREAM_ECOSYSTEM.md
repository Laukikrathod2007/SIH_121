# SIH 26121 — The Indian Upstream Exploration & Production (E&P) Ecosystem

## 1. Executive Summary
This document provides a comprehensive structural mapping of the Indian upstream oil and gas sector, detailing the governmental ministries, regulatory authorities, national oil companies (NOCs), private operators, safety mandates, and data repositories governing drilling operations across the country.

---

## 2. Institutional & Regulatory Governance Hierarchy

The Indian upstream sector operates under a centralized constitutional and statutory framework administered by the Government of India:

```
[MINISTRY OF PETROLEUM & NATURAL GAS (MoPNG)]
Executive policy, PSU administrative oversight, resource allocation
       │
       ├── [DIRECTORATE GENERAL OF HYDROCARBONS (DGH)]
       │   ├── Technical upstream regulator (Upstream E&P oversight)
       │   ├── National Data Repository (NDR) custodian
       │   ├── Open Acreage Licensing Policy (OALP) & HELP bid manager
       │   └── Production Sharing Contract (PSC) & Revenue Sharing Contract (RSC) monitor
       │
       ├── [OIL INDUSTRY SAFETY DIRECTORATE (OISD)]
       │   ├── Statutory safety regulator for upstream, midstream, downstream
       │   ├── Formulates technical safety standards (OISD-STD-106, 174, 187, etc.)
       │   └── Safety audits, blowout investigations, disaster prevention mandates
       │
       └── [PUBLIC SECTOR UPSTREAM OPERATORS (NOCs)]
           ├── Oil and Natural Gas Corporation Limited (ONGC) — Maharatna CPSE
           └── Oil India Limited (OIL) — Maharatna CPSE
```

`[VERIFIED: MoPNG Official Portal; DGH Annual Report 2023-24; OISD Standards Portal]`

---

## 3. Major Upstream E&P Operators in India

The Indian domestic hydrocarbon production landscape is dominated by two national oil companies and one major private conglomerate:

| Operator | Ownership Type | Primary Operational Basins | Domestic Crude Production Share | Digital / Real-Time Operations Infrastructure |
| :--- | :--- | :--- | :--- | :--- |
| **ONGC (Oil and Natural Gas Corporation)** | Central PSU (Maharatna) | Mumbai Offshore, Cambay, KG Offshore, Cauvery, Assam Shelf, Tripura | ~65–70% | **RTDOC** (Dehradun), **WIS** (GenAI reporting), **Digital Well Program (DWP)**, **DBA** (edge alerts). |
| **Oil India Limited (OIL)** | Central PSU (Maharatna) | Upper Assam Shelf, Arunachal Thrust, Rajasthan, Mahanadi, Andaman | ~9–11% | **eRTMAC 1.0 / 2.0** (Duliajan), Landmark Well Plan, Project DRIVE 2.0. |
| **Cairn Oil & Gas (Vedanta Ltd.)** | Private Indian Conglomerate | Barmer (Rajasthan), Cambay (Gujarat), Ravva (KG Basin) | ~20–25% | **Project Nirmaan**, PetroTechnical Cloud, SLB-Cognite digital alliance. |
| **Reliance Industries (RIL) / bp** | Private / International JV | KG-D6 Deepwater (Mahanadi / KG Basin) | Major Deepwater Gas | Ultra-deepwater subsea command and control digital infrastructure. |
| **Other PSUs (IOCL, BPCL, HPCL)** | Central PSUs (Maharatna) | Participating interests through BPRL, IndOil Global, Prize Petroleum | Equity crude / Non-operator | Primarily financial/joint venture partner oversight. |

`[VERIFIED: MoPNG Monthly Petroleum Statistics; DGH Hydrocarbon Outlook]`

---

## 4. OISD Standards Governing Drilling Operations

The Oil Industry Safety Directorate (OISD) issues legally binding safety and operating standards that directly dictate drilling engineering practices, well integrity, and risk protocols:

- **OISD-STD-106 (Wellhead & Well Control Equipment):** Mandates BOP ratings, choke and kill manifold testing, accumulator closing time limits, and kick detection procedures.
- **OISD-STD-174 (Well Servicing and Workover Operations):** Covers well integrity verification, casing pressure testing, and barrier management.
- **OISD-STD-187 (Drilling Rigs Safety & Maintenance):** Governs surface sensor calibration, pit volume totalizers (PVT), flow sensors, and alarm thresholds.
- **OISD-GDN-206 (Safe Drilling Practices in Abnormal Pressure Formations):** Specifically governs pore pressure estimation, mud weight margin maintenance, and casing seat depth selection in high-risk overpressured horizons (e.g. Upper Assam and Krishna-Godavari basins).

`[VERIFIED: OISD Standards Repository: https://oisd.gov.in/oisd-standards]`

---

## 5. Strategic Context for Problem Statement 26121

1. **National Energy Security Context:** India imports over **85% of its crude oil requirements**. Under the government's *Aatmanirbhar Bharat* and energy security mandates, MoPNG has directed ONGC and OIL to accelerate domestic drilling under the *Samudra Manthan* and Mission 4+ campaigns.
2. **Cost of Inefficiency:** In complex Indian basins, drilling complications (stuck pipe, kicks, lost circulation) cost Indian PSUs hundreds of crores annually in Non-Productive Time (NPT).
3. **Cross-Operator Digital Acceleration:** Both ONGC and Cairn have made massive digital leaps (ONGC's RTDOC/WIS/DBA and Cairn's Nirmaan). Oil India's initiation of PS 26121 for eRTMAC-NWIS represents a deliberate, strategic initiative to close the historical knowledge gap and equip its engineers with state-of-the-art AI-driven decision support.
