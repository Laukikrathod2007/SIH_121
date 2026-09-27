# SIH26121 — eRTMAC-NWIS: Nearby Wells Intelligence System
### Real-Time Drilling Digital Twin, Subsurface Stratigraphic Correlation & Predictive Hazard Analytics Platform

**Sponsoring Organization:** Oil India Limited (OIL)  
**Smart India Hackathon 2026** — Problem Statement ID: 26121  
**Lead Systems Architecture:** Integrated Subsurface, Drilling Mechanics, Predictive ML & Real-Time Telemetry Twin  
**Verification Status:** **105/105 Automated Tests Passing (100% Green)**  

---

## 1. System Overview & Core Philosophy

The **eRTMAC-NWIS** platform transforms real-time drilling operations from reactive firefighting into **proactive, predictive risk management**. In directional and deep exploratory drilling, geological beds dip, vary in thickness, and cross structural fault compartments. Comparing raw Measured Depth ($MD$) between adjacent wells leads to the catastrophic *"Trajectory Trap"*—misidentifying formation tops and failing to anticipate hazards.

eRTMAC-NWIS establishes a **geologically normalized, physics-grounded operational digital twin**:

```
                       [ DIRECTIONAL DRILLING TRAJECTORY ]
                                       │
                       (SPE/API Minimum Curvature 3D)
                                       ▼
                       [ TRUE VERTICAL DEPTH SUBSEA (TVDSS) ]
                                       │
                       (Interval Boundary Matching)
                                       ▼
                       [ STRATIGRAPHIC FORMATION TOP & BASE ]
                                       │
                       (Dimensionless Stratigraphic Coordinate)
                                       ▼
                       [ STRATIGRAPHIC COORDINATE ξ ∈ [0, 1] ]
                                       │
                       (Offset Formation Thickness Scaling)
                                       ▼
                       [ EQUIVALENT OFFSET TVDSS & EVIDENCE ]
```

Coupled to this geological backbone is a **reduced-order physics engine** that operates under strict conservation laws (mass, momentum, torque, and energy) rather than arbitrary random number generators or client-side sine waves.

---

## 2. Architecture & Subsystem Highlights

```mermaid
graph TD
    subgraph Subsurface Geology (Module 4)
        M4_1[Directional Surveys: MD, Inc, Az] --> M4_2[SPE Minimum Curvature: TVDSS, North, East, DLS]
        M4_2 --> M4_3[Boundary Identification: Half-Open Interval Matching]
        M4_3 --> M4_4[Stratigraphic Coordinate: ξ = (TVDSS - Top) / Thickness]
        M4_4 --> M4_5[Equivalent Offset TVDSS Mapping]
        M4_5 --> M4_6[Dynamic Offset Relevance Scoring DORS]
        M4_6 --> M4_7[Ahead-of-Bit Lookahead Corridor 100m]
    end

    subgraph Reduced-Order Physics Twin (Module 5)
        P1[Operator Controls: WOB, RPM, Q_in, Mud Weight] --> P2[Drilling Mechanics: Bourgoyne-Young ROP, Teale MSE]
        P1 --> P3[Hydraulics: Power-Law Pressure Loss, SPP, BHP, ECD]
        P1 --> P4[Torsional Dynamics: 2-DOF Stribeck Friction Limit Cycles]
        P2 & P3 --> P5[Dynamic Pit Mass Balance: Influx / Darcy Loss]
        P2 --> P6[Hole Cleaning: Cuttings Slip & Bed Accumulation]
        FAULT[Scenario Injector: Loss, Kick, Stuck Pipe, Stick-Slip] --> P3 & P4 & P5
    end

    subgraph Sensor Observation & Streaming
        P2 & P3 & P4 & P5 --> S1[Sensor Array: Gaussian Noise, Lag, Quantization, Dropout]
        S1 --> S2[Sensor Fault Engine: Bias, Stale, Outlier Resilience]
        S2 --> S3[FastAPI WebSocket Stream 1 Hz]
    end

    subgraph Predictive ML & Risk Fusion (Module 5 & 6)
        S3 --> F1[Rolling Feature Pipeline: 55 Features at 1 Hz]
        F1 --> R1[Deterministic Baseline Rules: Debounced Hysteresis State Machine]
        F1 --> R2[Unsupervised Anomaly Model: Isolation Forest 0.2 alerts/hr]
        F1 --> R3[Supervised Classifier: 6-Class XGBoost PR-AUC 0.949]
        M4_7 --> R4[Geological Offset Context Score]
        R1 & R2 & R3 & R4 --> FUSE[Multi-Signal Risk Fusion Engine]
        FUSE --> M6[Module 6 Alert & Advisory Engine: 4 Tiers, IADC Action Cards, Recovery Lifecycle]
    end
```

