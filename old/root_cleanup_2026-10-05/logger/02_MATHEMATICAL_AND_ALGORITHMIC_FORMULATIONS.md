# SIH 26121 — eRTMAC-NWIS: Mathematical & Algorithmic Formulations

This document logs the exact mathematical formulas, scoring models, and algorithms powering the NWIS intelligence platform. Use these directly in your technical presentation slides and documentation.

---

## 1. Dynamic Offset Relevance Score (DORS)

To rank offset wells dynamically as the active well drills ahead:

$$\text{DORS}(w, d_t) = w_s \cdot S_{\text{spatial}}(w) + w_f \cdot S_{\text{formation}}(w, d_t) + w_d \cdot S_{\text{depth}}(w, d_t) + w_t \cdot S_{\text{trajectory}}(w) + w_h \cdot S_{\text{hazard}}(w, d_t)$$

Where the weights satisfy $\sum w_i = 1.0$ (Default: $w_s=0.20, w_f=0.30, w_d=0.20, w_t=0.15, w_h=0.15$).

### 1.1 Component Sub-Scores:

1. **Spatial Proximity Score ($S_{\text{spatial}}$)**:
   $$S_{\text{spatial}}(w) = \max\left(0, 1 - \frac{\text{Distance}(w, \text{ActiveWell})}{R_{\max}}\right)$$
   Where $R_{\max}$ is the search radius (e.g., 25 km). Distance is computed via the Haversine formula on well surface coordinates:
   $$\Delta\sigma = 2 \arcsin \sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}$$

2. **Stratigraphic / Formation Match Score ($S_{\text{formation}}$)**:
   $$S_{\text{formation}}(w, d_t) = \begin{cases} 
   1.0 & \text{if offset well } w \text{ penetrated the same formation at corresponding depth} \\
   0.6 & \text{if adjacent formation in the same stratigraphic group} \\
   0.1 & \text{if different formation or unmapped}
   \end{cases}$$

3. **Depth Overlap Score ($S_{\text{depth}}$)**:
   Let $[D_{\min}(w), D_{\max}(w)]$ be the total drilled interval of offset well $w$, and $[d_t, d_t + \Delta D]$ be the active well's current lookahead window ($\Delta D = 100\text{ m}$):
   $$S_{\text{depth}}(w, d_t) = \frac{\text{Length}\left([D_{\min}(w), D_{\max}(w)] \cap [d_t - 50, d_t + 100]\right)}{150\text{ m}}$$

4. **Trajectory Similarity Score ($S_{\text{trajectory}}$)**:
   Compares wellbore profile type (Vertical, J-Type, S-Type, Horizontal) and average inclination $\bar{\theta}$:
   $$S_{\text{trajectory}}(w) = 1.0 - \frac{|\bar{\theta}_{\text{active}} - \bar{\theta}_{w}|}{90^\circ} \times 0.5 - 0.5 \cdot \mathbb{I}(\text{Type}_{\text{active}} \neq \text{Type}_{w})$$

5. **Historical Hazard Density Score ($S_{\text{hazard}}$)**:
   Measures whether offset well $w$ experienced documented drilling complications in the vicinity of depth $d_t$:
   $$S_{\text{hazard}}(w, d_t) = \min\left(1.0, \sum_{e \in \text{Events}(w)} \text{Severity}(e) \cdot \exp\left(-\frac{(d_e - d_t)^2}{2 \sigma_d^2}\right)\right)$$
   Where $\sigma_d = 25\text{ m}$ is the depth smoothing bandwidth.

---

## 2. Multi-Coordinate Depth Alignment & True Stratigraphic Depth

Directional wells have differences between Measured Depth (MD), True Vertical Depth (TVD), and Subsea TVD (TVDSS):

$$\text{TVD}(s) = \int_0^s \cos(\text{Inclination}(u)) \, du$$

### Stratigraphic Normalized Offset Alignment:
To account for geological formation dip angle $\alpha$ and dip azimuth $\beta$:

$$d_{\text{strat}}(w, d) = \text{TVD}(w, d) - \text{Top}_{\text{TVD}}(\text{Formation}_k, w)$$

This aligns historical events by **penetration distance within the geological formation**, eliminating false offsets caused by regional dipping layers.

---

## 3. Historical Risk Corridor Identification

A **Risk Corridor** $\mathcal{C}_k = [D_{\text{start}}, D_{\text{end}}]$ is identified when a cluster of historical events across top-ranked offset wells $W_{\text{top}}$ satisfy:

$$\mathcal{C}_k = \left[ \min_{e \in \mathcal{E}} d_{\text{start}}(e) - \delta, \; \max_{e \in \mathcal{E}} d_{\text{end}}(e) + \delta \right]$$

### Lead-Time Distance Calculation:
$$\Delta D_{\text{lead}} = D_{\text{start}}(\mathcal{C}_k) - d_{\text{current}}$$

* **Safe State:** $\Delta D_{\text{lead}} > 50\text{ m}$
* **Proactive Early Warning State:** $0 < \Delta D_{\text{lead}} \le 50\text{ m}$
* **Critical Hazard State:** Active bit is inside corridor ($D_{\text{start}} \le d_{\text{current}} \le D_{\text{end}}$)

---

## 4. Multi-Signal Hybrid Risk Aggregation Model

The contextual risk for each hazard family $H \in \{\text{MudLoss}, \text{StuckPipe}, \text{Kick}, \text{TorqueSpike}, \text{Cementing}\}$ is:

$$R_H(t) = \alpha \cdot P_{\text{history}}(H, d_t) + \beta \cdot A_{\text{sensor}}(H, t) + \gamma \cdot M_{\text{ML}}(H, X_t)$$

Where:
* $P_{\text{history}}(H, d_t) \in [0, 1]$ is the historical frequency of hazard $H$ in top relevant offsets in this interval.
* $A_{\text{sensor}}(H, t) \in [0, 1]$ is the real-time sensor anomaly score (e.g. flow discrepancy, torque gradient).
* $M_{\text{ML}}(H, X_t) \in [0, 1]$ is the calibrated supervised classifier prediction.
* Weights $\alpha=0.45, \beta=0.35, \gamma=0.20$.

### Decoupled 4-Pillar Confidence Breakdown:
$$\text{Confidence Output} = \begin{cases}
\text{Evidence Strength:} & \text{High / Moderate / Low (based on sample size } N_{\text{offsets}}\text{)} \\
\text{Telemetry Anomaly:} & \text{Z-score deviation on real-time stream} \\
\text{Data Quality Index:} & \text{Percentage of structured parameters present} \\
\text{Audit Status:} & \text{Fully Grounded with Source PDF + Page Number}
\end{cases}$$
