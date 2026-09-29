# SIH 26121 — Peloton WellView: Deep Prior-Art & Architectural Audit

## 1. Executive Summary & Corporate Stance
- **Company Name:** Peloton Computer Enterprises Ltd. (Calgary, Canada / Houston, Texas)
- **Market Position:** Dominant independent software vendor for well lifecycle data management, accounting for thousands of energy operators globally.
- **Flagship Digital Platform:** **WellView®** (Complete Well Lifecycle Data Management Software).
- **Primary Domain Focus:** Master data management for drilling, completions, well servicing, and abandonment.

---

## 2. Deep Dive: Peloton WellView Capabilities

Peloton's **WellView** serves as an operator's centralized system of record for the physical and operational life of every well in an asset:

```
[PELOTON WELLVIEW DATA MODEL & ARCHITECTURE]
Field Data Capture (Drilling Tour Sheets, Completion Reports, Workover Logs)
       │
       ▼
WellView Standardized Relational Schema (Peloton Master Data Platform)
       ├── Complete Well History (Spud date, TD, casing strings, perforations)
       ├── Detailed Daily Operations Logs (Time-breakdown per activity code)
       ├── Wellbore Schematics (Automated 2D graphical completion diagrams)
       └── Standardized Lessons-Learned Database (Categorized manual entries)
       │
       ▼
Enterprise Reporting & Historical Benchmarking
       ├── Trend Analysis & Multi-Well Performance Benchmarking
       ├── Regulatory Compliance Reporting (DGH / State regulatory exports)
       └── Upstream Integration with WITSML Stores and Subsurface Suites
```

### Forensic Capability Assessment:
- **What Problem Does It Solve?** Eliminates data silos across departments by providing a single authoritative master database for every well from initial permitting to permanent abandonment.
- **Lessons-Learned Tracking:** WellView includes dedicated modules for recording post-well lessons learned and engineering recommendations.
- **Data Capture Mechanism:** Relies entirely on **structured manual form entry** by rig clerks, drilling engineers, and completion supervisors.
- **Schematic Visualization:** Generates detailed, millimeter-accurate 2D mechanical wellbore schematics showing casing shoes, liners, packers, tubing, and perforations.

`[VERIFIED: Peloton WellView Portal: https://www.peloton.com/products/well-data-lifecycle/wellview; Peloton Drilling Use Case: https://www.peloton.com/peloton-use-case-drilling-completions-management]`

---

## 3. Reverse-Engineering Forensic Questionnaire: Peloton WellView

| Technical & Operational Question | Peloton Capability Status | Detailed Engineering Reality |
| :--- | :---: | :--- |
| **Does it maintain decades of historical well records?** | **YES** | Core business function of WellView. |
| **Does it track drilling events, casing seats, and NPT?** | **YES** | Industry-standard relational data model for well operations. |
| **Does it automatically ingest unstructured scanned PDFs via AI?** | **NO** | Requires manual or API-driven structured data entry; no native OCR/NLP pipeline for legacy paper records. |
| **Does it dynamically correlate active drilling depths to offset intervals?** | **NO** | Users can view historical well reports side-by-side, but it lacks a dynamic stratigraphic correlation engine. |
| **Does it run real-time predictive ML models for stuck pipe or kicks?** | **NO** | Strictly a data management and reporting system; does not execute high-frequency predictive telemetry analytics. |
| **Does it display live "Historical Risk Corridors" ahead of the bit?** | **NO** | Not designed for live real-time rig surveillance. |

---

## 4. Conclusions for SIH 26121

1. **WellView is a Foundational Data Source, Not a Direct NWIS Competitor:** In a mature enterprise deployment, NWIS would sit *above* a system like WellView or SAP, extracting structured well histories via API while augmenting it with AI document intelligence for unindexed reports.
2. **The Manual Burden of Structured Systems:** Systems like WellView fail on legacy archives because operators cannot afford the millions of dollars required to hire data entry clerks to manually type 40 years of paper records into structured software forms.
3. **The NWIS Solution:** By using AI, OCR, and multimodal LLMs, NWIS automates this extraction at a fraction of the time and cost, converting raw PDF archives into structured entities automatically.
