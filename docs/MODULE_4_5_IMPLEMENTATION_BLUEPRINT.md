# SIH26121 — eRTMAC-NWIS: Module 4 & 5 Master Implementation Blueprint & Comprehensive Audit

**Project:** SIH26121 — Nearby Wells Intelligence System (eRTMAC-NWIS)  
**Sponsoring Organization:** Oil India Limited (OIL)  
**Role:** Lead Systems Engineer & Drilling Subsurface Architect  
**Specification Documents:**  
1. `docs/SIH26121_Module_4_Research_and_Implementation_Plan.md`  
2. `docs/SIH26121_Module_5_FINAL_Physics_Engine_Telemetry_ML_Methodology.md`  
**Document Purpose:** Complete repository audit, requirement traceability matrix, competitor code-level reality check, architectural boundary freeze, and master execution blueprint.

---

## 1. Deep Competitor Code-Level Audit (Reality vs Claims)

Based on direct source code inspection of the 12 cloned competitor repositories in `research/competitors/direct/`:

| Competitor Repository | What is Really Implemented | What is Merely Claimed / Mock | Data Used | Correlation Logic | Raw MD vs Geological Normalization | Telemetry State | ML State | Source Provenance | What to Adopt | What NOT to Copy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **dhanwanth-dh/eRTMAC--NWIS** | 5 XGBoost models, IsolationForest, 6-factor similarity, 4-step action cards | True stratigraphic correlation, physical drilling dynamics | Synthetic CSVs (`wells.csv`, `historical_drilling.csv`) | Total depth difference $|TD_{act} - TD_{off}|$ | **Raw MD only**; ignores structural dip | Static row replay from CSV | Trained on synthetic rows, but circular boolean rules | Plain text string citations | 5 dedicated binary hazard models; 4-step actionable mitigations | Random row splitting; circular boolean training labels; raw TD matching |
| **thor11223344/PetrolQ** | PostGIS `ST_DWithin`, MapLibre GL tiles, Eaton PPFG equations | Real gamma-ray log correlation, dynamic trajectory tracking | Static JSON dictionary & synthetic script | Hardcoded formation dictionary lookup | **Raw MD slices** ($\pm 100\text{m}$) | Fake telemetry script | Hardcoded sine wave risk curves ($0.12 + 0.08\sin(z/200)$) | Plain text file citations | PostGIS spatial queries; Eaton PPFG & dynamic operating margins | Fake sine wave logs & risk curves; static formation dictionaries |
| **n3ssdub3y/SIH_2026_PLANNS** | FastDTW trajectory alignment, NetworkX graph, hazard feature weights | Autonomous predictive corridor, OCR layout analysis | Equinor Volve subset + synthetic events | Linear depth penalty ($1 - \|\Delta MD\| / 500$) | **Raw MD only** | Static JSON replay | No real ML; basic similarity weighting | Plain text document citations | Hazard-specific offset ranking weights; FastDTW profile matching | Linear MD proximity formula; lack of visual provenance |
| **Physics0070/nwis** | PostgreSQL + Alembic schema, `EngineerAction` decision audit model | Real-time predictive analytics, 3D wellbore visualizer | PostgreSQL seed tables | SQL range queries on depth | **Raw MD only** | Replay service from DB | Rule-based heuristics | Plain text passage strings | Structured `EngineerAction` decision audit logging schema | Raw depth SQL queries without stratigraphic normalization |
| **vidhiii1711/eRTMAC-NWIS** | Fullstack Node/React/Mongo on Vercel, 20+ telemetry stream channels | Machine learning predictive risk, rock physics engine | Mongo seed JSON | Threshold matching on depth | **Raw MD only** | Replayed stream | Heuristic rule checks | Plain text citations | Wide telemetry channel schema (20+ rig sensors) | Pure heuristic thresholding without rock mechanics |
| **pallavi-a11y/eRTMAC-NWIS** | pypdfium2 + OpenCV table line detection, Qwen2.5-VL OCR, Qdrant | Real-time drilling telemetry, physics simulation | Utah FORGE PDFs | Vector search on report text | **No depth normalization** | None | None (pure RAG) | Cropped PDF page images | OpenCV morphological table line detection; bounding box tracking | Heavy full-page VLM inference in live request loops |
| **ArokyaMatthew/DrillMind** | BM25 + Dense Vector Hybrid RAG with RRF ($k=60$), Agent routing | Predictive rock physics, real-time WITSML parsing | Synthetic text chunks | Flat $\pm 100\text{m}$ MD window | **Raw MD only** | None | Prototype PyTorch LSTM (untrained on real physics) | Document chunk IDs | RRF hybrid BM25 + dense vector retrieval | Passing raw telemetry numbers to LLMs to guess physics |
| **invo-coder19/Drill-IQ** | React 19 + Vite + TanStack Router UI, interactive `WellMap.tsx` | Working backend physics and intelligence engines | Mock JSON endpoints | Mock offset score | **None** | Mock streaming | None | Mock citations | High-density dark-mode UI layout & gauge panels | Shallow mock backend |
| **tech-nitin/wellwise** | Three.js 3D subsurface layer explorer with OrbitControls & CSS2D | Backend integration, live telemetry, ML models | Hardcoded JS constants | None | **None** | None | None | None | Three.js 3D subsurface trajectory & cylinder renderer | Static layer depths decoupled from backend |
| **suryanshkota07-oss/AROH** | 5-factor analog matching, forward depth risk projection concept | Structural dip alignment, pore pressure physics | Static Python dicts | 2D Euclidean distance + depth window | **Raw MD only** | Mock telemetry | Rule thresholds | None | Forward lookahead corridor projection concept | 2D Euclidean distance without fault block barriers |
| **djimrastephane/DDR_UTAH_FORGE** | Deep PDF parsing of Utah FORGE DDRs, IADC 14-class NPT taxonomy | Real-time telemetry streaming, interactive decision platform | Real Utah FORGE DDRs | NPT event extraction | **Raw MD only** | None | None | Document headers | IADC NPT classification codes & multi-day phase parsing | Streamlit framework for real-time telemetry streaming |
| **rudrachauhan12999/eRTMAC-NWIS** | Clean FastAPI routing structure with modular sub-routers | Analytical calculation engines, physics simulator | Mock JSON returns | None | **None** | Mock JSON | None | None | Clean REST router modularization | Mock analytical stubs |