---

## 3. Subsystem Breakdown

### Module 4 — Subsurface Stratigraphic Correlation
- **SPE/API Minimum Curvature Engine:** Exact 3D directional coordinates, dogleg severity ($DLS$), and subsea depths ($TVDSS$). Zero-dogleg singularities resolved via 4th-order Taylor series expansions.
- **Stratigraphic Coordinate ($\xi$):** Eliminates structural dip and thickness variation:
  $$\xi = \frac{TVDSS - Top_{TVDSS}}{Base_{TVDSS} - Top_{TVDSS}} \in [0.0, 1.0]$$
- **Dynamic Offset Relevance Scoring (DORS):** Multi-factor weighting dynamically modulated by hazard query type (mud loss, kick, stuck pipe).
- **Ahead-of-Bit Lookahead Corridor:** Forward-projects the active trajectory $[d, d + 100\text{m}]$, scanning offset $\xi$-intervals for historical NPT events to deliver **120 seconds of precursor warning**.
- **Visual Evidence Provenance:** Traces every historical incident back to its Daily Drilling Report (DDR/DOR) source with IADC NPT codes and bounding boxes.

### Module 5 — Physics Digital Twin & Live Telemetry
- **Drilling Mechanics & Energy:** Bourgoyne-Young / Maurer penetration rate, Teale's Mechanical Specific Energy ($MSE$), and Coulomb-Euler soft-string torque and drag.
- **Hydraulics & Pressure Regimes:** Power-law annular pressure loss, bit nozzle pressure drop, Standpipe Pressure ($SPP$), dynamic $BHP$, and Equivalent Circulating Density ($ECD$).
- **Pore & Fracture Regimes:** Eaton normal compaction trend, Hubbert-Willis fracture gradient, pore pressure kick margin, and fracture breakdown margin.
- **Darcy Pit Mass Balance:** Fluid exchange driven by borehole differential pressure:
  $$\frac{dV_{pit}}{dt} = Q_{return} - Q_{pump} = Q_{influx} - Q_{loss}$$
- **2-DOF Stribeck Torsional Dynamics:** True autonomous limit cycles with Runge-Kutta 4th-order numerical integration ($\Delta t = 0.02\text{ s}$), reproducing authentic stick-slip bit stall and release oscillations ($SSI > 0.80$).
- **Sensor Degradation Layer:** Real-world sensor physics including Gaussian noise, physical time lag, ADC quantization, MWD packet dropout, and sensor fault isolation (detects sensor drift without raising false wellbore alerts).

### Module 5 & 6 — Predictive Analytics & Closed-Loop Alert Engine
- **Deterministic Baseline Rules:** Physics-based thresholds with debounce timing and hysteresis to prevent alarm chatter.
- **Unsupervised Anomaly Detection (Isolation Forest):** Trained exclusively on normal drilling baselines; detects multidimensional anomalies with **0.2 false alerts per hour**.
- **Supervised Classifier (XGBoost 6-Class):** Multi-class hazard predictor (`NORMAL`, `LOST_CIRCULATION`, `STUCK_PIPE`, `KICK`, `TORQUE_DRAG`, `WASHOUT`). Validated via strict **`GroupKFold` well-level splitting** with zero spatial data leakage.
- **Multi-Signal Risk Fusion:** Weighted synthesis of rules ($35\%$), anomalies ($20\%$), ML hazard probabilities ($30\%$), and geological offset context ($15\%$).
- **Closed-Loop Mitigation & Recovery:** Module 6 issues SPE/IADC recommended mitigation action cards. When an operator applies mitigation, setpoints feed back into the physics digital twin, downhole telemetry clears, risk decreases, and alert state recovers to `CLEARED`.

---

## 4. Quick Start & Execution Runbook

All commands are provided in standard PowerShell syntax.

### 4.1 Environment Setup
```powershell
# 1. Clone repository
git clone https://github.com/Laukikrathod2007/SIH_121.git
Set-Location "SIH_121"

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r backend/requirements.txt
```

