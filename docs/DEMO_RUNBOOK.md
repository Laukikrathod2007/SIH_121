# SIH26121 — eRTMAC-NWIS: Operational Demonstration Runbook & Judging Script
**Document ID:** DOC-NWIS-DEMO-2026-01  
**Project:** Smart India Hackathon 2026 — Problem Statement 26121 (eRTMAC-NWIS)  
**System:** Real-Time Drilling Digital Twin, Stratigraphic Correlation & Predictive Hazard Analytics Platform  
**Purpose:** Step-by-Step Evaluator Script for End-to-End Live Product Demonstration  

---

## 1. System Startup Commands (PowerShell)

### Step 1: Start Backend Core API & WebSocket Server
```powershell
# Open Terminal 1 (Backend)
Set-Location "d:\Programming\Project 3.0\PS121"
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Verify: Open `http://localhost:8000/docs` to see interactive OpenAPI documentation for all 7 modules.
- Health Check: `http://localhost:8000/api/v1/health` returns `status: "healthy"`.

### Step 2: Start Industrial Frontend
```powershell
# Open Terminal 2 (Frontend)
Set-Location "d:\Programming\Project 3.0\PS121\frontend"
npm run dev
```
- Open Browser to: `http://localhost:5173`

---

## 2. Module Traceability Matrix

| Module | Backend Service | API & WebSocket Routes | Frontend Page | Demonstration Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Module 1: Document Intelligence** | `DocumentIntelligencePipeline` | `POST /api/v1/documents/ingest`<br>`GET /api/v1/documents/jobs` | `/documents` | Demonstrate 6-layer OCR extraction of legacy DDR PDFs into WITSML records with Layer 5 physics validation. |
| **Module 2: Well Intelligence** | `NWISDataStore`<br>`SpatialIndex` | `GET /api/v1/wells`<br>`GET /api/v1/map/wells` | `/wells` | Interactive Upper Assam Basin GIS map; active well selection; DORS offset discovery with distance concentric circles. |
| **Module 3: Knowledge Base** | `DrillingEventStore` | `GET /api/v1/events`<br>`GET /api/v1/events/{id}` | `/knowledge` | Natural language search for historical offset NPT events; RAG evidence synthesis with source bounding-box citations. |
| **Module 4: Geological Correlation** | `StratigraphicCorrelator`<br>`XiCorrelator` | `GET /api/v1/xi_correlate`<br>`GET /api/v1/corridors/ahead` | `/correlation` | Visual side-by-side stratigraphic columns; dimensionless coordinate $\xi \in [0, 1]$; offset mapped TVDSS; 150m ahead corridor. |
| **Module 5: Physics Twin & Telemetry** | `DrillingPhysicsEngine`<br>`SensorObservationEngine` | `WS /api/v1/physics/stream`<br>`POST /api/v1/physics/start` | `/drilling`<br>`/simulator` | 16-channel SCADA gauges; 4 real-time Recharts time-series; 2-DOF Stribeck stick-slip limit cycles; Darcy fluid balance. |
| **Module 5: Predictive ML** | `RealTimeRiskInference`<br>`HazardClassifier` (XGBoost) | `POST /api/v1/predictive/evaluate`<br>`GET /api/v1/predictive/models` | `/risk` | 4-pillar risk fusion; Isolation Forest anomaly score (0.2 false alerts/hr); 6-class XGBoost (ROC-AUC 0.949); feature importance. |
| **Module 6: Closed-Loop Advisory** | `AlertAdvisoryEngine` | `GET /api/v1/predictive/alerts`<br>`POST /api/v1/predictive/alerts/mitigate`| `/alerts` | 4-tier alert cards; causal evidence chains; SPE/IADC standard mitigation action cards; feedback recovery to CLEARED. |
| **Module 7: Reporting & Analytics** | `ReportingAnalyticsService` | `GET /api/v1/telemetry`<br>`/reports` | `/reports` | Shift drilling summary; historical NPT hours lost breakdown; live CSV and canonical JSON export center. |
| **System Overview** | `FastAPI Core` | `GET /api/v1/health` | `/`<br>`/status` | Master command cockpit bringing all 7 modules together; full latency breakdown (29.35 ms cycle). |

---

## 3. The 10-Minute Closed-Loop Demonstration Script

Follow this exact sequence to demonstrate the entire platform to judges without opening terminal code or explaining separate repositories:

```
[ STEP 1: DASHBOARD ] → [ STEP 2: OFFSETS ] → [ STEP 3: KNOWLEDGE ] → [ STEP 4: GEOLOGY ]
         ↓
[ STEP 5: COCKPIT ]  → [ STEP 6: SIMULATE ] → [ STEP 7: PREDICTION ]
         ↓
[ STEP 8: ALERT ]    → [ STEP 9: MITIGATE ] → [ STEP 10: RECOVERY ]
```

---

