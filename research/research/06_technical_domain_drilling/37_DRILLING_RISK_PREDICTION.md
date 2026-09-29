# SIH 26121 — Multi-Hazard Predictive Framework: Lead-Time Aware Risk Engine

## 1. Executive Summary
This document establishes the overarching predictive risk architecture for NWIS. It details the 3-layer hybrid risk fusion engine combining historical offset priors, real-time sensor anomaly scoring, and supervised predictive models, providing lead-time-aware early warnings for the five core drilling complications specified in PS 26121.

---

## 2. The 3-Layer Hybrid Risk Inference Architecture

NWIS rejects the naive assumption that a single "black-box" machine learning model can predict all drilling complications. Instead, it deploys a **3-Layer Hybrid Fusion Engine**:

```
                                [LAYER 1: HISTORICAL OFFSET PRIOR]
                  Calculates Bayesian base rate $P(Risk | Formation, Depth)$ from offset WCRs/DDRs.
                                                │
                                                ▼
[ACTIVE RIG TELEMETRY] ──► [LAYER 2: REAL-TIME ANOMALY DETECTOR] ──► [HYBRID RISK FUSION ENGINE]
(WOB, RPM, TRQ, SPP, Flow)  Unsupervised rolling Z-score & Isolation Forest    Weighted Bayesian combination
                                                ▲                                     │
                                                │                                     ▼
                                [LAYER 3: SUPERVISED RISK MODEL]             [FINAL PROACTIVE ALERT]
                            Gradient Boosted Decision Trees (XGBoost/LightGBM)   Advisory / Caution / Critical
                            Trained on domain features & geomechanical limits    + Actionable Mitigation
```

### Mathematical Formulation:
For any specific hazard $k \in \{\text{Mud Loss}, \text{Stuck Pipe}, \text{Kick}, \text{Torque Spike}, \text{Cementing Issue}\}$:
$$P(\text{Hazard}_k) = \sigma \left( w_1 \cdot \text{Prior}_{offset}^{(k)} + w_2 \cdot \text{Anomaly}_{sensor}^{(k)} + w_3 \cdot \text{Model}_{supervised}^{(k)} \right)$$

1. **$\text{Prior}_{offset}^{(k)}$ (Historical Prior):** Derived from the number, severity, and proximity of historical incidents recorded in the relevant offset wells within the active formation.
2. **$\text{Anomaly}_{sensor}^{(k)}$ (Real-Time Sensor Deviation):** Detects whether current surface parameters deviate from baseline steady-state drilling (e.g. rising torque variance or declining flow return).
3. **$\text{Model}_{supervised}^{(k)}$ (Specialized GBDT Prediction):** Specialized classification model evaluating instantaneous formation drillability, mud weight margin, and BHA configuration.

---

## 3. Lead-Time Aware Early Warning Logic

An alarm that triggers when a drill pipe is already irrevocably stuck or when mud is already boiling out of the rotary table is useless. The entire value of NWIS lies in **Advance Lead-Time Warning**:

$$\Delta D = MD_{corridor}^{entry} - MD_{bit}$$
$$T_{lead} = \frac{\Delta D}{\text{ROP}_{current}}$$

| Alert Level | Spatial Proximity ($\Delta D$) | Temporal Lead Time ($T_{lead}$) | System Action & Required Operational Response |
| :--- | :--- | :--- | :--- |
| 🟢 **NORMAL (Monitoring)** | $\Delta D > 50$ m | $T_{lead} > 4.0$ hours | Normal drilling. Offset risk register displayed in background. |
| 🟡 **ADVISORY (Pre-Alert)** | $20\text{ m} < \Delta D \le 50\text{ m}$ | $1.5\text{ hr} < T_{lead} \le 4.0\text{ hr}$ | Highlights approaching formation top. Notifies engineer to review offset casing seats and prepare standby chemicals. |
| 🟠 **CAUTION (Active Prep)** | $5\text{ m} < \Delta D \le 20\text{ m}$ | $0.5\text{ hr} < T_{lead} \le 1.5\text{ hr}$ | Sounds visual alert on console. Recommends pre-treating mud system, checking flowline sensors, and holding pre-section safety briefing. |
| 🔴 **CRITICAL ALERT** | $\Delta D \le 5\text{ m}$ OR Inside Corridor | $T_{lead} \le 30\text{ minutes}$ | Flashes high-priority alarm with audio chime. Urges driller to observe flow check, limit ECD, and stage LCM pills on active pit. |

---

## 4. Multi-Hazard Decoupled Pipeline Overview

The table below outlines the specialized inputs, models, and outputs across the five risk families detailed in the subsequent research files:

| Risk Family | Specialized Predictive Engine | Primary Input Telemetry & Historical Data | Target Advance Warning | Detailed Research Doc |
| :--- | :--- | :--- | :--- | :--- |
| **1. Mud Losses** | Fracture Gradient Margin & GBDT | ECD, Mud Weight, Permeability, Offset Loss History | 15–30 m ahead of loss zone | [57_MUD_LOSS_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/57_MUD_LOSS_RESEARCH.md) |
| **2. Stuck Pipe** | Dual-Mechanism Classifier | Hookload overpull, Torque variance, Shale cavings | 30–60 min prior to seizure | [58_STUCK_PIPE_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/58_STUCK_PIPE_RESEARCH.md) |
| **3. Kicks / Overpressure** | $d_{xc}$-Trend & Flow Balance | Corrected d-exponent, $\Delta Q$, Pit Volume, Gas chromatography | 10–20 m ahead of pressure ramp | [59_KICK_OVERPRESSURE_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/59_KICK_OVERPRESSURE_RESEARCH.md) |
| **4. Torque Spikes** | FFT Spectral Variance Engine | 1-Hz Top Drive Torque, RPM, String length, DLS | 5–15 min prior to stick-slip | [60_TORQUE_AND_DRILLING_DYSFUNCTION.md](file:///d:/Programming/Project%203.0/PS121/research/60_TORQUE_AND_DRILLING_DYSFUNCTION.md) |
| **5. Cementing Risk** | Slurry Hydraulics Rule Engine | Casing standoff, Mud displacement efficiency, Slurry density | Pre-job engineering review | [61_CEMENTING_RISK_RESEARCH.md](file:///d:/Programming/Project%203.0/PS121/research/61_CEMENTING_RISK_RESEARCH.md) |
