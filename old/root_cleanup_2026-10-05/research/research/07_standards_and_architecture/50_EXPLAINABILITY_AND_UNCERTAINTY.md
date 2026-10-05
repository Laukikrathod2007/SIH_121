# SIH 26121 — Explainability & Uncertainty Quantification: SHAP & Conformal Prediction

## 1. Executive Summary
In high-consequence upstream operations, black-box machine learning predictions are unacceptable. A drilling supervisor facing an alert that costs lakhs of rupees in operational downtime will not pull out of hole without understanding *why* the system fired and *how certain* the prediction is. This document designs the dual-layer explainability and uncertainty framework for NWIS: combining **TreeSHAP** (for physical feature attribution) with **Conformal Prediction** (for distribution-free, mathematically guaranteed confidence intervals).

---

## 2. The Trust Gap in Drilling AI

Traditional ML models emit point probabilities (e.g., *"Stuck Pipe Risk: 78%"*). In drilling operations, this fails for two reasons:
1. **Uncalibrated Confidence:** Neural networks and gradient-boosted trees are notoriously overconfident on out-of-distribution inputs (e.g. drilling through an unmapped fault block).
2. **Lack of Physical Attribution:** A single scalar does not tell the drill crew whether the risk is driven by differential pressure across a depleted sandstone, severe dogleg severity, or cuttings accumulation in the annulus.

```
[CONVENTIONAL BLACK BOX (REJECTED)]
Telemetry Data ──► [Deep Net / GBDT] ──► "Hazard Risk: 82%"  (Driller ignores alarm due to lack of proof)

[NWIS TRUSTED AI FRAMEWORK (RECOMMENDED)]
Telemetry Data ──► [Physics-Grounded Model] ──► "Differential Sticking Alert"
                         │
                         ├── 1. SHAP Attribution: +42% Overbalance Pressure (ΔP = 4.2 MPa)
                         │                         +28% Drillstring Static Time (t = 8.5 min)
                         │                         +14% Mud Filtrate Loss (API = 12 ml)
                         │
                         └── 2. Conformal Interval: 95% Confidence Corridor [Risk ∈ [0.74, 0.89]]
                                                   Epistemic Uncertainty: LOW (3 Verified Offsets)
```

---

## 3. Physical Feature Attribution via TreeSHAP

For tree-based ensembles (XGBoost/LightGBM), **TreeSHAP** (Lundberg et al., Nature MI 2020) computes exact Shapley values in polynomial time $O(TLD^2)$, where $T$ is the number of trees, $L$ is maximum leaves, and $D$ is maximum tree depth.

The prediction $f(x)$ is decomposed additively into the base expected value $\phi_0$ and individual feature contributions $\phi_i(x)$:

$$f(x) = \phi_0 + \sum_{i=1}^{M} \phi_i(x)$$

### Operational Feature Attribution Mapping:
When NWIS fires an alert, it dynamically extracts top positive contributors $\phi_i(x) > 0$ and translates them into plain-English physical telemetry terms:

| Feature Name | Sensor / Derived Parameter | Physical Interpretation | Driller Actionable Translation |
| :--- | :--- | :--- | :--- |
| `delta_flow_out` | $Q_{out} - Q_{in}$ | Flow deficit into formation. | *"Mud loss: Formation absorbing 140 L/min."* |
| `spp_decay_rate` | $\frac{d(SPP)}{dt}$ | Rapid pressure drop. | *"SPP falling at 45 kPa/sec without pump throttling."* |
| `rotary_torque_std` | $\sigma(\tau)_{30s}$ | Torsional vibration / slip. | *"Stick-slip intensity exceeding operational limit."* |
| `delta_overbalance`| $P_{wellbore} - P_{pore}$ | High differential pressure. | *"Overbalance excessive across Barail sand (+3.8 MPa)."* |
| `pipe_stationary_t`| $t_{rot=0, pump=0}$ | Drillstring motionless. | *"Pipe stationary for 7.2 minutes in permeable zone."* |

---

## 4. Conformal Prediction: Guaranteed Uncertainty Bounds