### Step 1: Open Main Command Dashboard (`/`)
1. Point out the top header:
   - Active Well: `NHK-001 (Nahorkatiya)`
   - Measured Depth: `2450.0 m` | TVDSS: `2315.6 m`
   - Active Formation: `Porous Sandstone` | Stratigraphic Coordinate: $\xi = 0.250$
2. Highlight the **7-Subsystem Connectivity Bar**:
   - All modules (`Mod 1: Docs`, `Mod 2: Offsets`, `Mod 3: RAG`, `Mod 4: ξ`, `Mod 5: Physics`, `Mod 5: ML`, `Mod 6: Alerts`) are green/active.
3. Review the **4 Quadrants**:
   - Quadrant 1 (Where are we?): Geological progress through interval ($25.0\%$).
   - Quadrant 2 (What is around us?): DORS ranked offset wells ($WELL-NHK-002$, $WELL-NHK-003$).
   - Quadrant 3 (What is happening now?): Real-time telemetry gauges.
   - Quadrant 4 (What could go wrong?): Fused hazard probabilities in safe baseline ($< 20\%$).

---

### Step 2: Explore Nearby Wells & Basin GIS Map (`/wells`)
1. Click **Nearby Wells** in the sidebar.
2. Show the **Upper Assam Basin Spatial Map**:
   - Point out the active well (cyan pulsating node at $27.15^\circ\text{N}, 95.29^\circ\text{E}$).
   - Point out offset targets (amber pins) and distance concentric rings ($5\text{ km}$, $15\text{ km}$).
   - Note the **Naga Thrust Fault Barrier** polygon applying the $80\%$ geological penalty ($\beta = 0.20$).
3. Click on **WELL-NHK-002** in the table:
   - Dossier drawer opens showing spud date, total depth ($3244\text{ m}$), trajectory (J-Type), formation tops, and historical NPT incidents.

---

### Step 3: Search Historical Drilling Knowledge (`/knowledge`)
1. Click **Historical Search** in the sidebar.
2. In the natural-language search bar, type:
   > *"Lost circulation in Barail Sandstone"*
3. Click **SEARCH**:
   - Point out the **Grounded Operational Synthesis (RAG Evidence-Backed)** panel summarizing why differential pressure surges cause mud loss in this specific sand, and recommending field standard mitigation (spotting 40 bbl LCM pill).
   - Scroll through the supporting DDR evidence cards showing exact IADC codes (`05`), depths, and source citations.
   - Emphasize the **Data Provenance tag:** `OBSERVED (Daily Drilling Report #14)`.

---

### Step 4: Inspect Geological Stratigraphic Correlation (`/correlation`)
1. Click **Geological Correlation** in the sidebar.
2. Explain the **"Trajectory Trap"** to judges:
   - In a deviated well, comparing raw Measured Depth gives misleading formation positions.
3. Show the **Side-by-Side Stratigraphic Normalization**:
   - Active Well ($WELL-NHK-001$): Bit at $2450.0\text{ m}$ MD ($2435.2\text{ m}$ TVDSS) $\to \xi = 0.250$ in Barail Sandstone ($Top = 2400\text{ m}$, $Base = 2600\text{ m}$, $Thickness = 200\text{ m}$).
   - Offset Well ($WELL-NHK-002$): Same formation is thinner ($Top = 2350\text{ m}$, $Base = 2500\text{ m}$, $Thickness = 150\text{ m}$).
   - The engine computes:
     $$TVDSS_{offset} = 2350.0 + (0.250 \times 150.0) = 2387.5\text{ m TVDSS}$$
   - Point out the banner: *"Eliminated 62.5m structural dip & thickness divergence!"*
4. Show the **Ahead-of-Bit Lookahead Corridor** below:
   - Projections for $0-20\text{m}$ (immediate), $20-50\text{m}$ (coal transition), and $50-150\text{m}$ (Kopili overpressured shale entry) giving **120 seconds of early warning**.

---

### Step 5: Enter Live Drilling Cockpit (`/drilling`)
1. Click **Live Drilling** in the sidebar.
2. Show the **16-Channel High-Density SCADA Grid**:
   - ROP, WOB, RPM, Torque, Flow In, Flow Out, SPP, Pit Volume, Dynamic BHP, ECD, $\Delta Q$, MSE, Stick-Slip SSI, Overpull.
3. Point out the **4 Real-Time Recharts Scrolling Time-Series**:
   - Chart 1: Flow In / Out Balance & Pit Volume trend.
   - Chart 2: Pressure Operating Window (SPP, BHP, Eaton Pore Pressure, Frac Gradient).
   - Chart 3: Torsional Dynamics (Torque vs Bit RPM).
   - Chart 4: Penetration Mechanics (ROP vs WOB).

---

### Step 6: Trigger Lost Circulation Scenario (`/simulator` or Top Header)
1. In the top header scenario dropdown, select:
   > **⚠️ LOST CIRCULATION**
   *(Alternatively, navigate to `/simulator` and click **INJECT LOST CIRCULATION**)*
