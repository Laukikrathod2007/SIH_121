# SIH 26121 — Subsurface Drilling Data Architecture & Domain Entity Relationships

## 1. Executive Summary
This document establishes the conceptual data architecture, entity relationships, and industry standards alignment for drilling intelligence. Instead of prematurely detailing implementation database schemas or vendor-specific SQL DDL, it investigates how drilling entities (wells, wellbores, directional surveys, lithological markers, casing shoes, and daily operational reports) relate in the real physical world, and how global standards (PPDM, OSDU, WITSML) structure upstream asset information.

---

## 2. Core Real-World Drilling Domain Entities

A drilling asset is inherently hierarchical and multidimensional. Subsurface operations require capturing temporal telemetry, spatial geometries, geological stratigraphy, and human operational narratives:

```
[OPERATOR ASSET] (Oil India Limited / Field / Concession)
       │
       ▼ (1:N)
    [WELL] (Surface Location, RKB Elevation, Spud Date)
       │
       ▼ (1:N)
   [WELLBORE] (Original Hole, Sidetrack, Lateral)
       │
       ├───► [SPATIAL TRAJECTORY] (Survey Stations: MD, Inclination, Azimuth, TVD, DX, DY)
       │
       ├───► [STRATIGRAPHIC TOPS] (Formations: Tipam, Barail, Kopili; Marker Depths)
       │
       ├───► [WELLBORE ARCHITECTURE] (Hole Sizes, Casing Strings, Cement Tops, Tubing)
       │
       ├───► [DAILY DRILLING LOGS (DDR)] (24-Hour Operations, BHA, Mud Properties, NPT)
       │
       └───► [OPERATIONAL INCIDENTS] (Mud Losses, Tight Spots, Kicks, Stuck Pipe, Remediation)
```

---

## 3. Global Petroleum Standards Mapping: PPDM, OSDU & WITSML

Upstream oil and gas organizations avoid proprietary point schemas by aligning with established data governance bodies:

| Petroleum Entity | Energistics WITSML (Real-Time Ingestion) | PPDM Association (Public Petroleum Data Model) | OSDU Data Platform (The Open Group) |
| :--- | :--- | :--- | :--- |
| **Well & Wellhead** | `<well>` object (Surface coordinates, operator, CRS). | `WELL` table (UWI, operator, surface legal coordinates). | `master-data--Well` (WGS84 Point, spatial boundaries). |
| **Trajectory Survey** | `<trajectory>` object (Station arrays, calculation method). | `WELL_DIR_SRV` / `WELL_DIR_SRV_STATION`. | `work-product-component--WellboreTrajectory`. |
| **Formation Tops** | `<formationMarker>` object (MD, TVD, lithofacies). | `WELL_STRAT_UNIT` (Stratigraphic column hierarchy). | `work-product-component--WellboreMarkerSet`. |
| **Daily Report (DDR)** | `<bhaRun>`, `<tubular>`, `<mudLog>` objects. | `WELL_ACTIVITY` / `WELL_DAILY_REPORT`. | `work-product-component--ActivityLog`. |
| **Operational Events** | WITSML Risk XML (`<risk>`: Category, severity, mitigation). | `WELL_PROBLEM` / `WELL_EVENT`. | Custom Hazard Extension / Risk Register. |

---

## 4. Subsurface Entity Relationships & Integrity Rules

### 1. Spatial-to-Stratigraphic Decoupling
* **The Physical Reality:** A wellbore trajectory is defined strictly in 3D Euclidean space (North-South, East-West, Subsea Elevation). Stratigraphy, however, represents undulating geological surfaces that dip, fault, and pinch out.
* **Integrity Constraint:** Formation markers must NEVER be stored as static functions of Measured Depth (MD) alone. They must reference the wellbore survey station to calculate **True Vertical Depth Subsea (TVDSS)**:
  $$\text{TVDSS} = \text{TVD}_{\text{RKB}} - \text{Elevation}_{\text{RKB}}$$

### 2. Multi-Wellbore Lineage
* In complex Upper Assam drilling, drilling complications (such as severe mechanical stuck pipe in swelling shales) frequently force operators to set a cement plug and **sidetrack**.
* **Integrity Constraint:** An offset intelligence platform must distinguish between the original parent wellbore (`Well-01_OH`) and subsequent sidetracks (`Well-01_ST01`, `Well-01_ST02`). Complications that occurred in the abandoned hole must remain linked to the exact sidetrack kickoff point.

### 3. Document Provenance & Evidence Grounding
* Unstructured historical data extracted from Daily Drilling Reports (DDRs) and Well Completion Reports (WCRs) carries epistemic uncertainty.
* **Integrity Constraint:** No historical event record may exist in the system as an orphaned assertion. Every extracted event must maintain immutable bidirectional lineage to:
  1. The source document hash / filename.
  2. The specific page index within the archival dossier.
  3. The spatial bounding box coordinates $[x_1, y_1, x_2, y_2]$ of the verified text block.

---

## 5. Architectural Verdict for SIH 26121

**Verdict:** `[OSDU-ALIGNED CONCEPTUAL ENTITY MODEL]`.
- NWIS models drilling data around **open industry standards (OSDU and PPDM)** rather than bespoke, proprietary data formats.
- This ensures that when the system transitions from research to enterprise engineering, it can natively ingest data from Oil India Limited's eRTMAC WITSML servers and Landmark OpenWorks repositories without structural data conversion friction.
