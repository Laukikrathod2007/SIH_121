# SIH 26121 — Open Drilling Datasets & Benchmarking Corpus

## 1. Executive Summary
Machine learning and document intelligence systems in upstream oil and gas require diverse, realistic well datasets. Because proprietary field data from Oil India Limited (Duliajan) is restricted by national data sovereignty mandates, NWIS establishes a multi-source benchmarking and validation strategy: utilizing open global real-world datasets for model pre-training and verification, paired with a physics-grounded synthetic generator tailored to the Upper Assam Basin (Tipam, Barail, Kopili, and Disang formations).

---

## 2. Global Open Benchmark Datasets

```
                                GLOBAL OPEN DATA REPOSITORY MATRIX
┌─────────────────────────────┬──────────────────────────┬─────────────────────────┬─────────────────────────┐
│       EQUINOR VOLVE         │        FORCE 2020        │       UTAH FORGE        │       DATA DRILL        │
├─────────────────────────────┼──────────────────────────┼─────────────────────────┼─────────────────────────┤
│ • 24 North Sea Wells        │ • 98 Norwegian Wells     │ • Geothermal Deep Wells │ • SPE DSEA Challenge    │
│ • 1 Hz Time Telemetry       │ • Standardized Wireline  │ • 1 Hz High-Res Sensors │ • Stuck Pipe Incidents  │
│ • Full DDR PDFs & XMLs      │ • Expert Lithofacies     │ • Hard Rock Drilling    │ • Mud Loss Case Studies │
│ • Complete WITSML Trees     │ • Formation Tops Labels  │ • DOE GDR Public Access │ • Telemetry Precursors  │
└─────────────────────────────┴──────────────────────────┴─────────────────────────┴─────────────────────────┘
```

### 1. Equinor Volve Field Dataset (Gold Standard)
- **Origin & Scope:** Released in 2018 by Equinor and its Volve license partners (ExxonMobil, Bayerngas) under the Equinor Open Data License. Contains 40,000+ files and 5 TB of data from Block 15/9 in the southern Norwegian North Sea (produced 2008–2016).
- **Drilling Relevance:**
  - **24 Wellbores:** Contains complete well construction lifecycles from surface spudding to P&A.
  - **Daily Drilling Reports (DDRs):** Unstructured PDF and XML daily logs recording bit runs, mud properties, operational remarks, NPT incidents, and cementing records.
  - **Real-Time Telemetry:** 1-Hz and 5-second depth/time logs (ROP, WOB, RPM, Torque, SPP, Flow In, Pit Gain, Gas total).
  - **Well Completion Reports (WCRs):** Geological summaries, casing schematics, formation tops, and core analysis.
- **NWIS Usage:** Serves as the primary validation testbed for the **OCR/NLP Document Intelligence Pipeline (File 53)** and the **RAG Retrieval Engine (File 54)**.

### 2. FORCE 2020 Machine Learning Competition Dataset
- **Origin & Scope:** Published by the Norwegian Petroleum Directorate (NPD), FORCE, and Earth Science Analytics in 2020.
- **Content:** 98 training wells and 10 blind test wells from the Norwegian Continental Shelf.
- **Features:** Comprehensive log suites (Gamma Ray, Density, Neutron Porosity, Resistivity, Sonic DTC/DTS, Caliper) coupled with 12 standardized lithofacies classes.
- **NWIS Usage:** Used to benchmark **Dynamic Time Warping (DTW)** and stratigraphic feature alignment across offset wells.

### 3. Utah FORGE Geothermal Drilling Dataset
- **Origin & Scope:** US Department of Energy (DOE) Frontier Observatory for Geothermal Energy hosted on the Geothermal Data Repository (GDR).
- **Wells:** Wells 16A(78)-32, 58-32, and 78B-32 drilled into hard granitic basement.
- **Features:** Continuous 1-Hz surface telemetry, downhole PWD (pressure-while-drilling), torsional and axial vibration bursts, MSE logs, and bit wear records.
- **NWIS Usage:** Used for high-frequency torsional vibration, stick-slip resonance, and mechanical dysfunction benchmarking.

---

## 4. Synthetic Upper Assam Telemetry Generator

To bridge the gap between Norwegian offshore geology and Oil India Limited's operational footprint in Assam, NWIS implements a **Forward Physics-Grounded Synthetic Generator** calibrated to Upper Assam stratigraphy:

```
[STRATIGRAPHIC ARCHETYPE: UPPER ASSAM]
├── Alluvium / Dhekiajuli (0 - 800 m) ───────► Unconsolidated sand, washouts
├── Tipam Sandstone (800 - 2,100 m) ────────► Permeable gas/oil sand, depleted pressure zones
├── Surma / Girujan Clay (2,100 - 2,800 m) ──► Swelling/sloughing shales, tight hole, pack-off
├── Barail Series (2,800 - 3,500 m) ────────► Interbedded coal seams, overpressured gas, kicks
└── Kopili Formation (3,500 - 4,200 m) ─────► Extremely fragile, reactive shale, severe sloughing
```

### Physics Formulation for Telemetry Generation:
The generator models rate of penetration using the **Bourgoyne and Young ROP Model**:

$$\text{ROP} = e^{\left( a_1 + \sum_{j=2}^{8} a_j f_j \right)}$$

Where $f_j$ captures depth compaction, pore pressure overbalance, bit weight ($WOB/D_b$), rotary speed ($\text{RPM}$), and bit hydraulic jet impact force ($F_j$).

### Automated Synthetic Incident Injection:
1. **Mud Loss Simulation:** Injects sudden fractured/depleted sand at $3,210$ m in Barail:
   $$Q_{out}(t) = Q_{in}(t) - Q_{loss} \cdot \left(1 - e^{-t / \tau_{loss}}\right) + \mathcal{N}(0, \sigma^2)$$
   Pit volume reflects immediate volumetric deficit.
2. **Differential Sticking Simulation:** Injects high overbalance ($P_{mud} - P_{pore} > 4.5$ MPa) across high-permeability Tipam sandstone with stationary drillstring $> 5$ minutes:
   $$F_{pull\_max} = F_{overpull} + A_c \cdot \Delta P \cdot \mu_{mud\_cake}$$
3. **Gas Kick Influx Simulation:** Simulates gas bubble expansion per real-gas equation of state ($P V = z n R T$) upon drilling through overpressured coal seam:
   $$\text{Pit Gain} = \int_{0}^{t} (Q_{out} - Q_{in}) \, dt, \quad \text{SPP} \uparrow, \quad \text{Gas} \uparrow \uparrow$$

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[VOLVE + SYNTHETIC ASSAM DUAL BENCHMARK]`.
- **SIH Demonstration Base:** NWIS will use 5 real-world wells extracted from the **Equinor Volve dataset** to prove end-to-end functionality on genuine industrial DDRs, WCRs, and 1-Hz WITSML logs.
- **OIL-Specific Proof-of-Concept:** NWIS will execute the **Upper Assam Synthetic Generator** to demonstrate exact compatibility with Oil India Limited's local geology (Tipam, Barail, Kopili) and specific failure archetypes before the evaluation jury.
