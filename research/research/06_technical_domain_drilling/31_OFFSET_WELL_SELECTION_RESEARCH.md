# SIH 26121 — Offset-Well Selection: Distance vs. Relevance Algorithms

## 1. Executive Summary
This document investigates how petroleum engineers select offset wells in practice, evaluating the physical, geological, and operational limitations of naive spatial radius filtering. It establishes the mathematical formulation for a multi-criteria **Dynamic Offset Relevance Engine** that ranks historical wells by true operational comparability to the active wellbore.

---

## 2. The Operational Problem: Why Distance-Only Selection Fails

In naive GIS systems, offset wells are selected purely by Euclidean surface radius:
$$\text{Distance} = \sqrt{(X_{active} - X_{offset})^2 + (Y_{active} - Y_{offset})^2} \le R_{threshold}$$

In complex geological basins (such as the Upper Assam Shelf and Fold Belt), this naive spatial assumption creates severe operational failures:

```
[SCENARIO A: NEARBY BUT IRRELEVANT]
Active Well (3,200m) ──── 1.2 km ──── Major Sealing Fault ──── Offset Well A (3,200m)
- Well A is geographically close (1.2 km away).
- However, the fault threw the strata down by 450 meters (downthrown block).
- The formation penetrated by Well A at 3,200m is completely different from the active well's target.
- Relying on Well A creates catastrophic drilling errors.

[SCENARIO B: DISTANT BUT HIGHLY RELEVANT]
Active Well (3,200m) ──────── 8.5 km along strike in same fault block ──────── Offset Well B (3,200m)
- Well B is 8.5 km away (outside a 5 km radius filter).
- However, it lies along structural strike within the exact same continuous sandstone facies.
- Well B encountered severe lost circulation in the identical stratigraphic horizon.
- Well B is the MOST critical offset well, yet naive radius filtering excludes it completely!
```

`[VERIFIED: SPE Drilling Engineering Literature; DGH Geological Basins of India]`

---

## 3. The Multi-Criteria Offset Relevance Formulation

To solve this operational failure, NWIS implements a **Dynamic Offset Relevance Score ($S_{offset}$)** that evaluates multi-dimensional geological, structural, and engineering parameters:

$$S_{offset} = w_d \cdot S_{spatial} + w_g \cdot S_{geology} + w_t \cdot S_{trajectory} + w_c \cdot S_{casing} + w_h \cdot S_{hazard}$$

Where weights satisfy $\sum w_i = 1.0$, and the individual component scores are defined as follows:

### 1. Spatial Proximity Component ($S_{spatial} \in [0, 1]$)
Evaluates geodesic distance on the WGS84 ellipsoid using an exponential decay or Gaussian kernel:
$$S_{spatial} = \exp\left( - \frac{d(Well_{act}, Well_{off})^2}{2 \cdot \sigma_d^2} \right)$$
Where $\sigma_d$ is the field correlation length (typically 5.0 km in Upper Assam).

### 2. Geological & Stratigraphic Stratum Match ($S_{geology} \in [0, 1]$)
Evaluates whether the offset well penetrates the active formation and structural fault block:
$$S_{geology} = \alpha_{block} \cdot \mathbb{I}(\text{FaultBlock}_{act} = \text{FaultBlock}_{off}) + \beta_{form} \cdot \frac{\text{Thickness}_{overlap}}{\text{Thickness}_{target}}$$
If separated by a major sealing fault, $S_{geology}$ is penalized by up to 80%.

### 3. Directional Trajectory & Inclination Similarity ($S_{trajectory} \in [0, 1]$)
Vertical wells cannot be directly compared to high-angle horizontal wells due to completely different borehole cleaning dynamics, torque/drag, and differential sticking risks:
$$S_{trajectory} = 1.0 - \frac{|\text{Inc}_{act} - \text{Inc}_{off}|}{90^\circ} - 0.5 \cdot \frac{|\text{DLS}_{act} - \text{DLS}_{off}|}{\max(\text{DLS})}$$

### 4. Hole Size & Casing Architecture Compatibility ($S_{casing} \in [0, 1]$)
Compares hole section dimensions and casing programs:
$$S_{casing} = \begin{cases} 1.0 & \text{if Hole Diameter is identical (e.g. both 12-1/4")} \\ 0.6 & \text{if adjacent diameter (e.g. 12-1/4" vs. 8-1/2")} \\ 0.2 & \text{if completely incompatible hole size} \end{cases}$$

### 5. Historical Hazard Density ($S_{hazard} \in [0, 1]$)
Boosts the visibility of offset wells that experienced critical complications (stuck pipe, kicks, losses) in the active formation:
$$S_{hazard} = \min\left(1.0, \, 0.2 \cdot N_{incidents} + 0.1 \cdot \text{Severity}\right)$$

---

## 4. Static Well-Level vs. Dynamic Interval-Level Relevance

A critical distinction enforced in NWIS is that **relevance changes dynamically as the active well deepens**:

```
[WELL-LEVEL RELEVANCE (STATIC)]
Calculated once before drilling. Ranks historical wells across their entire life.

[INTERVAL-LEVEL RELEVANCE (DYNAMIC)]
Recalculated in real time at every 10 meters of new penetration:
- At 1,800 m (Tipam Sand): Offset Well 3 is ranked #1 (identical sand channel).
- At 3,200 m (Barail Coal-Shale): Offset Well 9 becomes #1 (identical coal thickness).
- At 3,800 m (Kopili Shale): Offset Well 5 becomes #1 (experienced severe sloughing).
```

This dynamic interval recalculation ensures the drilling engineer is never overwhelmed with irrelevant historical data, but receives pinpoint offset intelligence for the exact rock volume currently being penetrated.
