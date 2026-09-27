# SIH 26121 — ONGC: Digital Drilling Stack Deep Audit

## 1. Executive Summary & Strategic Importance
Oil and Natural Gas Corporation Limited (ONGC) is India's largest national oil company, producing roughly 70% of domestic crude. As an operator drilling hundreds of onshore and offshore wells annually, ONGC has built the most sophisticated public-sector digital drilling ecosystem in South Asia. 

Auditing ONGC's digital drilling architecture is mandatory: it provides the direct national benchmark against which Oil India Limited's **eRTMAC-NWIS** must be evaluated.

---

## 2. Component 1: RTDOC (Real Time Drilling Operations Centre)
- **Facility Location:** Institute of Drilling Technology (IDT), Dehradun, Uttarakhand, India.
- **Operational Role:** Centralized 24/7 command, surveillance, and operational advisory center for ONGC rigs across all offshore (Mumbai High, KG Basin) and onshore (Cambay, Assam, Cauvery, Rajahmundry) assets.
- **Capabilities:**
  1. *Real-Time Telemetry Consolidation:* Ingests surface and downhole MWD/LWD sensor streams from dozens of rigs concurrently.
  2. *Multidisciplinary Subject Matter Expert (SME) Support:* Staffed by senior drillers, geomechanicians, and directional specialists providing remote guidance during complex operations.
  3. *Phase-II Expansion:* ONGC has recently undertaken the Phase-II modernization of RTDOC to incorporate cloud computing, enhanced edge-connectivity, and automated predictive analytics.

`[VERIFIED: DGH Urjavarta Portal; ONGC Technical Bulletins; Public Tenders]`

---

## 3. Component 2: WIS (Well Information System) — GenAI Modernization
- **Launch Date:** Formally introduced in its **Generative AI-powered iteration in December 2024**.
- **System Purpose:** Enterprise-grade central repository and daily drilling reporting platform for all drilling and workover rigs.
- **Core Capabilities:**
  1. *Digital Daily Drilling Reporting (DDR):* Replaces manual paper tour sheets with structured digital data entry across all field operations.
  2. *Generative AI Search & Ingestion:* Employs GenAI models to process, structure, and query daily operational narratives, equipment maintenance logs, and well event tallies.
  3. *Performance Benchmarking:* Provides automated Rate of Penetration (ROP), tripping speed, and bit dull grading analytics.

`[VERIFIED: BSE/NSE Regulatory Disclosures; Bureaucrats India Official Release Dec 2024]`

---

## 4. Component 3: DWP (Digital Well Program)
- **Partner / Platform:** Built in strategic partnership with global software suites (Halliburton Landmark DecisionSpace 365 Digital Well Program).
- **Core Capabilities:**
  1. *Unified Well Planning:* Integrates trajectory design, geomechanics, casing design, mud planning, and cementing into a single collaborative cloud environment.
  2. *Automated Rule Validation:* Flags casing burst/collapse limits, kick tolerances, and torque/drag friction factors in real time during the planning phase.
  3. *Direct Execution Link:* Automatically exports the approved Digital Well Program to the rig floor and RTDOC, eliminating discrepancies between pre-drill design and rig execution.

`[VERIFIED: ONGC Annual Reports; Halliburton Digital Well Program Disclosures]`

---

## 5. Component 4: DBA (Drilling Belief Analytics)
- **System Classification:** Edge-based probabilistic analytics platform deployed directly on the rig floor.
- **Field Deployments & Trials:** Successfully trialed on active onshore wells in **Rajahmundry Asset (Andhra Pradesh)** and **Sivasagar / Assam Asset (Upper Assam Basin)**.
- **Algorithmic Approach:** Uses Bayesian probabilistic networks and sensor anomaly detection to calculate dynamic "belief states" for developing drilling complications.
- **Target Complications:**
  1. *Stuck Pipe:* Precursor detection based on hook load overpull trends and torque variance.
  2. *Stick-Slip & Torsional Vibration:* Real-time surface torque frequency oscillation tracking.
  3. *Abnormal Formation Pressure / Kick:* Standpipe pressure and flowline temperature deviation analysis.
  4. *Bit Balling:* ROP degradation combined with mechanical specific energy (MSE) spikes in reactive shales.

`[VERIFIED: National Stock Exchange (NSE) Regulatory Disclosures; ONGC Technology Papers]`

---

## 6. Component 5: Project DRISHTI & TATHYA.AI (Internal AI Innovations)

Under ONGC's internal innovation accelerator and hackathon initiatives (**Project Udbhav 1.0 & 2.0**), two specialized drilling AI solutions have been developed:

### 1. DRISHTI (Real-Time Stuck-Pipe Risk Intelligence)
- Real-time ML model analyzing streaming sensor data at 1 Hz.
- Predicts differential and mechanical stuck-pipe risks before pipe seizure occurs.
- Generates early warning risk scores and features a conversational AI engineering copilot for rig supervisors.

### 2. TATHYA.AI (Legacy Well Document Intelligence)
- Purpose-built to solve the historical institutional memory crisis across ONGC's 60-year archive.
- Utilizes custom OCR and multi-modal models to ingest scanned, faded, and handwritten well logs, mud reports, and DDRs.
- Automatically extracts and verifies stratigraphic markers, casing seats, and reservoir test data, converting static paper into queryable subsurface intelligence.

`[VERIFIED: ONGC Udbhav Innovation Disclosures; Samudra Manthan Technology Briefs]`

---

## 7. Comparative Architectural Matrix: ONGC Stack vs. OIL Stack vs. NWIS

The table below positions the ONGC ecosystem against Oil India's current baseline and highlights exactly where NWIS fits:

| Capability Domain | ONGC Deployed Platform | OIL Current Platform | NWIS Proposed Contribution to OIL |
| :--- | :--- | :--- | :--- |
| **Real-Time Surveillance** | RTDOC (IDT Dehradun) | eRTMAC (Duliajan) | Integrates with eRTMAC; consumes live stream. |
| **Well Planning Suite** | Digital Well Program (DWP) | Landmark Well Plan | Ingests planned trajectory to project risk corridors. |
| **Structured Daily Reporting** | WIS (GenAI Enabled - Dec 2024) | SAP ERP / Tour Sheets | Ingests daily DDR records into memory engine. |
| **Edge Hazard Alerts** | DBA (Drilling Belief Analytics) | High-threshold eRTMAC alarms | Provides multi-hazard ML risk models (5 families). |
| **Legacy Document Parsing** | TATHYA.AI | Manual file searching | AI/OCR/NLP pipeline for OIL's DDR/WCR archives. |
| **Offset Interval Alignment** | Manual Geologist Correlation | Manual Geologist Correlation | **Automated Dynamic Stratigraphic Correlation**. |
| **Proactive Risk Corridor** | In-development (DRISHTI) | None | **Core Signature Feature of NWIS**. |

---

## 8. Critical Insight for SIH 26121

ONGC's extensive digital drilling portfolio proves conclusively that:
1. **The problem of drilling hazard prediction and document intelligence is not theoretical in India.** The nation's largest upstream operator is actively investing hundreds of crores into solving it.
2. **Oil India Limited's PS 26121 is strategically targeted:** OIL does not need to duplicate ONGC's entire multi-platform infrastructure. Instead, **NWIS acts as the focused integration bridge**, combining the capabilities of what ONGC split across WIS, DBA, DRISHTI, and TATHYA.AI into a single, cohesive decision-support platform designed specifically for OIL's eRTMAC environment.