2. Watch the live physical propagation:
   - **Physics Solver:** BHP breaches fracture gradient $\to$ Darcy fracture loss initiates ($q_{loss} > 150\text{ LPM}$).
   - **Telemetry:** Flow Out drops from $2200\text{ LPM}$ to $2045\text{ LPM}$ ($\Delta Q = -155\text{ LPM}$).
   - **Pit Volume:** Pit volume graph curves downwards ($\frac{dV_{pit}}{dt} < -0.15\text{ m}^3/\text{min}$).
   - **Anomaly Detector:** Isolation Forest detects multivariate flow imbalance anomaly.
   - **Hazard Classifier:** XGBoost Lost Circulation probability surges to $> 75\%$.

---

### Step 7: Inspect Multi-Signal Risk Breakdown (`/risk`)
1. Click **Risk & Prediction** in the sidebar.
2. Show the **Fused Drilling Hazard Probabilities**:
   - Lost Circulation is now highlighted in **CRITICAL RED ($> 70\%$)**.
3. Point out the **4 Decision Layers**:
   - Layer 1 (Rules): Triggered by persistent $\Delta Q < -30\text{ LPM}$.
   - Layer 2 (Isolation Forest): State marked **ANOMALOUS** (Anomaly score: $-0.245$).
   - Layer 3 (XGBoost): Predicts `LOST_CIRCULATION` ($82\%$).
   - Layer 4 (Geology): Historical offset incident weighting applied.

---

### Step 8: View Critical Alert & Evidence Chain (`/alerts`)
1. Click **Alerts & Advisory** in the sidebar.
2. Point out the **CRITICAL Alert Card**:
   - Headline: *"BHP (245 bar) breached formation fracture gradient (238 bar) in Porous Sandstone, producing 155 LPM return flow deficit."*
   - Causal Evidence Chain: Traces exact physical symptoms to downhole Darcy flow.
   - IADC Action Plan: *"Stop drilling $\to$ pull off bottom $\to$ reduce pump rate to 1400 LPM $\to$ mix & spot 40 bbl LCM pill."*

---

### Step 9: Execute Engineer Mitigation Action (Closed-Loop)
1. On the alert card, click the green button:
   > **EXECUTE MITIGATION**
2. Watch the system execute the feedback cycle:
   - Button transitions to *"APPLYING SETPOINTS..."*
   - The backend applies the operational fix: pumps down, fracture sealed, leakoff restored.

---

### Step 10: Observe Autonomous Recovery to CLEARED
1. Return to **Live Drilling Cockpit** (`/drilling`):
   - Return flow climbs back to $2200\text{ LPM}$ ($\Delta Q \approx 0$).
   - Pit volume curve flattens and stabilizes.
2. Return to **Alerts & Advisory** (`/alerts`):
   - Notice the alert card transitions to green:
   - **`✓ RECOVERED & CLEARED`**
3. Return to **Dashboard** (`/`):
   - Overall threat level returns to **`LOW RISK`**.
   - The closed-loop demonstration cycle is complete!

---

## 4. Alternative Scenario Quick Triggers

| Scenario to Test | Trigger Location | Observable Physics Reaction |
| :--- | :--- | :--- |
| **KICK / OVERPRESSURE** | Header dropdown $\to$ `KICK_OVERPRESSURE` | Flow Out surges to $2420\text{ LPM}$ ($\Delta Q = +220\text{ LPM}$); Pit Volume gains rapidly; Kick risk rises to $77\%$; Module 6 issues Shut-in BOP alert. |
| **STICK-SLIP VIBRATION** | Header dropdown $\to$ `STICK_SLIP` | Bit stalls ($0\text{ RPM}$) while torque ramps to $28\text{ kN}\cdot\text{m}$, then slips to $260\text{ RPM}$; $SSI > 0.85$; Torque chart displays violent limit-cycle waves. |
| **STUCK PIPE** | Header dropdown $\to$ `STUCK_PIPE` | Overpull climbs to $32.5\text{ kN}$; rotary torque spikes to $30\text{ kN}\cdot\text{m}$; ROP drops to $< 0.5\text{ m/hr}$; Stuck Pipe risk climbs to $81\%$. |
| **SENSOR FAULT** | Header dropdown $\to$ `SENSOR_FAULT` | Flow sensor drops to zero; quality marks `DEGRADED`; system does **NOT** trigger a false kick/loss alert (proving fault isolation). |

---

## 5. Technical Troubleshooting Guide

| Issue | Root Cause | Immediate Fix |
| :--- | :--- | :--- |
| **"Telemetry Bus: POLLING" in sidebar** | WebSocket connection to port 8000 pending | Ensure `uvicorn` is running on port 8000. The frontend automatically falls back to HTTP polling so UI never freezes. |
| **Port 8000 already in use** | Stray background uvicorn process | Run: `Get-Process python \| Stop-Process -Force` in PowerShell, then restart backend. |
| **Port 5173 already in use** | Another Vite instance active | Run: `Get-Process node \| Stop-Process -Force`, then run `npm run dev`. |
| **Blank screen on initial load** | Browser caching stale assets | Hard refresh: `Ctrl + Shift + R`. |