---

## 2. Requirement Traceability Matrix (RTM)

### 2.1 Module 4 — Subsurface Stratigraphic Correlation

| ID | Requirement | Spec Source | Existing File / Function | Status | Required Engineering Change | Validation Method |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **M4-01** | Minimum Curvature Trajectory Calculation | Mod 4 Sec 6, 29 | `stratigraphic_correlator.py::tvd_at_md` | **INCORRECT** | Currently does piecewise linear interpolation between pre-computed TVDs. Must implement full SPE/API Minimum Curvature equations taking raw $(MD, Inc, Az)$ to calculate $TVD, TVDSS, Northing, Easting, DLS$. | SPE/API directional survey benchmark test case |
| **M4-02** | TVDSS Normalization | Mod 4 Sec 4, 10 | `stratigraphic_correlator.py::tvdss_at_md` | **PARTIAL** | Subtracts $KB$, but relies on linearly interpolated TVD. Connect to Minimum Curvature engine output. | Unit test against known $KB$ elevations and survey stations |
| **M4-03** | Formation Identification | Mod 4 Sec 7, 10 | `xi_correlator.py::find_formation_by_tvdss` | **IMPLEMENTED** | Correctly identifies formation based on TVDSS bounds ($top \le d < base$). Add missing-formation imputation for unpenetrated offset horizons. | Unit test verifying boundary membership |
| **M4-04** | Stratigraphic Coordinate $\xi$ | Mod 4 Sec 8, 10 | `xi_correlator.py::compute_xi` | **IMPLEMENTED** | Computes $\xi = \frac{d_{tvdss} - top_{tvdss}}{thickness} \in [0.0, 1.0]$ with out-of-bounds confidence penalties. | Boundary tests ($\xi=0.0$ top, $\xi=1.0$ base, $\xi<0, \xi>1$) |
| **M4-05** | $\xi$-to-Offset Depth Mapping | Mod 4 Sec 9, 10 | `xi_correlator.py::map_xi_to_offset` | **IMPLEMENTED** | Computes $d_{offset\_tvdss} = top_{offset} + \xi \cdot thickness_{offset}$. Returns unavailable if unpenetrated. | Multi-well thickness variation test |
| **M4-06** | Historical Event Horizon Correlation | Mod 4 Sec 10, 12 | `xi_correlator.py::search_historical_events` | **PARTIAL** | Searches within $\pm 50\text{m}$ TVDSS window. Needs to convert event MD to TVDSS using offset trajectory rather than vertical assumption fallback. | Benchmark search with deviated offset trajectories |
| **M4-07** | Formation Top Uncertainty ($\pm \sigma$) | Mod 4 Sec 38, 39 | Schema has `confidence` float | **MISSING** | Implement depth uncertainty bounds ($Z_{top} \pm \sigma$) and boundary proximity penalty. | Synthetic tops with varying standard deviations |
| **M4-08** | Fault-Block Structural Gating | Mod 4 Sec 40 | None (Haversine only in DORS) | **MISSING** | Implement structural compartment check and apply barrier penalty ($\beta_{fault} = 0.20$) when crossing faults. | Wells partitioned by sealing fault polygon |
| **M4-09** | Dynamic $\Omega$ Offset Ranking | Mod 4 Sec 30-35 | `dors_engine.py::rank_offset_wells` | **PARTIAL** | DORS has static weights. Add dynamic hazard-specific weight modulation (mud loss vs stuck pipe vs kick). | Multi-hazard ranking test with varying event types |
| **M4-10** | Ahead-of-Bit Lookahead Corridor | Mod 4 Sec 36, 73 | `risk_corridor_engine.py::identify_risk_corridors` | **PARTIAL** | Currently clusters past events. Must project forward corridor $[d, d + 100\text{m}]$ along active trajectory and scan offset $\xi$-intervals. | Forward projection test verifying warnings occur before bit arrival |
| **M4-11** | Evidence Provenance & Citation | Mod 4 Sec 12, 45 | `DrillingEvent` schema text strings | **PARTIAL** | Text strings exist. Upgrade to structured evidence card with IADC NPT code, confidence tier, and normalized bounding-box coordinates. | Evidence traceability verification |
| **M4-12** | 5-Tier Validation Suite | Mod 4 Sec 57-62 | `test_xi_correlator.py` | **PARTIAL** | Tests $\xi$ math. Must add Structural Cross-Section, Formation Clustering, Blind Prediction, and Traceability tests. | Automated execution in CI pipeline |

