# SIH 26121 — Digital Twin Research: Scope, Levels & Prototype Boundary

## 1. Executive Summary
This document investigates the concept of "Digital Twins" within upstream petroleum engineering. It establishes a 5-level taxonomy of digital twins, analyzes what is physically and computationally feasible, and defines the practical, high-impact digital twin scope for the NWIS prototype, warning against costly academic overengineering.

---

## 2. The 5-Level Digital Twin Hierarchy in Drilling

In industrial engineering, the term "Digital Twin" is frequently abused as marketing hype. In petroleum operations, it spans five distinct levels of maturity:

```
[LEVEL 1: 3D CAD VISUAL TWIN]
Decorative 3D model of the derrick, drawworks, and casing.
Operational Value: Low (Good for marketing; useless for engineering decisions).

[LEVEL 2: HISTORICAL REPLAY / PLAYBACK TWIN]
Time-series and depth-series playback of historical well runs with synchronized sensor curves.
Operational Value: High for post-well training and pre-drill scenario modeling.

[LEVEL 3: OPERATIONAL STATE SYNCHRONIZATION TWIN]
Real-time digital representation of active wellbore geometry, bit position, current formation top,
casing shoes, and mud column hydrostatic balance updated continuously via WITSML.
Operational Value: Highest for real-time situational awareness and decision support.

[LEVEL 4: TRANSIENT HYDRODYNAMIC PHYSICS TWIN]
Continuous numerical solution of Navier-Stokes and cuttings transport partial differential equations.
Operational Value: Specialized (Computationally heavy, requires real-time downhole rheology).

[LEVEL 5: AUTONOMOUS CLOSED-LOOP RIG CONTROL TWIN]
Digital twin directly controls rig brakes and top drive speed without human intervention.
Operational Value: Extreme risk; requires SIL-rated PLC control systems (e.g. NOVOS).
```

---

## 3. Recommended Digital Twin Scope for NWIS

### What to Build: Level 3 "Operational Decision-Support Twin"
NWIS implements an **Operational State Synchronization Twin**:
1. **Real-Time Subsurface Geometry:** Renders the active wellbore in 2D/3D space with correct TVDSS, inclination, and dogleg severity.
2. **Stratigraphic Layering:** Displays the active bit cutting through named geological formations (Tipam, Surma, Barail, Kopili).
3. **Approaching Risk Windows:** Projects the Historical Risk Corridor ahead of the bit, showing approaching hazard horizons.
4. **Simulation / Live Mode Toggle:** Enables engineers to play back historical wells (e.g. Volve or synthetic OIL wells) at 1×, 5×, or 10× speed to demonstrate how alarms trigger dynamically during active drilling.

### What Explicitly NOT to Build (Overengineering Warnings):
- **Avoid Decorative 3D Rig Graphics:** Do NOT waste development time animating a spinning 3D drill pipe or 3D derrick in Three.js. Experienced drilling superintendents view decorative 3D rigs as a gimmick that wastes screen real estate.
- **Avoid Heavy Navier-Stokes Solvers:** Do NOT attempt to program full transient multiphase hydrodynamic flow simulators in Python. OIL already licenses Landmark Well Plan for physical mud hydraulics.