Standard Bayesian neural networks require unverified prior assumptions and excessive Monte Carlo sampling latency ($> 500$ ms). NWIS adopts **Inductive Conformal Prediction (ICP)**, providing distribution-free coverage guarantees:

$$P\left(Y_{new} \in \hat{C}(X_{new})\right) \ge 1 - \alpha$$

Where $\alpha \in (0, 1)$ is the driller-selected error tolerance (e.g., $\alpha = 0.05$ guarantees $95\%$ statistical coverage).

### Operational Protocol for Conformal Interval Generation:
1. **Calibration Set:** Maintain a rolling calibration set $\mathcal{D}_{cal} = \{(X_i, Y_i)\}_{i=1}^n$ of the most recent $n=500$ verified drilling intervals from the active field.
2. **Non-Conformity Scoring:** Compute absolute residual non-conformity scores:
   $$s_i = |Y_i - \hat{f}(X_i)|$$
3. **Quantile Calculation:** Determine the empirical $(1 - \alpha)(1 + 1/n)$-th quantile $\hat{q}$ of scores $\{s_1, \dots, s_n\}$.
4. **Guaranteed Prediction Region:** Construct the operational interval:
   $$\hat{C}(X_{new}) = [\hat{f}(X_{new}) - \hat{q}, \;\; \hat{f}(X_{new}) + \hat{q}]$$

If the prediction interval width $2\hat{q}$ exceeds an operational tolerance threshold $\tau_{width}$, the alert is flagged as **High Uncertainty / Low Empirical Support**, triggering a prompt for manual engineer review rather than false automated intervention.

---

## 5. Disentangling Aleatoric vs. Epistemic Uncertainty

To prevent alert fatigue, NWIS formally partitions operational uncertainty into two orthogonal dimensions:

```
                                  UNCERTAINTY SPACE
                  High │
                       │    ZONE 3: NOVEL FORMATION / EXPLORATION
                       │    (Epistemic High, Aleatoric Low)
                       │    • Offset data sparse or unmapped fault
    EPISTEMIC          │    • Action: Flag "Exploratory Interval", defer to geosteering
   UNCERTAINTY         │
(Lack of Knowledge)    │    ZONE 1: HIGH-CONFIDENCE DRILLING   │  ZONE 2: DIRTY SENSOR / CAVING
                       │    (Both Low)                         │  (Epistemic Low, Aleatoric High)
                       │    • High offset density, clean logs  │  • Heave noise, surging, sensor drift
                       │    • Action: Automated alerts active  │  • Action: Filter noise, check telemetry
                  Low  └──────────────────────────────────────┴────────────────────────────────────
                       Low                                    High
                                       ALEATORIC UNCERTAINTY (Physical Randomness / Sensor Noise)
```

1. **Aleatoric Uncertainty (Data Noise):** Estimated via short-window sensor variance $\sigma^2(\text{telemetry})$. High aleatoric noise indicates pump valve chatter, wave heave on offshore rigs, or sensor degradation.
2. **Epistemic Uncertainty (Model Ignorance):** Estimated via the distance in latent embedding space between current well conditions and the nearest historical offset well:
   $$U_{epistemic} = \min_{w \in \Omega_{offsets}} \mathcal{D}_{\text{stratigraphic}}(X_{current}, X_w)$$
   When $U_{epistemic}$ is high, the system informs the engineer: *"Approaching interval with zero historical offset penetrations within 5 km. Rely on real-time geosteering rather than historical priors."*

---

## 6. Architectural Verdict for SIH 26121

**Verdict:** `[SHAP WATERFALL + CONFORMAL GUARANTEE ON RIG UI]`.
- For every hazard alert dispatched, NWIS computes **local TreeSHAP attributions in $< 15$ ms** and renders a compact horizontal bar chart highlighting the top 3 driving telemetry deviations.
- Every projected physical value (such as projected pore pressure or expected loss volume) is rendered with a **90% Conformal Prediction Corridor** $[y_{low}, y_{high}]$, eliminating deceptive false precision.
- This dual framework directly satisfies the SIH evaluation criteria for safety-critical AI auditability.
