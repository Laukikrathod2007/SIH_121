# SIH 26121 — Other Global Commercial Solutions: Nabors, Kongsberg, eDrilling, ROGII

## 1. Executive Summary
This document audits secondary and specialized global drilling technology providers, including drilling contractor automation platforms (**Nabors RigCLOUD**), real-time data hubs (**Kongsberg SiteCom**), physics-based digital twin simulators (**eDrilling**), and geological geosteering platforms (**ROGII StarSteer**), completing the global prior-art audit.

---

## 2. Audit of Specialized Commercial Vendors

### 1. Nabors Industries: RigCLOUD® & SmartROS™
- **Company Profile:** One of the world's largest land drilling contractors (Houston, Texas).
- **Core Technology:**
  - *SmartROS™:* Automated rig operating system installed across Nabors drilling fleet.
  - *RigCLOUD®:* Open digital platform hosting drilling optimization apps, real-time analytics, and automated directional steering algorithms.
  - *Corva Partnership:* Strategic alliance enabling Corva apps to write automated setpoint commands directly into Nabors rig drawworks and top drives.
- **Relevance to PS 26121:** Represents the convergence of software analytics and rig machinery automation.
- **Classification:** `[VENDOR-CLAIMED / COMMERCIAL PRODUCTION]`.

---

### 2. Kongsberg Digital: SiteCom®
- **Company Profile:** Norwegian industrial digital technology leader.
- **Core Technology:**
  - *SiteCom:* Enterprise real-time drilling data management suite and WITSML store.
  - *Remote Operations Centers:* Deployed across North Sea operators (Equinor, Aker BP) to aggregate live telemetry, mud logs, and well plans into remote surveillance hubs.
- **Relevance to PS 26121:** Serves a functional role similar to OIL's eRTMAC 1.0 (telemetry transport and live display).
- **Classification:** `[COMMERCIAL PRODUCTION]`.

---

### 3. eDrilling: Physics-Based Drilling Digital Twins
- **Company Profile:** Specialist digital twin provider headquartered in Stavanger, Norway.
- **Core Technology:**
  - *wellAhead:* Real-time, forward-looking digital twin of the wellbore that runs continuous hydrodynamic and temperature simulations alongside live drilling.
  - *Hazard Prediction:* Simulates cuttings transport, surge/swab, and pack-off risk based on physical differential equations.
- **Relevance to PS 26121:** Highlights the distinction between **physics-first simulation digital twins** (computationally intensive, requires detailed fluid rheology) and **hybrid data/offset intelligence digital twins** (NWIS approach).
- **Classification:** `[COMMERCIAL PRODUCTION]`.

---

### 4. ROGII: StarSteer & Solo Cloud
- **Company Profile:** Global leader in geological geosteering software.
- **Core Technology:**
  - *StarSteer:* Specialized platform for real-time wellbore placement and stratigraphic correlation.
  - *Offset Log Correlation:* Employs automated curve stretching, compression, and Dynamic Time Warping (DTW) to align active LWD Gamma Ray curves with offset well logs to keep horizontal wells inside thin reservoir sweet spots.
- **Relevance to PS 26121:** Demonstrates state-of-the-art mathematical algorithms for **subsurface depth and formation correlation**.
- **Classification:** `[COMMERCIAL PRODUCTION]`.

---

## 3. Global Commercial Solutions Synthesis Matrix

| Solution | Vendor Type | Primary Focus | Offset Handling | Unstructured PDF NLP? | Closed-Loop Automation? |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **SLB Tela** | Service Giant | Document AI & Risk | Multi-parameter search | **YES** | No |
| **SLB DrillPlan** | Service Giant | Well Planning | Parametric offset filter | No | No |
| **Baker Hughes DHP** | Service Giant | Real-Time Hazard | Dynamic hazard register | No | No |
| **Baker Hughes JewelSuite**| Service Giant | Engineering Analysis | Automated section analysis| No | No |
| **Cognite Know Your Well** | Industrial AI | Institutional Memory | Knowledge graph links | **YES** | No |
| **Halliburton OpenWells** | Service Giant | Well Reporting | Section benchmarking | No | No |
| **NOV KAIZEN** | Rig Manufacturer | Parameter Advisory | Performance curve overlay | No | **YES** |
| **Corva Drilling** | Cloud Platform | Real-Time Apps | Visual curve overlays | No | No |
| **eDrilling wellAhead** | Simulation Specialist| Physics Digital Twin | Synthetic physics models | No | No |
| **ROGII StarSteer** | Geosteering Specialist| Stratigraphic Geosteer | Curve DTW correlation | No | No |
| **eRTMAC-NWIS (Target)** | **Proposed SIH** | **Contextual Offset Intel**| **Dynamic Stratigraphic** | **YES (OCR/NLP)**| **No (Decision Support)**|
