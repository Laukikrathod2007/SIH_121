# SIH 26121 — Machine Learning Model Research: GBDT vs. LSTM vs. Transformers

## 1. Executive Summary
This document investigates machine learning architectures for real-time drilling hazard prediction (stuck pipe, mud loss, kicks, and dysfunctions). It benchmarks Gradient Boosted Decision Trees (XGBoost/LightGBM/CatBoost), Recurrent Neural Networks (LSTM/GRU), and Temporal Convolutional / Transformer architectures against real-time drilling constraints: streaming latency, tabular sensor heterogeneity, class imbalance, and edge deployment on rig-floor industrial IPCs.

---

## 2. Drilling Telemetry Data Topology

Real-time drilling telemetry consists of high-frequency, non-stationary multivariate time-series combined with low-frequency spatial/stratigraphic context:

```
[TIME DOMAIN: 1 Hz to 10 Hz WITS Streams]
├── Mechanical: ROP (m/hr), WOB (kN), Torque (kNm), RPM (rev/min)
├── Hydraulic: Standpipe Pressure (SPP, kPa), Flow In (L/min), Flow Out (%), Pit Volume (m³)
└── Mud Logging: Total Gas (ppm), C1-C5 Chromatography, Mud Temp In/Out (°C), ECD (g/cm³)
                        │
                        ▼
[SPATIAL / STRATIGRAPHIC DOMAIN: Depth-Indexed]
├── Lithology Class (Sandstone, Shale, Coal, Limestone)
├── True Vertical Depth Subsea (TVDSS) & Stratigraphic Normalization Ratio (ξ)
└── Historical Offset Hazard Precursors (from NWIS PostGIS Corridor)
```

### Critical Operational Constraints:
1. **Inference Latency Limit:** Hard ceiling of $< 250$ ms per telemetry frame to guarantee timely alarm dispatch before drillstring lockup or gas kick surfacing.
2. **Extreme Class Imbalance:** Normal rotary drilling accounts for $> 98.5\%$ of operational time. Hazardous anomalies (e.g., differential sticking, total loss) constitute $< 1.5\%$ of historical data.
3. **Missing Telemetry & Sensor Drift:** Rig-floor sensors frequently experience packet dropouts, calibration drift, and noise from mud pumps.

---

## 3. Systematic Model Architecture Benchmark

| Evaluation Criterion | Gradient Boosted Trees (XGBoost / LightGBM) | Recurrent Architectures (LSTM / Bi-LSTM / GRU) | Temporal Transformers (PatchTST / Informer) |
| :--- | :--- | :--- | :--- |
| **Tabular Sensor Processing** | **Superior:** Natively handles heterogeneous scale, unnormalized units, and discrete categorical features. | **Moderate:** Requires strict Min-Max scaling, z-score normalization, and continuous embeddings. | **Moderate:** High sensitivity to feature scaling and tokenization schemas. |
| **Inference Latency (Edge IPC)**| **$< 5$ ms** (Compiled C++ / Treelite / ONNX runtime). | **$30 - 80$ ms** (PyTorch / ONNX C++ runtime). | **$150 - 400$ ms** (Quadratic/patch attention overhead). |
| **Training Sample Efficiency**| **High:** Converges rapidly on $10^4 - 10^5$ rows; robust against overfitting with leaf regularization. | **Low:** Requires $10^5 - 10^7$ continuous sequence steps to avoid degenerate state loss. | **Very Low:** Requires massive cross-well pretraining datasets (millions of time steps). |
| **Handling Missing Values** | **Native:** Splits missing values into optimal default branches without imputation artifacts. | **Fragile:** Fails on `NaN` inputs; requires forward-fill or Kalman filter imputation. | **Fragile:** Requires masking tokens and imputation layers. |
| **Temporal Context Capture** | **Windowed Features:** Captures dynamics via rolling statistics ($\Delta SPP_{30s}$, $\frac{d(Torque)}{dt}$, MSE rolling mean). | **Native:** Hidden states capture recurrent sequential dependencies. | **Native Long-Horizon:** Captures extended multi-hour operational trends. |
| **Rig-Floor Edge Footprint** | **Minimal:** $< 15$ MB binary; runs on standard quad-core industrial PC without GPU. | **Moderate:** $\sim 80 - 150$ MB; benefits from edge GPU/NPU acceleration. | **Heavy:** $> 400$ MB; demands dedicated edge GPU (NVIDIA Jetson / RTX). |

---

## 4. The Hybrid Feature-Lagged Architecture

Rigorous benchmarking across SPE literature (SPE-195971, SPE-204112) demonstrates that **feature engineering combined with Gradient Boosted Trees consistently outperforms deep neural networks on tabular drilling telemetry**. 

To capture temporal trends without the instability and latency of deep recurrent networks, NWIS implements a **Lagged Feature Extraction Window**:

$$\mathbf{X}_{t} = \left[ x_t, \; \bar{x}_{w=30s}, \; \sigma(x)_{w=30s}, \; \frac{dx}{dt}_{w=10s}, \; \frac{dx}{dt}_{w=60s}, \; \Delta x_{(t - t_{offset})} \right]$$

Where key engineered derivatives include:
1. **Differential Flow Discrepancy:** $\Delta Q = Q_{out} - Q_{in}$
2. **Mechanical Specific Energy (MSE):**
   $$\text{MSE} = \frac{\text{WOB}}{A_b} + \frac{120 \pi \cdot \text{RPM} \cdot \text{Torque}}{A_b \cdot \text{ROP}}$$
3. **Corrected D-Exponent Drift:** $\Delta d_{xc} = d_{xc}(t) - \bar{d}_{xc}(baseline)$
4. **Torque Fluctuation Intensity:** $\text{TFI} = \frac{\sigma(\text{Torque})_{30s}}{\bar{\text{Torque}}_{30s}}$

```
[1 Hz RAW TELEMETRY]
        │
        ▼
[ROLLING CIRCULAR BUFFER (120 sec)] ──► [FEATURE DERIVATION ENGINE]
                                                 │
                                                 ├── Rolling Slopes (dSPP/dt, dTorque/dt)
                                                 ├── Flow Delta (FlowOut - FlowIn)
                                                 ├── Mechanical Specific Energy (MSE)
                                                 └── Stratigraphic Ratio Normalization (ξ)
                                                 │
                                                 ▼
                                     [LIGHTGBM / XGBOOST ENSEMBLE]
                                                 │
                                                 ├── Mud Loss Probability ($P_{loss}$)
                                                 ├── Stuck Pipe Probability ($P_{stuck}$)
                                                 └── Kick Anomaly Score ($S_{kick}$)
                                                 │
                                                 ▼ (Latency < 8 ms)
                                     [DECISION ARBITRATION ENGINE]
```

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[LIGHTGBM / XGBOOST WITH DERIVED FEATURE WINDOWS]`.
- **Primary Inference Engine:** Deploy **LightGBM / XGBoost** classifiers for each of the 4 independent hazard families (Mud Loss, Mechanical Sticking, Kick Overpressure, Torsional Resonance).
- **Secondary Unsupervised Anomaly Gate:** A lightweight **Isolation Forest** or **One-Class SVM** trained exclusively on "clean drilling" baseline intervals to flag uncharacterized telemetry deviations.
- **Inference Runtime:** Export trained models to **ONNX Runtime (C++ / Python bindings)** to guarantee deterministic $< 10$ ms execution per telemetry packet on rig-floor hardware.
