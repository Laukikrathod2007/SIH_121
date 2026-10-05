# SIH 26121 — Oil India Limited: Drilling Data Systems & Asset Workflows

## 1. Executive Summary
This document investigates the physical and digital pipelines through which drilling data flows within Oil India Limited—from downhole sensors and surface Mud Logging Units (MLUs) to corporate archives and eRTMAC servers. It establishes the exact data types, transmission protocols, document formats, and data quality constraints that the NWIS platform must ingest and process.

---

## 2. Mud Logging Units (MLU) & Rig Instrumentation

At OIL drilling locations, surface data acquisition is contracted to specialized Mud Logging Service providers.
- **2026 Operational Scale:** In early 2026, OIL issued a major tender for **"12 Regular + 4 Call-out Mud Logging Units (MLUs) and Real-Time Monitoring Systems"** for onshore drilling wells in Assam and Arunachal Pradesh. `[VERIFIED: OIL Tender Portal 2026]`
- **MLU Responsibilities at Rigsite:**
  1. *Gas Chromatography:* Continuous extraction and analysis of hydrocarbon gases (Total Gas, C1 Methane, C2 Ethane, C3 Propane, iC4/nC4 Butanes, iC5/nC5 Pentanes) from return drilling mud.
  2. *Lithological Cutting Evaluation:* Microscopic examination of rock cuttings caught on shale shakers every 2 to 5 meters to describe rock type, porosity, fluorescence, and oil cut.
  3. *Surface Drilling Parameter Acquisition:* Hook load, rotary torque, top drive RPM, standpipe pressure, casing pressure, mud pump strokes, flowline temperature, and pit levels.
  4. *Real-Time Telemetry Streaming:* Encoding rig data into standardized **WITS Level 0** serial streams or **WITSML 1.4.1.1** XML packets and transmitting them via VSAT/cellular uplinks to eRTMAC.

---

## 3. Inventory of Operational Drilling Data Assets in OIL

The Problem Statement (§Relevant Data Availability) lists nine primary data categories available within OIL. The table below classifies their digital formats, storage locations, update frequencies, and ingestion complexity:

| Data Asset Category | Typical Format in OIL | Physical Storage Location | Generation Frequency | Ingestion & Structuring Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **1. Well Completion Reports (WCR)** | Digital PDF / Scanned PDF (50–250 pages) | Shared Network Drives, Document Management Archives | One report per well at conclusion (TD) | High: Unstructured multi-page PDFs with embedded tables, logs, and free text. |
| **2. Daily Drilling Reports (DDR)** | Digital PDF, Word, Excel, Rig Tour Sheets | SAP ERP, Rig Local Disks, Email Attachments | Daily (every 24 hours per active rig) | High: Semi-structured forms with daily operational narratives and irregular abbreviations. |
| **3. Mud Logging Strip Charts & Logs** | Scanned TIF / PDF, ASCII Well Logs, LAS 2.0 | Geological Archives, MLU Contractor Servers | Continuous per bit run (depth-indexed) | Medium: Requires OCR for header metadata and vector digitization for curves. |
| **4. Real-Time Telemetry Streams** | WITSML XML, WITS0 Serial, CSV dumps | eRTMAC Streaming Server, Time-Series DB | High frequency (1 to 5 seconds) | Low: Highly structured time-series data. |
| **5. Directional Surveys & Trajectories** | Excel, ASCII, PDF Run Reports, WITSML | Landmark COMPASS, Survey Contractor Files | Station surveys taken every 30m / 90m pipe stand | Low to Medium: Tabular MD, Inclination, Azimuth records. |
| **6. Casing & Cementing Records** | Scanned Tallies, Job Summaries in WCRs | Well Files, Cementing Contractor Folders | At conclusion of each hole section | Medium: Tabular casing weights, grades, slurry densities, and displacement pressures. |
| **7. Mud Program & Daily Mud Reports** | PDF / Excel Sheets authored by Mud Engineer | Rig site binders, Chemical Department archives | Daily mud check (Viscosity, PV, YP, Gel, Mud Weight) | Medium: Structured tabular fluid properties. |
| **8. Historical Event & NPT Records** | Free-text narrative sections in DDRs/WCRs | Embedded within 24-hr DDR operational text | Intermittent (occurs during complications) | High: Requires NLP entity extraction to classify kicks, losses, stuck pipe, and fishing runs. |
| **9. Subsurface G&G Stratigraphic Tops** | Petrel Project Files, Geological Marker Sheets | G&G Department Database, Master Well Files | Pre-drill prognosed; updated post-drill | Medium: Tabular formation top depths (MD/TVDSS). |

---

## 4. The Data Lifecycle & Knowledge Degradation Path

The flowchart below traces how data originates in pristine digital form on the rig floor and systematically degrades into inaccessible static documents over time:

```
[DAY 0: RIG FLOOR EXECUTION]
Rig Sensors & MLU generate pristine 1-second digital WITSML data.
       │
       ▼
[DAY 1: DAILY REPORTING]
Drilling Supervisor condenses 24 hours of sensor data into a 2-page text DDR (PDF/Word).
Granular sensor nuances are collapsed into qualitative summaries.
       │
       ▼
[DAY 60: WELL CONCLUSION]
Drilling team and geologist author the Well Completion Report (WCR).
Key events summarized; detailed daily logs relegated to paper archives or unindexed folders.
       │
       ▼
[YEAR 1+: ARCHIVAL AMNESIA]
WCRs converted to flattened PDFs or paper binders in archive rooms.
OCR indexing is nonexistent or poor.
Engineering knowledge can only be recovered by someone who knows the exact well name.
```

---

## 5. Real-World Data Quality Challenges in OIL Archives

Any practical software prototype or production system designed for OIL must be resilient against several severe real-world data quality defects:

1. **Scanned Artifacts & Skewed Text:** Many legacy Upper Assam wells drilled in the 1980s, 1990s, and 2000s exist only as scanned photocopies. Pages exhibit rotational skew, smudges, carbon-copy fading, and handwritten marginal notes.
2. **Abbreviation Proliferation in DDR Narratives:** Drilling supervisors use extreme operational shorthand:
   - *"POOH f/ 3240m w/ BHA#4 due to prs drop. Obs tite hole @ 3110m. Reamed f/ 3110-3150m. Recov 15 bbls cavings over shaker."*
   - Standard commercial NLP models trained on Wikipedia or legal text fail completely on oilfield jargon. NWIS requires domain-specific dictionary tokenization.
3. **Inconsistent Naming of Stratigraphic Horizons:** The same formation may be referred to interchangeably in different reports as:
   - *"Barail Coal-Shale"*, *"BCS"*, *"Barail Sand"*, *"BS-1"*, or *"Upper Barail"*.
   - NWIS must maintain a standardized stratigraphic ontology mapping aliases to formal lithostratigraphic units.
4. **Discrepancy Between Prognosed and Actual Tops:** Geological prognosis sheets predict formation tops at planned depths (e.g. Kopili at 3,350 m TVDSS), but structural dip or faulting may cause the actual top to be encountered at 3,382 m TVDSS. NWIS correlation algorithms must reference **actual mud-log and LWD-verified tops**, not pre-drill estimates.
5. **Missing or Incomplete Telemetry Channels:** Historical wells may lack continuous torque or flow-out sensors, having only ROP and mud weight recorded. The predictive engine must support graceful degradation when secondary sensor channels are absent.
