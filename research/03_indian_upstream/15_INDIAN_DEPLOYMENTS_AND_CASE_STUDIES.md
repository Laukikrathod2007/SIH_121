# SIH 26121 — Indian Deployments, Field Trials & Case Studies

## 1. Executive Summary
This document investigates documented, independently verified digital drilling deployments, field trials, and operator case studies across India. It strictly enforces the distinction between global marketing claims and verified Indian field installations.

---

## 2. Verified Field Deployments & Case Studies in India

### Case Study 1: ONGC Drilling Belief Analytics (DBA) Field Trials
- **Operator:** Oil and Natural Gas Corporation Limited (ONGC).
- **Location:** Onshore drilling locations in **Rajahmundry Asset** (Krishna-Godavari Onshore Basin, Andhra Pradesh) and **Sivasagar / Assam Asset** (Upper Assam Basin).
- **Technology:** Edge-based Bayesian belief network running at the rig site.
- **Operational Challenge:** High incidence of mechanical stuck pipe and severe stick-slip in complex tectonic formations.
- **Demonstrated Results:** The system ingested surface drilling parameters and successfully alerted drillers to impending stuck pipe conditions and abnormal formation pressures before mechanical lock occurred.
- **Classification:** `[VERIFIED: ONGC Regulatory Disclosures & Technical Bulletins]`.

---

### Case Study 2: ONGC Generative AI-Powered Well Information System (WIS)
- **Operator:** ONGC.
- **Deployment Scope:** Enterprise-wide rollout across all ONGC-operated drilling and workover rigs nationwide.
- **Launch Date:** Formally introduced in December 2024.
- **Operational Challenge:** Manual, error-prone Daily Drilling Reporting (DDR) creating fragmented historical records and delayed management reporting.
- **Demonstrated Results:** Accelerated daily operational report capture, automated data validation, and enabled conversational natural-language querying of historical drilling records for office and field personnel.
- **Classification:** `[VERIFIED: Public Announcements & Regulatory Filings 2024-25]`.

---

### Case Study 3: Cairn Oil & Gas — SLB & Cognite Enterprise Digitalization
- **Operator:** Cairn Oil & Gas (Vedanta Limited).
- **Location:** Barmer Basin, Rajasthan (Mangala, Bhagyam, Aishwarya field complexes).
- **Technology:** Cognite Data Fusion (CDF) deployed in partnership with SLB.
- **Operational Challenge:** Managing over 1,000 closely spaced wells with massive subsurface, drilling, and production sensor data trapped in vendor silos.
- **Demonstrated Results:** Ingested and contextualized multi-vendor sensor data, schematics, and operational logs into a unified industrial data model, facilitating cross-functional collaboration and predictive production/drilling workflows.
- **Classification:** `[VERIFIED: Official Cognite Customer Release & Industry Coverage]`.

---

### Case Study 4: Oil India Limited — Real-Time Remote Surveillance (eRTMAC)
- **Operator:** Oil India Limited (OIL).
- **Location:** Remote command center in Duliajan, monitoring drilling in **Andaman Deepwater Offshore**, **Jodhpur (Rajasthan)**, and **Upper Assam**.
- **Technology:** eRTMAC real-time data streaming suite paired with Landmark (Halliburton) **Well Plan**.
- **Operational Challenge:** Deep frontier exploration wells in ultra-deepwater and high-temperature environments with extremely narrow drilling margins between pore pressure and fracture gradient.
- **Demonstrated Results:** 24/7 continuous surveillance of standpipe pressure, pit volumes, and ECD enabled proactive detection of kicks and losses, safeguarding deep exploration operations.
- **Classification:** `[VERIFIED: OIL Annual Report 2024-25]`.

---

## 3. The 5-Level Market Penetration Spectrum

To eliminate ambiguity regarding software maturity in India, all solutions audited in this research are placed on a 5-level operational spectrum:

```
[LEVEL 1: GLOBAL PRODUCT ONLY]
Product exists globally; zero documented evidence of Indian marketing or customer engagement.

[LEVEL 2: INDIAN MARKET PRESENCE]
Vendor has an Indian subsidiary or sales office; actively markets to Indian operators (e.g. SLB, Baker Hughes, Halliburton).

[LEVEL 3: INDIAN CUSTOMER CONTRACT]
Indian operator has licensed software tools from the vendor (e.g. OIL licenses Landmark Well Plan from Halliburton).

[LEVEL 4: AUDITED INDIAN DEPLOYMENT]
Software is installed, actively running, and validated in an Indian drilling asset (e.g. ONGC RTDOC, Cairn CDF, ONGC DBA).

[LEVEL 5: OIL PRODUCTION DEPLOYMENT]
Software is actively running in live operational drilling inside Oil India Limited.
```

---

## 4. Multi-Vendor Classification on the Indian Spectrum

| Technology / System | Primary Vendor / Creator | Classification on Indian Spectrum | Evidentiary Basis |
| :--- | :--- | :--- | :--- |
| **Landmark Well Plan** | Halliburton | **Level 5: OIL Production Deployment** | Verified in OIL Annual Report 2024-25. |
| **eRTMAC 1.0** | In-house / Contractor | **Level 5: OIL Production Deployment** | Verified in OIL Tender CDH6605P21. |
| **RTDOC Center** | ONGC / Wipro / Partners | **Level 4: Audited Indian Deployment** | Verified at IDT Dehradun. |
| **Drilling Belief Analytics (DBA)** | ONGC | **Level 4: Audited Indian Deployment** | Verified trials in Rajahmundry & Sivasagar. |
| **Cognite Data Fusion** | Cognite / SLB | **Level 4: Audited Indian Deployment** | Verified deployment at Cairn (Barmer). |
| **SLB DrillPlan** | SLB | **Level 3: Indian Customer Contract** | Utilized by private/PSU operators for well planning. |
| **Baker Hughes JewelSuite DHP** | Baker Hughes | **Level 3: Indian Customer Contract** | Marketed and deployed in regional engineering offices. |
| **SLB Tela Offset Wells** | SLB | **Level 2: Indian Market Presence** | Global release (2024); marketed in India; no public PSU contract verified. |
| **Nergyflux DrillSense™** | Nergyflux (Indian Startup) | **Level 2: Indian Market Presence** | Indian corporate incorporation; commercial marketing active. |
| **Parallel Minds WellSynth AI** | Parallel Minds (Indian) | **Level 2: Indian Market Presence** | Commercial marketing and independent operator case studies. |
| **eRTMAC-NWIS** | Proposed SIH Platform | **Target: Level 5 Deployment at OIL** | Solves the unaddressed historical intelligence gap. |
