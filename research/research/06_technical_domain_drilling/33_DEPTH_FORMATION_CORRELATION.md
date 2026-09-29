# SIH 26121 — Stratigraphic & Depth Correlation: The Historical Risk Corridor

## 1. Executive Summary
This document establishes the mathematical transformation engine required to correlate subterranean intervals between non-vertical, geographically separated wells. It introduces the formal methodology for projecting historical offset drilling incidents onto an active well's trajectory to create the **Historical Risk Corridor**, resolving one of the most common physical fallacies in naive drilling software.

---

## 2. The Physical Fallacy of Raw Measured Depth (MD) Comparison

A catastrophic error made by inexperienced software developers is comparing drilling events across wells using raw Measured Depth (MD):
- Well A is a vertical exploration well.
- Well B is an S-shaped directional well with a $45^\circ$ inclination angle.
- Both wells penetrate the **Barail Sandstone**.
- In Well A, the Barail Sand is encountered at **3,000 m MD** (which is also **3,000 m TVD**).
- In Well B, because of the $45^\circ$ deviation angle, the drill pipe must travel further to reach the same vertical depth ($\cos 45^\circ \approx 0.707$). The Barail Sand is encountered at **4,242 m MD**!

If an algorithm naively alerts the driller of Well B when reaching 3,000 m MD, the alert fires **1,242 meters too early** while the bit is still in a completely different, benign upper formation!

`[VERIFIED: Standard Drilling Engineering; API RP 78 / SPE Casing Design Standards]`

---

## 3. The 3-Dimensional Depth Normalization Framework

To compare subterranean events accurately, all depths must be transformed into a standardized, geodetically referenced frame:

```
[MEASURED DEPTH (MD)]
Actual length of drillstring inside the curved wellbore (varies by wellpath).
       │
       ▼ (Minimum Curvature Trajectory Integration)
[TRUE VERTICAL DEPTH (TVD)]
Vertical distance directly below the surface rotary table (RKB).
       │
       ▼ (Minus Rotary Kelly Bushing Elevation above Mean Sea Level: TVDSS = TVD - RKB)
[TRUE VERTICAL DEPTH SUBSEA (TVDSS)]
Standardized vertical elevation relative to Mean Sea Level (MSL).
Independent of surface topography or derrick height.
```

---

## 4. The Stratigraphic Proportional Mapping Algorithm

Even after converting to TVDSS, formations dip, tilt, and change thickness across a geological basin. A sand layer that is 40 meters thick in Well A may pinch down to 25 meters thick in Well B. 

NWIS resolves this using **Proportional Stratigraphic Interval Normalization**:

```
[OFFSET WELL W-03]                           [ACTIVE WELL W-ACTIVE]
Formation Top: TVDSS = -3,100 m ──────────── Formation Top: TVDSS = -3,150 m
      │                                            │
      │ (Offset Event at 40% formation depth)     │ (Projected Corridor at 40%)
      ▼                                            ▼
[HISTORICAL MUD LOSS: -3,140 m]              [PROJECTED CORRIDOR: -3,180 m]
      │                                            │
Formation Base: TVDSS = -3,200 m ─────────── Formation Base: TVDSS = -3,225 m
(Total Thickness = 100 m)                    (Total Thickness = 75 m)
```

### Mathematical Formulation:
1. **Locate Historical Event in Offset Frame:**
   Given a historical loss or stuck-pipe event recorded in an offset well at $MD_{off}$:
   $$MD_{off} \xrightarrow{\text{Survey}_{off}} TVDSS_{off}$$
2. **Calculate Relative Stratigraphic Position ($\xi \in [0, 1]$):**
   Determine the normalized fractional depth of the event within its enclosing formation:
   $$\xi = \frac{TVDSS_{off} - TVDSS_{top, off}}{TVDSS_{base, off} - TVDSS_{top, off}}$$
3. **Project to Active Well Subsurface Coordinates:**
   Map the fractional position $\xi$ onto the active well's prognosed formation thickness:
   $$TVDSS_{act}^{projected} = TVDSS_{top, act} + \xi \cdot \left( TVDSS_{base, act} - TVDSS_{top, act} \right)$$
4. **Convert to Active Driller's Measured Depth ($MD_{act}$):**
   Using the active well's planned directional survey, invert $TVDSS_{act}^{projected}$ back to the driller's pipe tally depth:
   $$TVDSS_{act}^{projected} \xrightarrow{\text{Survey}_{act}^{-1}} MD_{act}^{target}$$
5. **Establish the "Historical Risk Corridor":**
   Apply an engineering uncertainty buffer ($\pm \Delta z$, typically $\pm 15$ m) to define the active monitoring window:
   $$\text{Risk Corridor} = \left[ MD_{act}^{target} - 15\,\text{m}, \; MD_{act}^{target} + 15\,\text{m} \right]$$

---

## 5. The Signature Feature: The Ahead-of-the-Bit Risk Corridor

This mathematical projection enables the signature visual innovation of NWIS:

```
[NWIS AHEAD-OF-THE-BIT RISK TRACK]
Current Bit Depth: 3,180 m MD (Drilling in Barail Shale)
       │
       │ Rate of Penetration: 12 m/hr
       │ (Estimated Time to Corridor: 1.5 Hours)
       ▼
═══════════════════════════════════════════════════════════════════
▼ 3,198 m MD — ENTRY INTO HISTORICAL RISK CORRIDOR
  Risk: SEVERE MUD LOSS PRECURSORS (Confidence: 87%)
  Offset Precedent: Well W-03 lost 35 m³/hr at this exact horizon.
  Formation: Fractured Barail Sandstone Upper Member.
  Recommended Mitigation: Pre-treat active mud system with 30 kg/m³
  coarse calcium carbonate LCM; reduce pump rate to 1,500 L/min.
▲ 3,222 m MD — EXIT FROM HISTORICAL RISK CORRIDOR
═══════════════════════════════════════════════════════════════════
       │
       ▼
Planned Total Depth (TD): 3,650 m MD
```

By presenting this ahead-of-the-bit corridor, the drilling supervisor is no longer surprised by downhole crises. The system delivers actionable foresight with ample lead time to execute preventive engineering procedures.
