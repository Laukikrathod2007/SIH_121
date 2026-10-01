# SIH 26121 — eRTMAC-NWIS: Real Datasets & In-Depth PS Data Requirements

This document details all available real-world drilling datasets and provides a word-by-word breakdown of the exact data layers required to satisfy Oil India Limited's Problem Statement (PS 26121).

---

## 1. Available Real-World Petroleum Drilling Datasets

While proprietary operating data from Oil India Limited (OIL) is internal, several internationally established public benchmarks provide real drilling reports, well logs, trajectories, and high-frequency telemetry:

| # | Dataset Name | Organization / Custodian | Contents & Data Types | Mapping to PS 26121 |
|---|---|---|---|---|
| **1** | **Equinor Volve Dataset** | Equinor & Norwegian Petroleum Directorate (NPD) | Full records for 24 wells: Daily Drilling Reports (DDRs in PDF/text), Well Completion Reports (WCR), Trajectories, Mud Logs, Well Logs. | Gold standard for **Historical Document RAG & Event Extraction**. |
| **2** | **FORCE 2020 ML Benchmark** | FORCE / Norwegian Petroleum Directorate | 100+ wells with standardized **Formation Tops, Lithology Curves, and Well Trajectories**. | Benchmark for **Stratigraphic Alignment & Cross-Well Correlation**. |
| **3** | **DataDrill Benchmark** | Society of Petroleum Engineers (SPE) & Petrobras | High-frequency telemetry (1 Hz) with labeled **Mud Loss, Well Kick, and Overpressure events**. | Benchmark for **Real-Time Sensor Anomaly Detection & Hazard ML Models**. |
| **4** | **Utah FORGE DDR Dataset** | US Department of Energy (DOE) | Daily Drilling Reports with structured incident records (stuck pipe, lost circulation, bit wear). | Benchmark for **Automated Event Extraction from unstructured drilling logs**. |
| **5** | **DGH / NDR Indian Basins** | Directorate General of Hydrocarbons (DGH, India) | Geological stratigraphic sequences and field coordinates for Indian sedimentary basins (Assam-Arakan Basin). | Provides authentic **geographical & geological context** for Oil India's operational fields (Nahorkatiya, Moran, Baghjan). |

---

## 2. Word-by-Word PS 26121 Deconstruction & Required Data Layers

When analyzing the problem statement text line-by-line, the system requires **6 interconnected data layers**:

```text
┌─────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ PS 26121 Explicit Requirements                              │ Required System Data Layer                             │
├─────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ 1. "Interactive geospatial map of nearby wells"             │ Dataset 1: Well Master & Geospatial Coordinates        │
│ 2. "Subsurface geological context and mud logging data"     │ Dataset 2: Formation Tops & Lithological Sequence      │
│ 3. "Correlation with comparable historical offset wells"    │ Dataset 3: Wellbore Trajectories & Deviation Surveys   │
│ 4. "Predictive analytics: Mud Losses, Stuck Pipe, Kicks"    │ Dataset 4: Normalized Historical Hazards & Mitigations │
│ 5. "Historical well completion & daily drilling reports"    │ Dataset 5: Unstructured Document Text Chunks & PDFs    │
│ 6. "Real-time drilling monitoring via eRTMAC integration"   │ Dataset 6: High-Frequency Telemetry Sensor Stream      │
└─────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Data Specifications

### Layer 1: Well Master & Geospatial Metadata (`wells.json`)
* **Identifiers:** `well_id`, `well_name`, `operator` (*Oil India Limited*), `field` (*Nahorkatiya, Moran, Kumchai*), `block` (*Assam-Arakan Basin*).
* **Coordinates:** `latitude`, `longitude`, `elevation_kb_m`.
* **Geometry:** `total_depth_md_m`, `total_depth_tvd_m`, `profile_type` (*Vertical / Directional-J / S-Type / Horizontal*).
* **Operational Status:** `status` (*HISTORICAL_OFFSET* or *ACTIVE_DRILLING*).

### Layer 2: Formation Tops & Stratigraphy (`formation_tops.json`)
* **Stratigraphic Units:** `formation_name` (*Alluvium, Dhekiajuli, Girujan Clay, Tipam Sandstone, Barail Coal-Shale, Kopili*), `lithology` (*Sandstone, Grey Shale, Siltstone*).
* **Depth Horizons:** `top_md_m`, `top_tvd_m`, `base_md_m`, `base_tvd_m`.
* **Pressure Gradients:** `expected_pore_pressure_ppg`, `fracture_gradient_ppg`.

### Layer 3: Trajectory & Deviation Surveys (`trajectories.json`)
* **Survey Stations:** `measured_depth_md_m`, `inclination_deg`, `azimuth_deg`.
* **Calculated Geometry:** `true_vertical_depth_tvd_m`, `subsea_tvdss_m`, `dogleg_severity_dls` (calculated via Minimum Curvature Method).

### Layer 4: Normalized Historical Events & Mitigation Playbook (`drilling_events.json`)
* **Hazard Category:** `Lost Circulation`, `Stuck Pipe`, `Well Kick / Overpressure`, `Torque & Drag Spike`, `Cementing Issue`.
* **Spatial/Depth Span:** `depth_start_md_m`, `depth_end_md_m`, `depth_start_tvd_m`, `depth_end_tvd_m`, `formation_name`.
* **Operational Details:** `severity`, `loss_rate_bbl_hr`, `npt_hours`, `observed_signals`, `root_cause`.
* **Proven Historical Mitigation:** Exact engineering remedy used historically (e.g. *LCM blend, pill volume, mud weight reduction, pump rate modification, jarring sequence*).
* **Evidence Source:** `source_document`, `source_page`, `source_paragraph`.

### Layer 5: Unstructured Document Knowledge Base (`document_corpus/`)
* Raw Daily Drilling Reports (DDR) and Well Completion Reports (WCR) text passages indexed into BM25 and Vector Search for exact citation highlighting.

### Layer 6: Real-Time Telemetry Sensor Stream (`telemetry_stream.json`)
* High-frequency channels: `measured_depth_m`, `true_vertical_depth_m`, `rop_m_hr`, `wob_klbs`, `surface_rpm`, `torque_kn_m`, `standpipe_pressure_psi`, `flow_in_lpm`, `flow_out_lpm`, `pit_volume_bbl`, `mud_weight_in_ppg`, `mud_weight_out_ppg`, `total_gas_units`.

---

## 4. Synthesis & Realistic Alignment Strategy

To prove the platform for SIH and Oil India:
1. We synthesize a 12-well testbed (verified count, `11_NWIS_BACKEND_VISUALIZATION_READINESS_AUDIT.md`) modeled on the **Upper Assam Basin** (Nahorkatiya, Moran, Baghjan, Hugrijan fields), plus 2 real Equinor Volve wells wired into the live store since logger Steps 20-24 — 14 wells live today.
2. Field names follow **WITSML**-style naming conventions as an interoperability step — this is not a certified Energistics WITSML 1.4/2.0 or OSDU schema (verified by direct code audit, `11_NWIS_BACKEND_VISUALIZATION_READINESS_AUDIT.md`; see `09_VERIFIED_STATUS_ARCHITECTURE_BENCHMARKS_AND_TECHNICAL_REFERENCE.md` §5.1 for the correct framing).
3. Sensor time-series distributions and hazard patterns mirror real benchmark dynamics from the **DataDrill** and **Equinor Volve** datasets.
4. Historical event narratives and LCM mitigations match official **OISD (Oil Industry Safety Directorate)** and **OIL drilling engineering manuals**.
