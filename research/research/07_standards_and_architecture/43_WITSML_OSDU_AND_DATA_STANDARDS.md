# SIH 26121 — Upstream Data Standards: WITSML, OSDU, PPDM & LAS

## 1. Executive Summary
This document audits the global data interchange standards governing wellsite telemetry, subsurface logs, and master E&P records: **WITSML** (Energistics), **OSDU** (The Open Group), **PPDM**, and **LAS** (CWLS). It evaluates their operational adoption within Oil India Limited and establishes the data schema mapping strategy for the NWIS platform.

---

## 2. Standards Taxonomy & Industry Roles

```
[UPSTREAM DATA STANDARDS HIERARCHY]
├── REAL-TIME RIG TELEMETRY & DRILLING OBJECTS
│   ├── WITS Level 0 (Serial / TCP/IP binary stream, 1980s legacy, 1-second cadence)
│   └── Energistics WITSML (XML / JSON schema, v1.4.1.1 & v2.0, standard for eRTMAC)
│
├── ENTERPRISE CLOUD DATA PLATFORM
│   └── The Open Group OSDU Forum (Cloud-native unified subsurface data platform)
│
├── RELATIONAL PETROLEUM MASTER DATA MODEL
│   └── PPDM Association (PPDM 3.9 relational schema for E&P assets)
│
└── WIRELINE & LWD PETROPHYSICAL CURVES
    ├── LAS 2.0 / 3.0 (Log ASCII Standard, Canadian Well Logging Society)
    └── DLIS / LIS (Digital Log Interchange Standard, binary curve archive)
```

---

## 3. Deep Dive: Energistics WITSML (Wellsite Information Transfer Standard ML)
- **Governing Body:** Energistics Consortium (now part of The Open Group).
- **Dominant Versions:**
  - *WITSML v1.4.1.1:* The global industry workhorse. XML-based over SOAP/HTTP. Standard protocol used by Oil India's eRTMAC and mud logging contractors.
  - *WITSML v2.0 / v2.1:* Modern JSON/WebSocket specification with Energistics Transfer Protocol (ETP) for high-speed streaming.
- **Core WITSML Objects Relevant to NWIS:**
  1. `well` & `wellbore`: Master wellhead coordinates, operator, field name, elevation datums.
  2. `trajectory`: Station surveys (MD, Inclination, Azimuth, TVD, DLS).
  3. `log`: Continuous depth-indexed or time-indexed sensor curves (GR, ROP, WOB, Torque).
  4. `mudLog`: Gas chromatography, cuttings lithology descriptions, drilling remarks.
  5. `opsReport`: Daily operational activity summaries, pump parameters, weather, casing tally.
  6. `risk`: Standardized hazard registry documenting loss zones, kicks, and stuck-pipe events.

`[VERIFIED: Energistics Official Documentation: https://docs.energistics.org]`

---

## 4. Deep Dive: The Open Group OSDU Data Platform
- **Governing Body:** The Open Group OSDU Forum (Consortium of 200+ operators including Shell, BP, ExxonMobil, Chevron, SLB, Microsoft, AWS, Google Cloud).
- **Core Architecture:** Open-source cloud data platform defining standardized JSON schemas for subsurface data:
  - *Master Data:* `master-data--Well`, `master-data--Wellbore`.
  - *Work Product Components:* `work-product-component--WellLog`, `work-product-component--WellboreTrajectory`.
  - *Reference Data:* Standardized dictionaries for lithology, units of measure, and coordinate reference systems.
- **Relevance to NWIS:** Adopting OSDU naming conventions (e.g. `WellboreTrajectory`, `FormationMarker`) ensures NWIS is architecturally compatible with emerging national cloud platforms in India.

---

## 5. Log ASCII Standard (LAS 2.0 / 3.0)
- **Governing Body:** Canadian Well Logging Society (CWLS).
- **Format Structure:** ASCII text files containing structured sections:
  - `~VERSION`: Version and wrap mode.
  - `~WELL`: Well name, field, location coordinates, start and stop depths.
  - `~CURVE`: Curve mnemonic headers and units (`DEPT`, `GR`, `RES`, `RHOB`, `NPHI`).
  - `~A`: Ascii numerical log data matrix.
- **Role in NWIS:** Standard format used for storing continuous Gamma Ray and petrophysical logs used in stratigraphic cross-well correlation.

---

## 6. Practical Implementation Strategy for SIH Prototype

| Operational Reality | What to Implement in NWIS | What to Avoid (Overengineering) |
| :--- | :--- | :--- |
| **OIL eRTMAC uses WITS / WITSML 1.4.1.1** | Implement a lightweight Python WITSML XML parser and WebSocket streamer. | Do NOT build a full enterprise WITSML commercial server. |
| **DDR/WCR archives are stored as PDFs** | Ingest PDFs via OCR/NLP and map extracted entities to WITSML `opsReport` and `risk` schemas. | Do NOT require users to manually re-enter data into WITSML XML editors. |
| **OSDU is the global enterprise trend** | Align internal PostgreSQL schemas with OSDU JSON entity property names. | Do NOT attempt to install a massive 50-node OSDU AWS/Azure cluster for an SIH hackathon. |