### 4.2 Start Backend REST & WebSocket Server
```powershell
# Starts the FastAPI application at http://localhost:8000
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation: `http://localhost:8000/docs`

### 4.3 Start Frontend Industrial SCADA Dashboard
```powershell
# Open Terminal 2 (Frontend)
Set-Location "frontend"
npm install    # (already installed)
npm run dev    # Starts Vite dev server at http://localhost:5173
```
Live Dashboard: `http://localhost:5173`  
*Step-by-step 10-minute evaluator judging script: [`docs/DEMO_RUNBOOK.md`](file:///d:/Programming/Project%203.0/PS121/docs/DEMO_RUNBOOK.md)*

### 4.4 Run Automated Review & Test Suites
```powershell
# Run the 10-point Engineering Review Suite
python -m pytest backend/tests/test_system_review.py -v

# Run the complete test suite (105/105 tests passing)
python -m pytest backend/tests -v
```

### 4.4 Train Machine Learning Models
```powershell
# 1. Train Unsupervised Isolation Forest (Anomaly Detector)
python backend/app/modules/predictive_analytics/models/anomaly_detector.py

# 2. Train Supervised 6-Class XGBoost Classifier
python backend/app/modules/predictive_analytics/models/xgboost_classifier.py

# 3. Run Multi-Architecture Benchmark Evaluation
python backend/app/modules/predictive_analytics/evaluation/model_benchmarking.py
```

### 4.5 Live Digital Twin Scenario Injection & Streaming
```powershell
# Inject Lost Circulation scenario via PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/physics/faults/inject" -Method POST -ContentType "application/json" -Body '{"scenario_type": "LOST_CIRCULATION", "severity": 0.85, "duration_s": 180}'

# Inject Kick / Overpressure scenario
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/physics/faults/inject" -Method POST -ContentType "application/json" -Body '{"scenario_type": "KICK_OVERPRESSURE", "severity": 0.80, "duration_s": 180}'

# Clear scenarios back to NORMAL state
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/physics/faults/clear" -Method POST

# Stream live telemetry via WebSocket client or browser:
# ws://localhost:8000/api/v1/physics/stream
```

### 4.6 Closed-Loop Mitigation Action Execution
```powershell
# Acknowledge and execute IADC mitigation action card
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/predictive/alerts/mitigate" -Method POST -ContentType "application/json" -Body '{"well_id": "WELL-001", "hazard_type": "LOST_CIRCULATION", "action_id": "SPOT_LCM_PILL"}'
```

---

## 5. Performance & Latency Benchmarks

| Subsystem Pipeline Stage | Measured Latency | Budget Target | Status |
| :--- | :--- | :--- | :---: |
| Physics ODE Step ($\Delta t = 1.0\text{ s}$) | `1.82 ms` | $< 50\text{ ms}$ | **PASS** |
| Sensor Degradation & Packaging | `0.45 ms` | $< 10\text{ ms}$ | **PASS** |
| Rolling Feature Pipeline (55 features) | `0.29 ms` | $< 20\text{ ms}$ | **PASS** |
| ML Inference (Isolation Forest + XGBoost) | `24.53 ms` | $< 200\text{ ms}$ | **PASS** |
| Multi-Signal Risk Fusion | `1.41 ms` | $< 50\text{ ms}$ | **PASS** |
| Module 6 Alert State Machine | `0.85 ms` | $< 20\text{ ms}$ | **PASS** |
| **Total Real-Time Cycle Latency** | **`29.35 ms`** | **`< 1000 ms` (1 Hz)** | **PASS** |

The entire computational cycle runs in under **30 ms**, leaving $> 97\%$ idle CPU headroom per second for multi-well concurrent streaming on standard commodity hardware.

---

## 6. Competitive Reality vs Claims Summary

An audit of 11 public competitor repositories in `research/competitors/direct/` revealed widespread limitations:
- **Depth Handling:** 10/11 competitors match raw Measured Depth ($MD$), completely ignoring well inclination, dogleg severity, and formation dip.
- **Stratigraphic Coordinates ($\xi$):** 0/11 competitors implement stratigraphic normalization; all match crude $\pm 50\text{m}$ windows.
- **Physics Engine:** Most competitors use `Math.sin(Date.now())` or static CSV replays. None implement coupled ODE limit cycles or Darcy fluid balance.
- **ML Training Integrity:** Competitors use random row splits (`train_test_split`), causing massive temporal and spatial data leakage between adjacent depths of the same well, and train on trivial circular boolean rules.
- **eRTMAC-NWIS Advantage:** Full 3D Minimum Curvature, exact stratigraphic coordinate $\xi$, 6 coupled physics ODE subsystems, 2-DOF Stribeck stick-slip, 0.2 false alerts/hr Isolation Forest, leak-free `GroupKFold` XGBoost, and full closed-loop mitigation recovery.

*See [`docs/FINAL_COMPETITIVE_AUDIT.md`](file:///d:/Programming/Project%203.0/PS121/docs/FINAL_COMPETITIVE_AUDIT.md) for the exhaustive line-by-line comparative audit.*

---

## 7. Hard Rule Honesty Register

To maintain complete technical integrity, we explicitly declare the provenance and nature of every component:

| Category | Component / Data Item | Description & Boundaries |
| :--- | :--- | :--- |
| **Real Observed Data** | Upper Assam Basin Stratigraphy & Public Well Coordinates | Real geological sequence (Tipam, Barail Sandstone, Kopili, Disang) derived from Oil India Limited published basin studies. |
| **Public Telemetry** | Equinor Volve WITSML Logs | Real drilling telemetry from open-access North Sea reservoir used for normal drilling baseline calibration. |
| **Synthetic Data** | Digital Twin Telemetry Runs | Generated via internal reduced-order physics engine; strictly tagged with provenance marker `NWIS_PHYSICS_ENGINE`. **Never falsely labeled as live oilfield logs.** |
| **Inferred Data** | TVD / TVDSS fallback | When directional survey stations are absent, TVD is inferred assuming vertical trajectory and explicitly tagged `VERTICAL_ASSUMPTION`. |
| **Trained Models** | Isolation Forest & XGBoost 6-Class | Trained using strict `GroupKFold` well-level holdout partitions. Stored in `model_registry/` with complete feature schemas. |
| **Rule-Based Systems** | Deterministic Hazard Baselines | Explicit threshold equations with debouncing and hysteresis for fast, guaranteed fail-safe physical checks. |
| **Physics-Based Systems** | Hydraulics, Mechanics, Torsional ODE | Reduced-order models governing ROP, MSE, frictional pressure drops, BHP, ECD, Darcy fluid balance, and 2-DOF Stribeck stick-slip limit cycles. |
| **Not Yet Field-Validated** | Downhole Shock Sub Acoustics | High-frequency acoustic telemetry ($> 100\text{ Hz}$) is approximated via 1-10 Hz low-pass envelope equivalents; requires offshore BHA bench test for microsecond acoustic validation. |

---

## 8. Documentation Index

- **Master Implementation Blueprint:** [`docs/MODULE_4_5_IMPLEMENTATION_BLUEPRINT.md`](file:///d:/Programming/Project%203.0/PS121/docs/MODULE_4_5_IMPLEMENTATION_BLUEPRINT.md)
- **Module 4 Verification Report:** [`docs/MODULE_4_VERIFICATION_REPORT.md`](file:///d:/Programming/Project%203.0/PS121/docs/MODULE_4_VERIFICATION_REPORT.md)
- **Module 5 Verification Report:** [`docs/MODULE_5_VERIFICATION_REPORT.md`](file:///d:/Programming/Project%203.0/PS121/docs/MODULE_5_VERIFICATION_REPORT.md)
- **Physics Engine Implementation:** [`docs/PHYSICS_ENGINE_IMPLEMENTATION.md`](file:///d:/Programming/Project%203.0/PS121/docs/PHYSICS_ENGINE_IMPLEMENTATION.md)
- **Live Telemetry Implementation:** [`docs/TELEMETRY_IMPLEMENTATION.md`](file:///d:/Programming/Project%203.0/PS121/docs/TELEMETRY_IMPLEMENTATION.md)
- **ML Dataset Report:** [`docs/ML_DATASET_REPORT.md`](file:///d:/Programming/Project%203.0/PS121/docs/ML_DATASET_REPORT.md)
- **ML Model & Benchmark Report:** [`docs/ML_MODEL_REPORT.md`](file:///d:/Programming/Project%203.0/PS121/docs/ML_MODEL_REPORT.md)
- **Final Competitive Implementation Audit:** [`docs/FINAL_COMPETITIVE_AUDIT.md`](file:///d:/Programming/Project%203.0/PS121/docs/FINAL_COMPETITIVE_AUDIT.md)