---

### 2.2 Module 5 — Physics Engine, Telemetry & Predictive ML

| ID | Requirement | Spec Source | Existing File / Function | Status | Required Engineering Change | Validation Method |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **M5-01** | Drilling Mechanics (ROP, MSE) | Mod 5 Sec 17-19 | `state.py::SimulationState` (fields) | **MISSING** | Implement Bourgoyne-Young / Maurer ROP and Teale's Mechanical Specific Energy: $MSE = \frac{WOB}{A_b} + \frac{120 \pi \cdot RPM \cdot \tau}{A_b \cdot ROP}$. | Known WOB/RPM/ROP parameter benchmark |
| **M5-02** | Torque & Drag Model | Mod 5 Sec 32-34 | `state.py::SimulationState` (fields) | **MISSING** | Implement soft-string torque and drag as a function of borehole inclination, string weight, and friction factor $\mu$. | Vertical vs 30° deviated well drag benchmark |
| **M5-03** | Torsional Dynamics (Stick-Slip) | Mod 5 Sec 35, 36 | `state.py::SimulationState` (fields) | **MISSING** | Implement 2-DOF torsional pendulum model simulating bit stall-slip cycles and stick-slip severity index. | Stalled bit release oscillation test |
| **M5-04** | Hydraulics & Annular Pressure Loss | Mod 5 Sec 20-24 | `state.py::SimulationState` (fields) | **MISSING** | Implement power-law annular friction loss, bit nozzle $\Delta P$, Standpipe Pressure ($SPP$). | Pressure loss vs flow rate sweep |
| **M5-05** | Bottomhole Pressure ($BHP$) & $ECD$ | Mod 5 Sec 25, 26 | `state.py::SimulationState` (fields) | **MISSING** | Implement dynamic $BHP = P_{hyd} + \Delta P_{ann}$ and $ECD = \frac{BHP}{g \cdot TVD}$. | Pump on/off ECD surge and swab validation |
| **M5-06** | Pore & Fracture Pressure Regimes | Mod 5 Sec 27, 28 | `FormationParams::pore_pressure_pa` | **PARTIAL** | Static gradient formula exists. Must couple to Eaton pore pressure and Hubbert-Willis fracture gradient. | Overpressured shale pore pressure kick margin test |
| **M5-07** | Fluid Balance & Pit Volume Dynamics | Mod 5 Sec 29-31 | `pit_volume_m3` field | **MISSING** | Implement mass balance $\frac{dV_{pit}}{dt} = Q_{return} - Q_{pump} = Q_{influx} - Q_{loss}$ coupled to differential bottomhole pressure. | Pit gain/loss integration test |
| **M5-08** | Hole Cleaning & Cuttings Transport | Mod 5 Sec 37 | `cuttings_concentration` field | **MISSING** | Implement annular cuttings transport velocity, bed accumulation, and transport ratio index. | Low pump rate cuttings bed buildup test |
| **M5-09** | Physical Fault & Scenario Injectors | Mod 5 Sec 38-43 | `ActiveFault` dataclass | **MISSING** | Implement 5 scenario parameter injectors: Lost Circulation, Kick, Differential Sticking, Packoff, Washout. | Scenario execution verifying physical causality |
| **M5-10** | Sensor Simulation Layer | Mod 5 Sec 44-46 | None | **MISSING** | Implement observation layer adding Gaussian noise, calibration bias, sensor lag, quantization, and packet dropout. | Noisy telemetry statistical distribution check |
| **M5-11** | Real-Time Feature Store (25+ Features) | Mod 5 Sec 60-73 | None | **MISSING** | Implement 1-Hz sliding window pipeline extracting $\Delta Q, \frac{dV_{pit}}{dt}, \Delta SPP, MSE, d_c, \tau_{var}$. | Rolling window feature calculation unit test |
| **M5-12** | Anomaly Detection (Isolation Forest) | Mod 5 Sec 86, 87 | None | **MISSING** | Train Isolation Forest + EWMA rolling Z-score on normal drilling baseline data. | Anomaly detection on synthetic mud loss step |
| **M5-13** | 5-Head Supervised XGBoost Models | Mod 5 Sec 88, 128 | None | **MISSING** | Train 5 dedicated binary XGBoost classifiers with well-level splitting and lookahead window labeling ($[t_{event}-20\text{m}, t_{event}]$). | ROC-AUC $> 0.85$ and PR-AUC $> 0.80$ on holdout wells |
| **M5-14** | Multi-Signal Risk Fusion & Hysteresis | Mod 5 Sec 114, 186 | `risk_corridor_engine.py` (heuristic) | **PARTIAL** | Rule fallback in Mod 4. Upgrade to 4-signal fusion ($R = \sum w_i S_i$) with debouncing state machine. | Alert stability test preventing alarm chattering |
| **M5-15** | Closed-Loop Intervention & Audit Log | Mod 5 Sec 144-148 | None | **MISSING** | Generate structured 4-step action recommendations and log operator responses (`EngineerAction`). | Action plan schema validation and audit trail test |

---

## 3. Existing Architecture Audit & Structural Conflicts

### 3.1 Subsystem Inventory
1. **Frontend**: No active frontend repository exists in the root workspace. (Competitors invo-coder19, dhanwanth, and vidhiii1711 have isolated frontends in `research/competitors/direct/`).
2. **Backend**: Clean FastAPI application in `backend/app/` with Uvicorn server runner in `backend/run.py`.
3. **Database Layer**: In-memory singleton (`NWISDataStore`) loading pre-generated JSON files. SQLite job database (`nwis_jobs.db`) for background document parsing tasks.
4. **APIs**: REST router (`api/v1/router.py`) mounting document routes, well routes, intelligence routes, and telemetry routes.
5. **WebSocket Layer**: Missing. Live telemetry currently queried via polling `GET /telemetry/{well_id}`.
6. **Machine Learning**: Completely missing. Neither trained models nor training pipelines exist in `backend/app/`.
7. **Document Ingestion & OCR**: Production-ready PyMuPDF + Docling + regex/NER extraction pipeline in `backend/app/modules/document_intelligence/`.
8. **Geospatial**: In-memory 2D Haversine math. No PostGIS integration.

### 3.2 Conflicting & Duplicate Implementations Identified
1. **Depth Normalization Conflict**:
   - `stratigraphic_correlator.py` calculates absolute distance from top: $d_{strat} = TVD - Top\_TVD$.
   - `xi_correlator.py` calculates dimensionless ratio: $\xi = \frac{d_{tvdss} - top_{tvdss}}{thickness}$.
   - *Resolution*: Adopt $\xi$ as the single authoritative subsurface correlation standard across the entire platform. Retire $d_{strat}$ or retain strictly as an auxiliary diagnostic metric.
2. **Trajectory Interpolation Conflict**:
   - `stratigraphic_correlator.py::tvd_at_md` uses naive piecewise linear interpolation between stations.
   - `generate_testbed.py` uses trigonometric approximations.
   - *Resolution*: Establish `trajectory_engine.py` using standard API/SPE Minimum Curvature as the sole source of truth for all directional survey conversions.
3. **Mock Telemetry vs Physics Simulation**:
   - `telemetry_stream.json` contains static pre-generated telemetry records.
   - `physics_engine` defines `SimulationState` but does not generate or stream telemetry.
   - *Resolution*: Physics Engine must become the authoritative dynamic generator and live telemetry feeder.

---

## 4. Final System Architecture & Dependency Graph

```
                                  ┌──────────────────────────────────────────────┐
                                  │    Active Rig Telemetry Stream & Surveys     │
                                  │   (MD, Inc, Az, WOB, RPM, Flow, SPP, Mud)    │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MODULE 4: SUBSURFACE STRATIGRAPHIC CORRELATION & HISTORICAL LOOKAHEAD                                          │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Directional Geodesy (Minimum Curvature):  (MD, Inc, Az) ──> (TVD, TVDSS, Northing, Easting, DLS)            │
│ 2. Fault-Block Gating:                      Check structural compartment & apply barrier penalty (β = 0.20)   │
│ 3. Stratigraphic Coordinate:                ξ(d) = (TVDSS - Top) / Thickness ∈ [0.0, 1.0]                     │
│ 4. Offset Horizon Mapping:                  d_offset_tvdss = Top_offset + ξ · Thickness_offset                │
│ 5. Dynamic Ω Ranking:                       Ω = w_dist·S_dist + w_geo·S_geo + w_traj·S_traj + w_comp·S_comp   │
│ 6. Forward Lookahead Corridor:              Project [d, d + 100m] ──> Intersect offset ξ-horizons ──> NPT Risk │
│ 7. Evidence Provenance:                     4-Pillar Confidence (Evidence, Sensor, Quality, Audit)            │
└────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                         │
                                 Historical Prior Risk   │   Equivalent Offset Depths
                                 & Corridor Bounds       │   & Formation Uncertainties
                                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MODULE 5: PHYSICS-BASED DIGITAL TWIN, TELEMETRY & ML ANALYTICS                                                 │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Physics Engine (Digital Twin):                                                                              │
│    ├── Mechanics: Bourgoyne-Young ROP, Bit Torque, Wall Drag, Mechanical Specific Energy (MSE)                 │
│    ├── Hydraulics: Annular Friction Loss, Bit Nozzle ΔP, Dynamic BHP, Equivalent Circulating Density (ECD)     │
│    ├── Pressure Regime: Eaton Pore Pressure, Hubbert-Willis Fracture Gradient, Dynamic Margins                 │
│    ├── Fluid Balance: Mass Balance (dV_pit/dt = Q_return - Q_pump = Q_influx - Q_loss)                         │
│    └── Dynamics: Stick-Slip Torsional Pendulum, Cuttings Bed Hole Cleaning Index                               │
│ 2. Scenario Fault Injector (Ground Truth):                                                                     │
│    └── Injectable Scenarios: Lost Circulation, Gas Kick, Differential Sticking, Packoff, Washout               │
│ 3. Sensor Observation Layer: Realistic Gaussian noise, calibration bias, sensor lag, dropout                   │
│ 4. Real-Time Feature Store (25+ Features): ΔQ, dV_pit/dt, ΔSPP, MSE, d_c, Torque Trend, ξ-Distance             │
│ 5. Anomaly Detection: Isolation Forest + Rolling Z-Score Baseline                                              │
│ 6. Supervised ML Suite: 5 dedicated XGBoost Binary Classifiers (trained with Well-Level Splitting)             │
│ 7. Multi-Signal Risk Fusion: R = w_hist·P_hist + w_sens·A_sens + w_phys·M_phys + w_ml·P_ml                     │
│ 8. Risk State Machine: Hysteresis Debouncing (NORMAL ──> WATCH ──> WARNING ──> CRITICAL)                       │
└────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MODULE 6 INTEGRATION & COCKPIT DECISION SUPPORT                                                                │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Actionable 4-Step Mitigations (Priority, Recommended MW, RPM, WOB, LCM formulation)                          │
│ • Operator Decision Audit Trail (EngineerAction: ACCEPTED / REJECTED / MODIFIED + Rationale)                   │
│ • Visual PDF Provenance: Exact bounding-box coordinates on source EOWR/DDR documents                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Frozen Architectural Ownership & Module Boundaries

To prevent duplication and tangled dependencies, ownership is strictly partitioned:

1. **Module 4 owns Geological & Subsurface Correlation**:
   - Owns raw directional surveys, Minimum Curvature conversion, TVDSS, formation top boundaries, stratigraphic $\xi$ coordinates, offset horizon mapping, fault block gating, $\Omega$ ranking, and historical event lookahead corridors.
   - *Never* calculates drilling mechanics, pump hydraulics, or sensor noise.
2. **Physics Engine owns Internal Physical Ground Truth**:
   - Owns the physical simulation of the wellbore, rock failure, drillstring rotation, fluid flow, bottomhole pressures, and scenario perturbations.
   - *Never* serves telemetry directly to the API without passing through the Sensor Model.
3. **Telemetry Layer owns Transport & Observation**:
   - Owns sensor noise, calibration bias, sensor lag, quantization, packet dropout, 1-Hz buffering, and WebSocket streaming.
   - *Never* computes risk probabilities or recommends mitigations.
4. **Module 5 owns Feature Engineering, Predictive Analytics & Risk Fusion**:
   - Owns rolling feature generation, anomaly detection (Isolation Forest), supervised hazard classification (5-head XGBoost), multi-signal risk fusion, and hysteresis debouncing.
   - Receives geological priors from Module 4 and observed telemetry from the Telemetry Layer.
5. **Module 6 owns Operational Decision Support & Action Workflows**:
   - Owns actionable mitigation generation, operational procedures, alarm escalation, and the `EngineerAction` decision audit trail.
6. **RAG / Document Intelligence owns Historical Evidence Retrieval & Provenance**:
   - Owns OCR, table parsing, vector embeddings, BM25 indexing, and linking alerts to PDF bounding boxes.

---

## 6. Implementation Action Plan

### 6.1 Files to Create
1. `backend/app/modules/well_intelligence/services/trajectory_engine.py`:
   - SPE/API Minimum Curvature directional survey calculator.
2. `backend/app/modules/physics_engine/services/mechanics.py`:
   - Bourgoyne-Young ROP, bit torque, string drag, MSE, hookload.
3. `backend/app/modules/physics_engine/services/hydraulics.py`:
   - Power-law annular friction, nozzle $\Delta P$, SPP, dynamic BHP, ECD, Eaton pore pressure, fracture gradient.
4. `backend/app/modules/physics_engine/services/faults.py`:
   - 5 physical scenario injectors (Loss, Kick, Differential Sticking, Packoff, Washout).
5. `backend/app/modules/physics_engine/services/sensors.py`:
   - Sensor observation layer (noise, bias, delay, quantization, dropout).
6. `backend/app/modules/physics_engine/services/engine.py`:
   - Master simulation runner coordinating mechanics, hydraulics, fluid balance, and dynamics.
7. `backend/app/modules/physics_engine/services/features.py`:
   - Real-time feature extractor computing 25+ rolling physics features.
8. `backend/app/modules/physics_engine/services/risk_fusion.py`:
   - Multi-signal risk aggregator with hysteresis state machine and `EngineerAction` logger.
9. `backend/app/modules/physics_engine/ml/generate_training_data.py`:
   - Batch simulation script generating domain-randomized training datasets.
10. `backend/app/modules/physics_engine/ml/train_models.py`:
    - Offline ML training pipeline with well-level splits and model serialization.
11. `backend/app/modules/physics_engine/ml/models.py`:
    - Inference engine wrapping Isolation Forest and 5-hazard XGBoost classifiers.
12. `backend/app/modules/physics_engine/routes/simulator_routes.py`:
    - REST & WebSocket endpoints for simulation control, telemetry streaming, and scenario injection.

### 6.2 Files to Modify
1. `backend/app/modules/well_intelligence/services/xi_correlator.py`:
   - Integrate Minimum Curvature trajectory engine, fault block gating, and boundary uncertainty.
2. `backend/app/modules/well_intelligence/services/dors_engine.py`:
   - Implement dynamic hazard-specific $\Omega$ weights.
3. `backend/app/modules/well_intelligence/services/risk_corridor_engine.py`:
   - Implement forward lookahead corridor projection $[d, d + 100\text{m}]$.
4. `backend/app/api/v1/router.py`:
   - Mount new simulator and predictive risk sub-routers.
5. `backend/requirements.txt`:
   - Add `xgboost>=2.0.0` and `scikit-learn>=1.4.0`.

---

## 7. Testing & Verification Strategy

1. **Directional Survey Geodesy Test**:
   - Compare `trajectory_engine.py` against standard SPE/API survey benchmarks. Error in TVD, Northing, Easting must be $< 0.001\text{m}$.
2. **$\xi$-Correlation Sanity Test**:
   - Verify $\xi=0.0$ at formation top, $\xi=1.0$ at formation base, monotonic mapping, and strict handling of unpenetrated offset formations.
3. **Physics Steady-State Test**:
   - Verify hydrostatic pressure matches $\rho g h$, ROP responds positively to WOB/RPM, and ECD increases with flow rate.
4. **Physical Scenario Causality Test**:
   - *Lost Circulation*: Inducing thief fracture must cause $Q_{out} < Q_{in}$, pit volume drop, and SPP drop.
   - *Kick*: Inducing overpressured formation must cause pit gain, $Q_{out} > Q_{in}$, and gas expansion.
5. **Machine Learning Holdout Evaluation**:
   - Evaluate 5 XGBoost hazard classifiers on holdout wells using well-level grouping. Require $PR\text{-}AUC \ge 0.80$ on pre-event windows ($[t_{event}-20\text{m}, t_{event}]$).
6. **End-to-End Alert & Mitigation Test**:
   - Run simulated active drilling approaching a known offset loss zone. Verify:
     - Module 4 flags lookahead corridor warning at $d_{event} - 50\text{m}$.
     - Telemetry exhibits developing flow anomaly.
     - ML model escalates risk from WATCH to WARNING.
     - System outputs actionable 4-step mitigation with source provenance.

---

## 8. Exact Next Implementation Step

Proceed immediately to **Phase 1: Directional Geodesy & Minimum Curvature Core (Module 4)** by creating `backend/app/modules/well_intelligence/services/trajectory_engine.py` and validating against industry benchmark surveys.
