# SIH26121 — eRTMAC-NWIS
## Module 4: Geological, Drilling & Reservoir Correlation
### Research, Terminology, Public-Solution Analysis, Architecture & Build Plan

**Problem Statement:** SIH26121  
**Organization:** Oil India Limited (OIL)  
**Theme:** Smart Automation  
**System:** eRTMAC-NWIS — Nearby Wells Intelligence System  
**Document purpose:** Single technical handoff for understanding and implementing the geological/drilling correlation module.

> **Core idea in one sentence:** Given the active well's current position, identify the geological position it occupies, map that same geological position into nearby historical wells, retrieve what happened there, rank the most relevant offset wells, and project historical hazards ahead of the bit.

---

# 1. What SIH26121 Actually Asks Us to Build

The public SIH26121 description says OIL wants a standalone decision-support platform alongside eRTMAC that can use historical drilling knowledge to support the active well. It explicitly calls for:

- Nearby wells on a geospatial map relative to the active well.
- Instant access to historical drilling experience and operational events from offset wells.
- Correlation of drilling parameters, reservoir characteristics, mud losses, kicks, stuck-pipe incidents, casing programs, cementing practices, and formation-specific risks across wells.
- Proactive alerts when current drilling approaches depths or formations where nearby wells encountered similar challenges.
- AI/NLP/OCR/data analytics for historical report extraction.
- A searchable knowledge repository.
- Geological/drilling/reservoir correlation by depth and formation.
- Predictive analytics for hazards such as mud losses, stuck pipe, overpressure, torque spikes, and cementing issues.
- Real-time alerts/recommendations and a user-facing dashboard.

Potential OIL data sources named by the problem include WCRs, DDRs, drilling and mud-logging databases, historical well parameters, reservoir/geological data, eRTMAC streams, well trajectory/survey data, casing/cementing/mud-program records, and historical event records.

**Source:** public SIH26121 problem statement mirrors and repositories. See [sih-hub SIH26121](https://github.com/ace-ify/sih-hub/blob/main/ps/SIH26121.md), and public reproductions of the problem statement such as [SIH 26 Copilot](https://sih-26-copilot.vercel.app/problem/sih26-26121).

---

# 2. What Module 4 Is

Module 4 is the **subsurface correlation engine**.

It should answer this chain:

```text
Active Well
    |
    +--> Current MD (Measured Depth)
             |
             v
       Convert MD -> TVDSS
             |
             v
       Identify Current Formation
             |
             v
       Calculate xi (position within formation)
             |
             +-----------------------------+
             |                             |
             v                             v
       Offset Well A                 Offset Well B
             |                             |
       Same Formation?               Same Formation?
             |                             |
       xi -> equivalent depth        xi -> equivalent depth
             |                             |
             +-------------+---------------+
                           |
                           v
                 Search Historical Events
                           |
                           v
                  Rank Relevant Offsets
                           |
                           v
                    Risk Corridor Ahead
                           |
                           v
                   Evidence + UI Alert
```

The key technical principle is that **raw MD is not necessarily comparable across wells**, and even raw TVDSS can be insufficient when wells sit at different structural positions. Our Module 4 document therefore uses TVDSS normalization and a stratigraphic depth ratio `xi` to compare equivalent positions inside a formation.

---

# 3. The Most Important Terms — Learn These First

## 3.1 Well

A drilled borehole identified by a unique well ID/name.

Example:

```text
NHK-412
NHK-089
MOR-034
```

A well record should normally contain at least:

```text
well_id
well_name
latitude
longitude
wellhead_elevation
status
spud_date
completion_date
field / basin
```

---

## 3.2 Active Well

The well currently being drilled/monitored.

The active well is the reference frame for all current correlation calculations.

Example:

```text
active_well = NHK-412
current_md = 3200 m
```

---

## 3.3 Offset Well

A historical or nearby well that is used as a comparison/analogue for the active well.

An offset well may be physically close, geologically similar, historically informative, or some combination of all three.

```text
Active well:  NHK-412
Offsets:      NHK-089, NHK-145, MOR-034, ...
```

---

# 4. Depth Terminology

## 4.1 MD — Measured Depth

**Measured Depth (MD)** is the distance measured along the actual wellbore path from the reference point.

For a vertical well:

```text
MD ≈ vertical depth
```

For a deviated well:

```text
MD > vertical depth
```

Example:

```text
Well A: vertical
MD = 3200 m

Well B: 35° deviated
MD = 3200 m
```

These two points do **not** necessarily represent the same vertical/geological horizon.

This is why comparing wells using raw MD alone can be misleading.

---

## 4.2 TVD — True Vertical Depth

**TVD** is the vertical distance from the reference surface/wellhead to the measurement point.

A deviated well can have:

```text
MD  = 3200 m
TVD = 2980–3000 m (illustrative)
```

while a vertical well at the same MD may have:

```text
MD  = 3200 m
TVD ≈ 3200 m
```

---

## 4.3 MSL — Mean Sea Level

A common vertical reference datum.

---

## 4.4 TVDSS — True Vertical Depth Sub-Sea

**TVDSS = True Vertical Depth Sub-Sea.**

It expresses the vertical position relative to mean sea level and incorporates wellhead elevation.

Our Module 4 convention is:

```text
TVDSS = TVD - wellhead_elevation_above_MSL
```

with positive values below MSL under the convention used in the module document.

Example:

```text
wellhead elevation = +85 m
TVD                = 3000 m below wellhead

TVDSS = 3000 - 85
      = 2915 m
```

**Why we use TVDSS:** it removes much of the distortion caused by different well trajectories and different surface elevations, giving us a common vertical reference.

---

# 5. Directional Survey Terms

## 5.1 Directional Survey

A table describing how the wellbore changes direction with depth.

Minimum fields:

```text
MD
Inclination
Azimuth
```

Example:

```text
MD     INC    AZ
0      0      0
100    2      45
200    8      45
500    20     45
1000   30     45
1500   35     45
2000   35     45
3000   35     45
```

---

## 5.2 Inclination (INC)

The angle of the wellbore away from vertical.

```text
0°   = vertical
90°  = horizontal
```

---

## 5.3 Azimuth (AZ)

The compass direction in which the wellbore is pointing, usually measured clockwise from north.

Examples:

```text
0°    = north
90°   = east
180°  = south
270°  = west
```

---

## 5.4 Dogleg / Dogleg Severity Concept

A **dogleg** measures how much the wellbore direction changes between survey stations.

The Module 4 specification uses the minimum-curvature dogleg equation:

```text
DL = arccos(
       cos(INC_i - INC_i+1)
       - sin(INC_i) * sin(INC_i+1)
         * (1 - cos(AZ_i - AZ_i+1))
     )
```

For implementation, degrees should be converted to radians before trigonometric calculations if using standard Python/NumPy math functions.

---

## 5.5 Ratio Factor (RF)

Minimum Curvature uses a **Ratio Factor** to account for the curved segment between two survey stations:

```text
RF = (2 / DL) * tan(DL / 2)    if DL != 0
RF = 1                         if DL == 0
```

---

# 6. Minimum Curvature Method

## 6.1 What It Does

**Minimum Curvature** is the standard calculation path we use to turn directional survey stations into a continuous wellbore geometry.

For each pair of survey stations:

```text
MD_i, INC_i, AZ_i
            +
MD_i+1, INC_i+1, AZ_i+1
            |
            v
        Dogleg + RF
            |
            v
  ΔNorth, ΔEast, ΔTVD
            |
            v
     cumulative position
```

The Module 4 specification provides:

```text
ΔNorth = (ΔMD/2)
         * [sin(INC_i)cos(AZ_i)
            + sin(INC_i+1)cos(AZ_i+1)]
         * RF

ΔEast  = (ΔMD/2)
         * [sin(INC_i)sin(AZ_i)
            + sin(INC_i+1)sin(AZ_i+1)]
         * RF

ΔTVD   = (ΔMD/2)
         * [cos(INC_i) + cos(INC_i+1)]
         * RF
```

Then:

```text
TVD = cumulative sum of ΔTVD
TVDSS = TVD - wellhead elevation
```

Source: Module 4 technical master document.

---

## 6.2 Implementation Strategy

Create a Python function:

```python
def compute_tvdss_from_survey(
    survey_df,
    wellhead_elevation_m,
):
    ...
```

Return:

```text
md
inclination
azimuth
north
 east
TVD
tvdss
```

Store the resulting survey-derived TVDSS points in the database so we do not recompute the entire path for every API request.

---

## 6.3 Missing Survey Fallback

Some old vertical wells may not have a directional survey.

Fallback:

```python
tvd = md
tvdss = md - wellhead_elevation
```

Tag the result:

```text
MINIMUM_CURVATURE
```

or:

```text
VERTICAL_ASSUMPTION
```

Never silently pretend the data came from a directional survey.

---

# 7. Formation Terminology

## 7.1 Formation

A geological unit/layer used as the main correlation context.

Examples in the Module 4 working example:

```text
Tipam Sandstone
Barail Lower Sand
Barail Coal-Shale
Kopili Formation
```

---

## 7.2 Formation Top

The depth at which a formation begins in a given well.

Example:

```text
Barail Lower Sand top = 2940 m TVDSS
```

---

## 7.3 Formation Base

The depth at which a formation ends in a given well.

Example:

```text
Barail Lower Sand base = 3380 m TVDSS
```

---

## 7.4 Formation Thickness

In the simplified model:

```text
thickness = base_tvdss - top_tvdss
```

Example:

```text
base = 3380
 top = 2940

thickness = 440 m
```

---

# 8. The Core Innovation — ξ (Xi)

## 8.1 What Is Xi?

`xi` is a **normalized position inside a formation**.

Instead of saying only:

```text
we are at 2986 m TVDSS
```

we say:

```text
we are at xi = 0.105 inside Barail Lower Sand
```

This is useful because an equivalent formation can start/end at different absolute depths in different wells.

---

## 8.2 Xi Formula

```text
xi = (d_tvdss - top_formation_tvdss)
     / formation_thickness
```

Interpretation:

```text
xi = 0.0   -> exact formation top
xi = 0.5   -> middle of formation
xi = 1.0   -> exact formation base
xi < 0     -> above formation
xi > 1     -> below formation
```

---

## 8.3 Worked Example

Active well:

```text
Current TVDSS = 2986 m
```

Formation:

```text
Barail Lower Sand
Top  = 2940 m
Base = 3380 m
```

Therefore:

```text
Thickness = 3380 - 2940 = 440 m

xi = (2986 - 2940) / 440
   = 0.105
```

Interpretation:

> The active well is 10.5% of the way through the Barail Lower Sand interval.

---

# 9. ξ-to-Depth Mapping in an Offset Well

Suppose the offset well has:

```text
Barail Lower Sand
Top  = 3180 m TVDSS
Base = 3640 m TVDSS
Thickness = 460 m
```

We want the same normalized position:

```text
xi = 0.105
```

Equivalent depth:

```text
equivalent_tvdss
= offset_top + xi * offset_thickness

= 3180 + 0.105 * 460
= 3228 m TVDSS
```

This lets us treat:

```text
Active well:
2986 m TVDSS
xi = 0.105

and

Offset well:
3228 m TVDSS
xi = 0.105
```

as a **geological analogue inside the same formation**, even though the absolute TVDSS values differ by 242 m.

This is the main difference between **raw depth matching** and **formation-normalized geological correlation**.

---

# 10. The Full Correlation Algorithm

Given:

```text
Active well A
Current depth d_active (TVDSS)
Offset well B
Formation tables for A and B
Historical NPT events in B
```

Do this:

### Step 1 — Identify Active Formation

```python
for formation in active_well.formations:
    if formation.top_tvdss <= d_active < formation.base_tvdss:
        current_formation = formation.name
        break
```

### Step 2 — Calculate Active Xi

```python
xi_active = (
    d_active - formation.top_tvdss
) / formation.thickness
```

### Step 3 — Find Same Formation in Offset Well

If the offset did not penetrate that formation:

```text
correlation = unavailable
confidence = zero / not_applicable
```

Do not fabricate a depth.

### Step 4 — Map Xi Into Offset

```python
equivalent_depth = (
    offset_formation.top_tvdss
    + xi_active * offset_formation.thickness
)
```

### Step 5 — Search Historical Events

Initial recommended window from Module 4:

```text
±50 m TVDSS
```

So if equivalent depth is `3228 m`:

```text
search interval = 3178–3278 m TVDSS
```

### Step 6 — Attach Evidence

Each event should retain:

```text
well_id
formation
depth
hazard/event type
severity
description
mitigation
document_id
page_number
bbox
```

The engineer should be able to inspect the source PDF/page for any important historical claim.

---

# 11. NPT — Non-Productive Time

**NPT = Non-Productive Time.**

It is time spent on an operational problem rather than planned productive drilling activity.

Relevant event classes for this system include:

```text
LOST_CIRCULATION
STUCK_PIPE
GAS_KICK
FISHING
TORQUE_SPIKE
CEMENTING_ISSUE
WELL_CONTROL
FORMATION_DAMAGE
OTHER_OPERATIONAL_EVENTS
```

NPT events are the historical evidence layer that makes offset-well intelligence useful to the engineer.

---

# 12. Hazard/Event Evidence

A useful NPT record:

```json
{
  "well_id": "NHK-089",
  "event_type": "LOST_CIRCULATION",
  "depth_tvdss": 3228,
  "formation": "Barail Lower Sand",
  "severity": 4,
  "description": "Total mud losses at 3228 m TVDSS",
  "mitigation": "Nut plug",
  "document_id": "DDR-2015-089",
  "page_number": 17,
  "bbox": [x0, y0, x1, y1]
}
```

This is much stronger than an LLM statement with no source.

---

# 13. How Historical Document Intelligence Fits In

The problem expects AI/NLP/OCR to extract historical information from reports.

## Inputs

```text
WCR
DDR
Mud logs
Drilling records
Casing records
Cementing records
Mud programs
Trajectory/survey files
Other operational documents
```

## Pipeline

```text
PDF / Scan
   |
   v
PDF parsing / rasterization
   |
   +--> text extraction
   |
   +--> OCR / VLM for scans
   |
   v
Structured extraction
   |
   v
Validation + normalization
   |
   +--> Wells
   +--> Formation tops
   +--> NPT events
   +--> Mud weights
   +--> Casing
   +--> Cementing
   +--> Survey
   |
   v
PostgreSQL / PostGIS
   + vector index where required
```

**Important architecture rule:** The LLM should help turn unstructured documents into structured records. The geological correlation math should remain deterministic and auditable.

---

# 14. DDR and WCR

## DDR — Daily Drilling Report

An operational report describing what happened during drilling over a specific day/time period.

Likely useful fields:

```text
Date/time
Depth
ROP
RPM
WOB
Mud weight
Flow
Pressure
Activities
NPT
Hazards
Mitigation
Remarks
```

Actual available fields depend on OIL's documents.

## WCR — Well Completion Report

A more complete historical record of a well, often including:

```text
well metadata
formation tops
trajectory
casing
cementing
completion
formation/reservoir information
well history
```

Do not assume every WCR/DDR has the same layout; legacy document variation is part of the problem.

---

# 15. Public SIH26121 Research

We reviewed public GitHub implementations and technical descriptions around SIH26121.

## 15.1 Public Problem Statement Sources

- [ace-ify/sih-hub — SIH26121](https://github.com/ace-ify/sih-hub/blob/main/ps/SIH26121.md)
- [xarjunpatil — SIH26121 repository](https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well)
- [pallavi-a11y/eRTMAC-NWIS](https://github.com/pallavi-a11y/eRTMAC-NWIS)
- [tarumishra22/eRTMAC-NWIS](https://github.com/tarumishra22/eRTMAC-NWIS)
- [n3ssdub3y/SIH_2026_PLANNS](https://github.com/n3ssdub3y/SIH_2026_PLANNS)
- [thor11223344/PetrolQ](https://github.com/thor11223344/PetrolQ)

Research date: **27 September 2026**.

---

# 16. Public Repo #1 — NWIS-Sentinel / n3ssdub3y

Repository:

https://github.com/n3ssdub3y/SIH_2026_PLANNS

Relevant architecture:

https://github.com/n3ssdub3y/SIH_2026_PLANNS/blob/main/ARCHITECTURE.md

## What they built

Their published architecture separates:

```text
Module 1 — Data Foundation / NLP
Module 2 — Geospatial + AHP Offset-Well Similarity
Module 3 — Real-Time Telemetry + Anomaly Detection
Module 4 — Knowledge Graph + GraphRAG
Module 5 — Engineering Decision Support Agent
```

Their published architecture describes a dataset consisting of:

```text
118 FORCE wells
1 Volve well
40 synthetic wells
1,959 events
16,670 WITSML rows
```

Their architecture says Module 2 computes analog-well ranking for multiple hazards.

## Their AHP engine

AHP = **Analytic Hierarchy Process**.

Their similarity engine compares multiple features, including:

```text
Formation
Mud weight
BHA type
Mud type
Trajectory
```

The published architecture states:

- Formation similarity via Jaccard similarity.
- Mud-weight similarity via a Gaussian distance function.
- BHA similarity via token Jaccard.
- Mud-type similarity via token Jaccard.
- Trajectory similarity via Fast Dynamic Time Warping (FastDTW) over inclination profiles.
- Hazard-specific AHP weights.

They compute a weighted score:

```text
Similarity(well_i, hazard_h)
    = Σ [weight(h,k) × similarity_k(well_i, target)]
```

They also expose an analog ranking API and output `formation_correlation.json`.

## Why it matters to us

This is useful prior art for **offset-well similarity**, especially:

```text
trajectory comparison
hazard-specific weighting
feature-level explainability
analog ranking
```

## What is different from our Module 4

The public implementation emphasizes **well similarity**, whereas our Module 4 needs an explicit **geological horizon mapping mechanism**:

```text
MD -> TVDSS -> formation -> xi -> offset equivalent depth
```

We did not find public evidence in the inspected repository of a normalized `xi` implementation equivalent to ours.

**Take from them:** hazard-specific similarity and trajectory alignment.  
**Do not simply replace geological correlation with a generic similarity score.**

---

# 17. AHP — Analytic Hierarchy Process

AHP is a multi-criteria decision method.

It is useful when we want to combine several relevance dimensions into one score.

For example:

```text
Distance
Geological match
Trajectory match
Mud similarity
BHA similarity
```

AHP typically works by:

```text
1. Define criteria
2. Build pairwise-comparison matrix
3. Derive weights
4. Check consistency
5. Combine feature scores
```

NWIS-Sentinel's published design uses Saaty-style pairwise weighting and reports a consistency-ratio check.

For our first implementation, fixed configurable weights are simpler. AHP can be introduced once the base engine works.

---

# 18. FastDTW / DTW — Trajectory Similarity

DTW = **Dynamic Time Warping**.

It compares two sequences even when their patterns are stretched/compressed differently along the sequence index.

For trajectory comparison:

```text
Well A inclination profile:
[0, 2, 8, 20, 30, 35, 35, 35]

Well B inclination profile:
[0, 1, 7, 15, 28, 34, 35, 35]
```

A DTW-type similarity can recognize similar trajectory shape even when the changes occur at different MD values.

Public NWIS-Sentinel architecture uses FastDTW for inclination-profile similarity.

This is a candidate enhancement for our trajectory score.

---

# 19. Public Repo #2 — pallavi-a11y/eRTMAC-NWIS

Repository:

https://github.com/pallavi-a11y/eRTMAC-NWIS

## What they built

The public project describes an offline document-intelligence system based on:

```text
PDF rasterization
Qwen2.5-VL 3B via Ollama
Structured extraction
SQLite
Qdrant
FastAPI
React + Vite
Leaflet
RAG assistant
Human-in-the-loop review
```

Their project structure contains components for:

```text
pdf_processor.py
unified_parser.py
table_parser.py
figure_extractor.py
vector_store.py
rag_engine.py
hazard_monitor.py
database.py
```

## Especially useful idea: source provenance

Their project retains document/page context for extracted hazards and supports a review UI where extraction can be corrected.

This supports an important requirement for our system:

> Every important historical hazard claim should be traceable to the source document/page.

## What their Risk Monitor does

The public description says the system uses nearby wells and a configurable depth window for historical hazard correlation.

This is useful as a baseline but is fundamentally simpler than our geological normalization approach.

Conceptually:

```text
nearby well
+
raw depth proximity
+
historical hazard
=
alert candidate
```

Our target:

```text
nearby well
+
formation match
+
xi-equivalent depth
+
historical hazard
=
geological analogue evidence
```

**Take from them:** VLM/OCR pipeline, human review, provenance, offline architecture.  
**Do not use raw depth proximity as the entire geological correlation algorithm.**

---

# 20. Public Repo #3 — tarumishra22/eRTMAC-NWIS

Repository:

https://github.com/tarumishra22/eRTMAC-NWIS

Their README describes:

```text
FastAPI
Python
ChromaDB
PyPDF
Geopy
React 19
Vite
Leaflet
```

They provide a tactical three-pane concept:

```text
Pane 1: Geospatial Discovery
Pane 2: Subterranean Twin
Pane 3: Proactive Advisor
```

They also describe:

```text
spatial / distance decay
vertical depth proximity
formation matching
vector RAG
historical hazard retrieval
```

## Why it matters

Their UI layout is useful for our cockpit.

The visual organization is approximately:

```text
Map          | Subsurface / correlation
-------------+---------------------------
Offset list  | Proactive risk / advice
```

## Limitation for our core correlation

The public risk-engine approach is much closer to:

```text
distance
+
depth window
+
formation factor
+
severity
```

than to true TVDSS/xi-based geological normalization.

**Take from them:** cockpit structure and visual synchronization.  
**Do not treat simple depth-window matching as final subsurface correlation.**

---

# 21. Public Repo #4 — PetrolQ

Repository:

https://github.com/thor11223344/PetrolQ

This is a larger public full-stack implementation.

The README currently describes:

```text
React 19 / Vite
MapLibre
Plotly WebGL
FastAPI
PostgreSQL
PostGIS
pgvector
LightGBM
SHAP
FastDTW
PyMuPDF
pdfplumber
EasyOCR
bge-small-en-v1.5
AHP
RAG
physics + ML hybrid hazard engine
```

It also describes:

- Multi-signal hybrid retrieval.
- Formation Jaccard.
- Depth-decay scoring.
- Event taxonomy matching.
- BM25.
- Dense vector similarity.
- AHP weighting.
- Petroleum-physics calculations.
- ML hazard classification.
- SHAP local attribution.
- Backtesting/time-travel replay.
- Safety guardrails.

## What to study from it

```text
PostGIS spatial architecture
well/event database structure
hybrid retrieval design
physics + ML separation
backtesting
explainability
safety gate concepts
```

## Important caution

Its public data/methodology documentation includes open industry datasets and synthetic/calibrated data. Public demo data should not be presented as proof of OIL-private field accuracy.

We must distinguish:

```text
public benchmark demo
vs
real OIL operational deployment
```

---

# 22. Public Repo #5 — xarjunpatil/SIH26121...

Repository:

https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well

The repository includes:

```text
HTML demo
FastAPI backend
PostgreSQL/PostGIS-oriented documentation
Docker
Tests
Technical whitepaper
```

However, inspection of the public implementation showed that some risk/telemetry outputs rely on mock/randomized values rather than a fully grounded subsurface model.

This is important for our process:

> Never assume a sophisticated README proves that the domain engine is actually implemented.

We need to audit public solutions from:

```text
README
    +
actual source code
    +
actual data
    +
actual test behavior
```

---

# 23. What the Public Ecosystem Is Mostly Doing

Across the public implementations we inspected, there are roughly three patterns.

## Pattern A — Proximity Correlation

```text
geographic distance
+
raw depth difference
+
formation match
=
historical hazard candidate
```

Simple and demo-friendly.

## Pattern B — Analog-Well Similarity

```text
formation similarity
+
mud similarity
+
BHA similarity
+
trajectory similarity
+
distance
=
analog-well score
```

More sophisticated. NWIS-Sentinel is a good example.

## Pattern C — Retrieval/RAG Layer

```text
candidate offset wells
        |
        v
historical events/documents
        |
        v
vector / lexical / graph retrieval
        |
        v
LLM explanation / briefing
```

Useful once the underlying structured correlation is trustworthy.

---

# 24. What We Should Build Instead

Our design should combine the strongest ideas without copying the weakest assumptions.

## Core difference

Public implementations often ask:

> Is there a historical event at a similar raw depth in a nearby well?

Our system should ask:

> What geological position is the active bit currently occupying, and where is that same stratigraphic position in each offset well?

That gives us:

```text
MD
 |
v
TVDSS
 |
v
Formation
 |
v
xi
 |
v
Equivalent offset depth
 |
v
Historical event evidence
```

This is the backbone of our Module 4 design.

---

# 25. Proposed Final Architecture

```text
                           +----------------------+
                           | Historical Documents |
                           | DDR / WCR / Logs     |
                           +----------+-----------+
                                      |
                                      v
                          +-----------------------+
                          | Ingestion / OCR / VLM |
                          +-----------+-----------+
                                      |
                                      v
                          +-----------------------+
                          | Structured Normalized |
                          | Well Knowledge Base   |
                          +----+-----+-----+------+
                               |     |     |
                 +-------------+     |     +----------------+
                 |                   |                      |
                 v                   v                      v
           Survey Data        Formation Tops          NPT Events
                 |                   |                      |
                 v                   v                      |
          Minimum Curvature   Geological Model             |
                 |                   |                      |
                 v                   |                      |
               TVDSS ----------------+                      |
                 |                                          |
                 +-------------------+----------------------+
                                     |
                                     v
                           +---------------------+
                           | Xi Correlation Core |
                           +----------+----------+
                                      |
                                      v
                         Equivalent Geological Horizon
                                      |
                                      v
                           +----------------------+
                           | Offset Ranking Engine|
                           | Omega / AHP / DTW   |
                           +----------+-----------+
                                      |
                                      v
                            Top Relevant Offsets
                                      |
                                      v
                          +--------------------------+
                          | Historical Event Search  |
                          | +/- depth around mapped  |
                          | equivalent horizon       |
                          +------------+-------------+
                                       |
                                       v
                               Historical Evidence
                                       |
                    +------------------+------------------+
                    |                                     |
                    v                                     v
             Risk Corridor                         Engineer UI
             +50 to +200 m                          Map / Logs
             +20 to +50 m                           Correlation
             0 to +20 m                             Alerts
                    |                               Evidence
                    +------------------+------------------+
                                       |
                                       v
                                Recommendation
                              + Human approval
```

---

# 26. Technology Stack We Should Use

## Backend

Recommended:

```text
Python
FastAPI
Pydantic
NumPy
SciPy
Pandas
PostgreSQL
PostGIS
```

## Document Processing

Depending on input quality:

```text
PyMuPDF
pdfplumber
OCR engine
VLM for difficult scanned layouts
OpenCV for charts/tables
```

## Retrieval

Use when justified:

```text
BM25 / lexical retrieval
pgvector or Qdrant
embeddings
```

## Frontend

```text
React
Vite / Next.js
Tailwind
MapLibre / Leaflet
Plotly / ECharts / custom SVG
```

## Real-Time

```text
WebSocket
```

For a demo, a simulated telemetry stream is enough initially.

---

# 27. Recommended Database Schema

## `wells`

```text
id
well_name
field
basin
latitude
longitude
wellhead_elevation_m
status
spud_date
completion_date
```

## `survey_stations`

```text
id
well_id
md_m
inclination_deg
azimuth_deg
north_m
east_m
tvd_m
tvdss_m
method
```

## `formations`

```text
id
formation_name
canonical_name
```

## `formation_tops`

```text
id
well_id
formation_id
top_md_m
top_tvdss_m
base_md_m
base_tvdss_m
thickness_m
confidence
source_document_id
source_page
```

Confidence examples:

```text
OBSERVED
INFERRED
IMPUTED
EXTRAPOLATED
```

## `npt_events`

```text
id
well_id
event_type
depth_md_m
depth_tvdss_m
formation_id
severity
duration_minutes
description
mitigation
source_document_id
source_page
bbox_x0
bbox_y0
bbox_x1
bbox_y1
confidence
```

## `mud_records`

```text
id
well_id
depth_md_m
depth_tvdss_m
formation_id
mud_weight
unit
source_document_id
source_page
```

## `casing_records`

```text
id
well_id
casing_type
shoe_depth_md_m
shoe_depth_tvdss_m
diameter
cement_program
source_document_id
source_page
```

## `correlation_results`

```text
id
active_well_id
offset_well_id
active_depth_tvdss
formation_id
xi
 equivalent_depth_tvdss
omega_score
correlation_confidence
created_at
```

---

# 28. Module 4 Core Python Package Layout

```text
module4/
├── __init__.py
├── models.py
├── units.py
├── survey/
│   ├── minimum_curvature.py
│   └── interpolation.py
├── geology/
│   ├── formation.py
│   ├── xi.py
│   └── uncertainty.py
├── correlation/
│   ├── equivalent_depth.py
│   ├── event_matcher.py
│   └── correlation_engine.py
├── ranking/
│   ├── distance.py
│   ├── trajectory.py
│   ├── ahp.py
│   └── omega.py
├── risk/
│   ├── corridor.py
│   └── aggregation.py
├── evidence/
│   └── provenance.py
└── tests/
    ├── test_minimum_curvature.py
    ├── test_xi.py
    ├── test_equivalent_depth.py
    ├── test_ranking.py
    └── test_corridor.py
```

---

# 29. Core Functions We Need

```python
def survey_to_tvdss(survey, wellhead_elevation):
    ...


def interpolate_tvdss(survey, md):
    ...


def find_current_formation(depth_tvdss, formation_tops):
    ...


def compute_xi(depth_tvdss, formation_top, formation_base):
    ...


def xi_to_tvdss(xi, offset_top, offset_base):
    ...


def correlate_events(active_well, offset_well, depth_tvdss):
    ...


def compute_distance_score(distance_km, max_distance_km=50):
    ...


def compute_geological_score(...):
    ...


def compute_trajectory_score(...):
    ...


def compute_omega(...):
    ...


def compute_risk_corridor(...):
    ...
```

---

# 30. Offset-Well Ranking — Ω (Omega)

The Module 4 specification gives a default relevance score:

```text
Ω(w,z)
 = w1 * S_distance
 + w2 * S_geological
 + w3 * S_trajectory
 + w4 * S_completion
```

Default weights:

```text
w1 = 0.25
w2 = 0.40
w3 = 0.20
w4 = 0.15
```

All component scores should be normalized.

---

# 31. Distance Score

One simple form from the Module 4 design:

```text
score = 1 - distance_km / max_distance_km
```

with:

```text
max_distance_km = 50 by default
```

Clamp the output to `[0,1]`.

In production, geodesic/PostGIS calculations are preferred over hand-written planar distance approximations for geographic coordinates.

---

# 32. Geological Score

The initial Module 4 design uses:

```text
S_geological
 = 0.5 * formation_match_flag
 + 0.5 * npt_cluster_match
```

Where:

```text
formation_match_flag = 1 if formation exists in offset well else 0
```

and:

```text
npt_cluster_match
= proportion of offset events within a chosen xi tolerance
```

This can later be expanded with:

```text
xi overlap
lithology similarity
reservoir similarity
formation-top confidence
structural continuity
```

---

# 33. Trajectory Score

The Module 4 baseline suggests azimuth similarity.

A stronger implementation inspired by public prior art should consider:

```text
azimuth similarity
inclination profile similarity
trajectory shape similarity
possibly dogleg profile similarity
```

DTW/FastDTW can be used for profile alignment.

**Implementation strategy:** keep the simple deterministic score first; add DTW as an optional enhancement after tests pass.

---

# 34. Completion Score

The Module 4 baseline gives example heuristics such as:

```text
both vertical                         -> 1.0
one vertical / one deviated           -> 0.5
both deviated, similar inclination    -> 0.9
```

This is a configurable feature, not a fundamental law of geology.

Treat it as a relevance heuristic rather than as a physical correlation rule.

---

# 35. Hazard-Specific Ranking — Improvement From Public Research

NWIS-Sentinel's public architecture provides a useful idea: different hazards can require different analog criteria.

For example:

```text
Lost circulation
    -> formation + mud-weight context

Stuck pipe
    -> trajectory + BHA + formation

Overpressure / kick
    -> mud-weight + formation + pressure evidence

Torque spike
    -> trajectory + BHA + mud/lubricity context

Cementing
    -> casing + mud + formation context
```

Therefore, after the base Omega engine works, implement:

```text
Omega_hazard(w, z, hazard_type)
```

rather than assuming one universal ranking is perfect for every event class.

---

# 36. Risk Corridor

The active bit should not only examine the current horizon.

It should inspect what lies ahead.

Module 4 defines three forward windows:

```text
+50 to +200 m    PROACTIVE
+20 to +50 m     WARNING
0 to +20 m       IMMINENT
```

A simple implementation:

```python
lookahead_depths = np.arange(
    current_tvdss,
    current_tvdss + 200,
    10,
)
```

For every projected depth:

```text
future TVDSS
    |
    v
future formation
    |
    v
future xi
    |
    v
xi -> equivalent depth in offset wells
    |
    v
historical events
    |
    v
aggregate hazard evidence
```

---

# 37. Risk Corridor Output

Suggested JSON:

```json
{
  "active_well": "NHK-412",
  "current_tvdss": 2986,
  "points": [
    {
      "tvdss": 3000,
      "lost_circulation_risk": 2.1,
      "stuck_pipe_risk": 0.7,
      "gas_kick_risk": 0.2,
      "evidence_count": 2
    },
    {
      "tvdss": 3020,
      "lost_circulation_risk": 4.5,
      "stuck_pipe_risk": 1.0,
      "gas_kick_risk": 0.3,
      "evidence_count": 4
    }
  ]
}
```

Do not call a raw aggregated historical count a calibrated probability unless the model has actually been trained/calibrated to produce probabilities.

Prefer language such as:

```text
historical risk score
historical event density
historical evidence strength
```

until a statistical calibration pipeline exists.

---

# 38. Formation Top Uncertainty

Formation tops may be:

```text
observed
inferred
imputed
extrapolated
```

The Module 4 document provides an uncertainty-propagation formula for xi:

```text
xi_uncertainty = sqrt(
    (sigma_top / thickness)^2
    + (
        sigma_thickness
        * (d-top)
        / thickness^2
      )^2
)
```

If uncertainty becomes large, the UI should explicitly show:

```text
Correlation confidence: LOW
Reason: formation top inferred / uncertain
```

The system should never hide uncertainty to make the demo look better.

---

# 39. Missing Formation Tops

Real historical wells may lack digitized formation tops.

Three candidate approaches from the Module 4 design:

## Strategy 1 — Lithology-based inference

Example:

```text
DDR says: "sand encountered at 3218 m"
Known regional expectation: Barail Lower Sand
=> infer formation top
```

Confidence:

```text
INFERRED
```

## Strategy 2 — Neighbor imputation

Use nearby known wells:

```text
neighbor tops:
2900
3000
3150

median = 3000
```

Confidence:

```text
IMPUTED
```

## Strategy 3 — Structural dip extrapolation

If regional dip is known:

```text
depth correction ≈ dip relationship × distance
```

Confidence:

```text
EXTRAPOLATED
```

**Build order:** observed data first, then inferred/imputed/extrapolated logic.

---

# 40. Fault Block Detection

A geological correlation can fail for a legitimate geological reason.

Example:

```text
Active well
     |
     | geological fault
     |
Offset well
```

The Module 4 design proposes a heuristic based on:

```text
offset distance
+
low correlation score
+
high NPT history in offset formation
```

and flags a potential fault boundary.

This should be presented as:

```text
POTENTIAL STRUCTURAL DISCONTINUITY
```

not as a confirmed geological interpretation unless supported by actual structural data.

---

# 41. Mud Window / PP-FG Chart

Another Module 4 feature is the **Mud Window**, also known as a drilling margin / PP-FG chart.

## PP — Pore Pressure

Pressure of fluids in the formation.

For safe drilling, mud pressure should generally be sufficient to avoid unwanted formation-fluid influx.

## FG — Fracture Gradient

The formation pressure/gradient limit beyond which the formation may fracture and take mud.

## Mud Window

The interval between:

```text
Pore Pressure
        |
        |   SAFE MUD WINDOW
        |
Fracture Gradient
```

Conceptually:

```text
mud too light
    -> kick / influx risk

mud too heavy
    -> fracture / lost-circulation risk
```

---

# 42. How Our Mud Window Should Use Offset Data

Instead of only drawing theoretical lines:

```text
offset actual mud weights
+
xi correlation
+
historical kick events
+
historical lost-circulation events
```

can be displayed at equivalent positions on the active-well chart.

This turns the mud-window chart into an **evidence-backed offset analogue tool**.

Possible layers:

```text
Pore pressure estimate
Fracture gradient estimate
Current mud weight
Offset actual mud weights
Historical kick markers
Historical lost-circulation markers
```

The exact PP/FG equations should be implemented only after validating units, assumptions, and data availability.

---

# 43. PP / FG Equations in the Existing Module Specification

The Module 4 source proposes several methods, including:

- Eaton-style pore-pressure estimation from drilling trends.
- Direct lower-bound evidence from the mud weight associated with a historical kick.
- Hubbert-Willis-type fracture-gradient approximation.
- Eaton fracture-gradient formulation using Poisson's ratio.

These are domain models with significant assumptions.

**For SIH MVP:** label model-based curves as estimates and prioritize transparent historical evidence rather than pretending demo parameters are OIL-calibrated measurements.

---

# 44. Engineer-in-the-Loop

The system is a **decision-support system**, not an autonomous rig controller.

Every important alert should allow the engineer to:

```text
ACKNOWLEDGE / IMPLEMENT
ACKNOWLEDGE / OVERRIDE
ESCALATE
```

For an override, record:

```text
timestamp
alert_id
user
action
engineer_note
```

This creates an audit trail.

A critical rule:

> No LLM response should directly command a physical drilling system.

---

# 45. Evidence Provenance

Every historical event should have:

```text
document_id
page_number
bounding box if available
extracted text
extraction confidence
review status
```

Example UI:

```text
Historical event: LOST CIRCULATION
Well: NHK-089
Equivalent depth: 3228 m TVDSS
Source: DDR-2015-089
Page: 17

[OPEN SOURCE PAGE]
```

The engineer should be able to inspect the original source instead of trusting a black-box AI statement.

---

# 46. RAG — Retrieval-Augmented Generation

RAG means:

```text
Retrieve relevant evidence
        |
        v
Give evidence to LLM
        |
        v
Generate grounded answer
```

For this system, RAG is useful for questions such as:

```text
"What mitigation was used when NHK-089 experienced losses in Barail Lower Sand?"

"Which nearby wells had stuck-pipe problems around the current horizon?"

"Show historical evidence for this alert."
```

RAG should sit **on top of structured correlation**, not replace it.

Bad design:

```text
LLM guesses which PDF is relevant.
```

Better design:

```text
xi/formation engine finds relevant offset/horizon
            |
            v
retriever finds source evidence
            |
            v
LLM summarizes only retrieved evidence
```

---

# 47. Vector Database

A vector DB stores embedding representations for semantic retrieval.

Examples seen in public projects:

```text
Qdrant
ChromaDB
pgvector
```

Use vectors for:

```text
semantic document search
mitigation similarity
lesson-learned retrieval
free-text engineer questions
```

Do not use vector similarity as the sole method for:

```text
formation position
TVDSS conversion
wellbore geometry
exact depth correlation
```

Those need deterministic/geological logic.

---

# 48. PostGIS

PostGIS extends PostgreSQL with geospatial capabilities.

Useful for:

```text
wellhead coordinates
spatial radius queries
geodesic distance
spatial indexing
fault polygons
field/basin polygons
```

Example query concept:

```text
Find wells within 10 km of active well.
```

Then the correlation engine can perform a second filter:

```text
same formation
```

and then the third:

```text
same xi horizon
```

This is much better than doing everything as one fuzzy similarity query.

---

# 49. Suggested Retrieval Order

Use a cascade so the expensive steps run only where useful.

```text
STEP 1
Spatial filter
        |
        v
Nearby wells
        |
STEP 2
Historical/data availability filter
        |
        v
Wells with needed formation/event/survey data
        |
STEP 3
TVDSS + formation filter
        |
        v
Wells that penetrate relevant formation
        |
STEP 4
Xi correlation
        |
        v
Geological analogue candidates
        |
STEP 5
Omega ranking
        |
        v
Top offsets
        |
STEP 6
Historical event retrieval
        |
        v
Evidence
        |
STEP 7
RAG / briefing
```

---

# 50. API Design

## Current Geological Position

```http
GET /api/correlation/xi?active_well={id}&depth_tvdss={d}
```

Response:

```json
{
  "current_formation": "Barail Lower Sand",
  "xi_value": 0.105,
  "offset_well_equivalent_depths": [
    {
      "well_id": "NHK-089",
      "tvdss": 3228
    }
  ]
}
```

## Risk Corridor

```http
GET /api/correlation/risk_corridor?active_well={id}&depth_tvdss={d}&lookahead_m=200
```

## Offset Ranking

```http
GET /api/offset_ranking?active_well={id}&depth_tvdss={d}
```

## Formation Tops

```http
GET /api/formation_tops/{well_id}
```

## Historical Evidence

Recommended addition:

```http
GET /api/correlation/events?active_well={id}&offset_well={id}&depth_tvdss={d}
```

## Source Document

```http
GET /api/documents/{document_id}/pages/{page}
```

---

# 51. WebSocket / Live Depth

The dashboard should be capable of receiving:

```json
{
  "well_id": "NHK-412",
  "md": 3200,
  "tvdss": 2986,
  "timestamp": "..."
}
```

Every new depth update can trigger:

```text
recalculate formation
recalculate xi
recalculate equivalent offset depths
recalculate offset ranking
recalculate risk corridor
update UI
```

For the first demo, a simulated depth stream is enough.

---

# 52. Frontend — Main Cockpit

Recommended layout:

```text
+------------------------------------------------------------------+
| ACTIVE WELL | MD | TVDSS | FORMATION | XI | SYSTEM STATUS       |
+--------------------------+---------------------------------------+
|                          |                                       |
| GEOSPATIAL WELL MAP      | WELL CORRELATION PANEL                |
|                          |                                       |
| Active well              | Well A | Well B | Well C | Well D    |
| Offset wells             | formation blocks                     |
| Radius                   | xi-equivalent horizontal line        |
| Fault boundaries         | NPT event markers                   |
|                          |                                       |
+--------------------------+---------------------------------------+
| OFFSET RANKING           | AHEAD-OF-BIT RISK CORRIDOR            |
|                          |                                       |
| #1 well / Omega          | depth  risk  event evidence           |
| #2 well / Omega          | depth  risk  event evidence           |
| #3 well / Omega          | depth  risk  event evidence           |
+--------------------------+---------------------------------------+
| HISTORICAL EVIDENCE / SOURCE DOCUMENT VIEWER                     |
+------------------------------------------------------------------+
```

---

# 53. Well Correlation Panel

This is the **stick-plot / correlation-panel** idea from our Module 4 design.

For each offset well show:

```text
Formation 1
Formation 2
Formation 3
Formation 4
```

with the active correlation horizon drawn across the wells at the **xi-equivalent position**.

Event markers:

```text
red/orange marker = historical hazard
```

Clicking an event should open the source evidence.

This provides an immediate visual answer to:

```text
Where are we?
Where is the same geological position in other wells?
What happened there?
```

---

# 54. Demo Scenario We Should Build

Use the worked example from our Module 4 source.

## Active well

```text
NHK-412
MD = 3200 m
TVDSS = 2986 m
```

## Active formation

```text
Barail Lower Sand
Top  = 2940
Base = 3380
Thickness = 440
```

## Xi

```text
xi = 0.105
```

## Offset

```text
NHK-089
Top  = 3180
Base = 3640
Thickness = 460
```

## Equivalent depth

```text
3228 m TVDSS
```

## Event query

```text
3178–3278 m TVDSS
```

## Historical result

```text
LOST CIRCULATION
Historical mitigation: nut plug
```

This is the first end-to-end test case.

---

# 55. MVP Data Strategy

Do **not** begin by trying to digitize hundreds of OIL wells.

Start with a small deterministic test corpus:

```text
10–20 wells
5–10 formations
50–200 events
survey data for at least several wells
```

Create seed CSV/JSON files for development.

Recommended initial files:

```text
data/
├── wells.csv
├── surveys.csv
├── formation_tops.csv
├── npt_events.csv
├── mud_records.csv
├── casing_records.csv
└── documents.csv
```

Once the core correlation works, connect the real document-extraction pipeline.

---

# 56. Why We Should Build CSV-First

If the mathematical engine cannot work on clean seed data, adding OCR and RAG will only hide bugs.

The correct order is:

```text
CSV
 |
v
Database
 |
v
Correlation engine
 |
v
API
 |
v
UI
 |
v
Document ingestion
 |
v
RAG
```

This separates:

```text
data ingestion problem
from
geological correlation problem
```

which makes debugging far easier.

---

# 57. Validation — How Do We Know Correlation Is Correct?

A major question is:

> How do we know the correlation isn't just producing plausible-looking numbers?

Our validation plan should have multiple layers.

---

# 58. Validation A — Formation Sanity

Compare the same formation across wells.

Check:

```text
formation tops
formation thickness
TVDSS consistency
```

Outliers should be flagged.

---

# 59. Validation B — Structural Cross-Section

Order wells geographically/structurally and plot formation tops.

We should expect smooth geological trends where the geology is continuous.

Sharp discontinuities may be:

```text
fault
structural break
bad data
wrong formation pick
```

The important engineering point is:

> A discontinuity is not automatically an algorithm error.

---

# 60. Validation C — Event Clustering by Formation

After xi mapping, examine whether event classes cluster in plausible formation intervals.

Example:

```text
Lost circulation events
    -> predominantly within relevant sand/formation interval

Stuck pipe events
    -> predominantly in relevant shale/coal interval
```

Unexpected scattering can indicate:

```text
formation-top errors
bad event depths
bad extraction
incorrect correlation
```

---

# 61. Validation D — Blind Prediction

This is the most important practical test.

Procedure:

```text
1. Take a historical well.
2. Hide its actual NPT events.
3. Run correlation using other wells.
4. Predict risky horizons.
5. Reveal the hidden events.
6. Compare predictions to reality.
```

Metrics:

```text
precision
recall
lead distance
lead time
false-alert rate
calibration if probabilistic model is used
```

The Module 4 source proposes a 70%+ prediction target under a specific equivalent-depth tolerance as a demo engineering acceptance criterion. Treat this as a **project acceptance target**, not a universally valid industry standard.

---

# 62. Validation E — Evidence Traceability

For every displayed historical alert:

```text
Can we identify the exact source?
Can we identify the page?
Can we show the extracted text?
Can we show the original page image?
```

A system that says “risk is high” with no evidence is much harder to defend.

---

# 63. Testing Strategy

## Unit Tests

```text
test_vertical_well_tvdss
test_deviated_well_tvdss
test_missing_survey_fallback
test_formation_lookup
test_xi_top_is_zero
test_xi_base_is_one
test_xi_outside_formation
test_equivalent_depth_mapping
test_event_window
```

## Integration Tests

```text
survey -> TVDSS -> formation -> xi -> offset -> event
```

## Regression Tests

Store known outputs for the worked numerical example.

If code changes and:

```text
2986 TVDSS
0.105 xi
3228 offset depth
```

suddenly become different without an intentional change, the test should fail.

---

# 64. Important Units Policy

Petroleum engineering data contains many units.

Do not store unitless numbers unless the schema explicitly defines the unit.

Examples:

```text
Depth          -> m
Distance       -> km / m
Inclination    -> degree
Azimuth        -> degree
Mud weight     -> g/cc or ppg
Pressure       -> psi / bar / MPa
Flow           -> L/min or bbl/min
Volume         -> bbl
Time           -> minutes / hours
```

Normalize internally.

Example policy:

```text
internal depth = meters
internal geographic coordinates = EPSG:4326
```

---

# 65. Confidence Model

Every correlation should expose confidence factors.

Possible components:

```text
survey confidence
formation-top confidence
formation-name normalization confidence
xi uncertainty
NPT event extraction confidence
source quality
structural continuity
```

Example:

```json
{
  "correlation_confidence": "MEDIUM",
  "reasons": [
    "survey observed",
    "formation top inferred",
    "event extracted from scanned DDR"
  ]
}
```

---

# 66. What AI Should Do

AI is useful for:

```text
OCR/VLM
entity extraction
formation/event normalization
document summarization
semantic retrieval
mitigation similarity
natural-language engineer queries
```

AI should **not** silently determine:

```text
TVDSS from raw numbers
wellbore geometry
xi equation
exact depth transformations
whether two points are physically equivalent
```

Those calculations should be deterministic and inspectable.

---

# 67. What ML Should Do Later

Once historical data is sufficiently structured, ML can predict:

```text
lost circulation
stuck pipe
kick/overpressure
 torque spikes
cementing issues
```

Potential model families:

```text
LightGBM / XGBoost
Random Forest
Logistic Regression
sequence models
anomaly detection
```

Explainability:

```text
SHAP
feature contribution tables
similar historical wells
```

But ML is an enhancement layer. The core offset correlation can exist before ML.

---

# 68. Suggested Final Risk Architecture

```text
Historical Evidence
        |
        v
Geological Correlation
        |
        v
Relevant Offset Wells
        |
        +----------+
        |          |
        v          v
Historical      Current Telemetry
Events               |
        |            |
        +-----+------+
              v
        Feature Builder
              |
       +------+------+
       |             |
       v             v
Physics         ML / Similarity
       |             |
       +------+------+
              v
        Risk Aggregator
              |
              v
       Evidence Validator
              |
              v
      Engineer Decision UI
```

---

# 69. What We Should NOT Do

## Do not start with an LLM agent

We need a working deterministic correlation core first.

## Do not use raw MD matching as geological truth

Different trajectories make raw MD non-comparable.

## Do not assume same TVDSS means same formation position

Structural position and formation thickness can differ between wells.

## Do not let an LLM invent historical events

Every historical claim should be evidence-backed.

## Do not call synthetic data “OIL data”

Clearly label benchmark/synthetic/demo data.

## Do not fake confidence

If a formation top is inferred, say so.

## Do not silently mix units

Normalize and validate.

---

# 70. Build Order — Exact Sequence

## Phase 1 — Geological math

Build and test:

```text
survey ingestion
Minimum Curvature
MD -> TVD
TVD -> TVDSS
interpolation
formation lookup
xi
xi -> offset depth
```

**Deliverable:** one active well can be correlated with one offset well.

---

## Phase 2 — Historical event correlation

Add:

```text
NPT events
formation association
±50m equivalent-depth search
source-document provenance
```

**Deliverable:** active depth returns historical events in equivalent geological positions.

---

## Phase 3 — Offset ranking

Add:

```text
spatial filter
formation match
xi cluster match
distance score
trajectory score
completion score
Omega
```

Then optionally:

```text
AHP
hazard-specific weights
DTW trajectory similarity
```

**Deliverable:** ranked offset wells with explainable scores.

---

## Phase 4 — Risk corridor

Add:

```text
+200m lookahead
10m sampling
future xi
future equivalent depths
historical event aggregation
```

**Deliverable:** ahead-of-bit risk corridor.

---

## Phase 5 — Frontend cockpit

Build:

```text
map
well list
correlation panel
offset ranking
risk corridor
evidence viewer
```

**Deliverable:** end-to-end visual demo.

---

## Phase 6 — Document intelligence

Connect:

```text
WCR/DDR ingestion
OCR/VLM
structured extraction
review screen
vector retrieval
```

**Deliverable:** historical reports automatically feed the correlation engine.

---

## Phase 7 — Predictive analytics

Add:

```text
ML hazard model
physics-informed features
SHAP/explainability
backtesting
```

**Deliverable:** predictive rather than purely historical correlation.

---

# 71. The First Coding Milestone

Before building anything visually impressive, make this exact Python test pass:

```python
active_depth = 2986
active_top = 2940
active_base = 3380

offset_top = 3180
offset_base = 3640

xi = (active_depth - active_top) / (active_base - active_top)

assert round(xi, 3) == 0.105

equivalent_depth = offset_top + xi * (offset_base - offset_top)

assert round(equivalent_depth, 0) == 3228
```

Then add:

```python
query_start = equivalent_depth - 50
query_end = equivalent_depth + 50

assert query_start == 3178
assert query_end == 3278
```

Then load one historical event at 3228 m and prove the matcher finds it.

**That is the first real proof that Module 4 works.**

---

# 72. Second Coding Milestone

Given:

```text
10 wells
```

run:

```text
active well
current depth
  -> current formation
  -> xi
  -> equivalent depth in all offsets
  -> event search
  -> Omega
  -> top 5 offsets
```

Output a JSON file:

```text
correlation_results.json
```

Then expose the same result through FastAPI.

---

# 73. Third Coding Milestone

Stream depth:

```text
2980
2990
3000
3010
...
3300
```

At each step update:

```text
formation
xi
offset equivalent horizons
Omega rankings
risk corridor
```

Then watch the UI reorder offsets as the bit crosses formations.

This is the strongest demonstration of a **dynamic geological context engine**.

---

# 74. How the Demo Story Should Be Told

Do not explain the project as:

> “We use AI to analyze nearby wells.”

That is too generic.

Instead show:

```text
CURRENT WELL
3,200m MD
       |
       v
2,986m TVDSS
       |
       v
BARAIL LOWER SAND
       |
       v
xi = 0.105
       |
       v
NHK-089 equivalent horizon = 3,228m TVDSS
       |
       v
Historical lost circulation found
       |
       v
Source DDR page opened
       |
       v
Risk corridor projects upcoming horizons
```

The judge should be able to follow the causal chain.

---

# 75. Main Engineering Insight

The fundamental distinction is:

```text
RAW PROXIMITY

"Two points are close in MD."
```

versus:

```text
GEOLOGICAL PROXIMITY

"Two points occupy the same normalized position
within the same formation, after wellbore and
structural differences have been accounted for."
```

Our Module 4 should be built around the second concept.

---

# 76. Final Target Architecture in One View

```text
             HISTORICAL OIL KNOWLEDGE
                      |
             +--------+--------+
             |                 |
          Documents         Structured data
             |                 |
        OCR / VLM          Wells / surveys
             |             formations / NPT
             +--------+--------+
                      |
                      v
                DATA NORMALIZER
                      |
       +--------------+--------------+
       |                             |
       v                             v
   GEOSPATIAL                    SUBSURFACE
    FILTER                        ENGINE
       |                             |
       v                             v
 nearby wells                 MD -> TVDSS
                                     |
                                     v
                              formation lookup
                                     |
                                     v
                                  xi
                                     |
                                     v
                           equivalent offset depth
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
               EVENT CORRELATION                WELL RANKING
                     |                         Omega / AHP / DTW
                     |                               |
                     +---------------+---------------+
                                     |
                                     v
                               RISK CORRIDOR
                                     |
                                     v
                         HISTORICAL + CURRENT DATA
                                     |
                                     v
                         EVIDENCE / ML / PHYSICS
                                     |
                                     v
                              ENGINEER UI
                                     |
                                     v
                           ACK / OVERRIDE / ESCALATE
```

---

# 77. Public Research Conclusions

After examining multiple public SIH26121 repositories:

### Reusable ideas

```text
AHP / multi-criteria ranking
trajectory similarity / DTW
PostGIS spatial filtering
RAG over historical documents
human-in-the-loop review
source-page provenance
hybrid retrieval
3-pane drilling cockpit
physics + ML separation
backtesting
```

### Gaps we should explicitly solve

```text
true MD -> TVDSS transformation
formation-normalized xi correlation
same-stratigraphic-position mapping
uncertainty propagation
geological rather than purely geographic analogue selection
transparent evidence at every correlation step
```

### Critical lesson

A repository can have a sophisticated README without a corresponding domain-real implementation. Always audit:

```text
README
source code
data
outputs
tests
```

before deciding that a public solution has solved a feature.

---

# 78. Final Implementation Checklist

## Geological Core

- [ ] Well model
- [ ] Survey model
- [ ] MD
- [ ] TVD
- [ ] TVDSS
- [ ] Inclination
- [ ] Azimuth
- [ ] Minimum Curvature
- [ ] Survey interpolation
- [ ] Formation tops
- [ ] Formation bases
- [ ] Formation thickness
- [ ] Xi calculation
- [ ] Xi-to-offset-depth mapping

## Historical Intelligence

- [ ] NPT event model
- [ ] Event taxonomy
- [ ] Source document
- [ ] Source page
- [ ] Evidence text
- [ ] Bounding box
- [ ] Confidence

## Offset Intelligence

- [ ] Geospatial radius filter
- [ ] Formation matching
- [ ] Xi matching
- [ ] Distance score
- [ ] Geological score
- [ ] Trajectory score
- [ ] Completion score
- [ ] Omega score
- [ ] Optional AHP
- [ ] Optional DTW
- [ ] Hazard-specific ranking

## Proactive Intelligence

- [ ] +200 m corridor
- [ ] 10 m sampling
- [ ] Future formation
- [ ] Future xi
- [ ] Offset equivalent horizon
- [ ] Historical event aggregation
- [ ] Evidence drill-down

## Engineering Controls

- [ ] Alert severity
- [ ] Acknowledge
- [ ] Override
- [ ] Escalate
- [ ] Audit trail
- [ ] Outcome tracking

## Visualization

- [ ] Map
- [ ] Well markers
- [ ] Active well
- [ ] Offset list
- [ ] Correlation stick plot
- [ ] Formation blocks
- [ ] Xi line
- [ ] Event markers
- [ ] Risk corridor
- [ ] Evidence viewer
- [ ] Live depth

## Data/Model Quality

- [ ] Unit normalization
- [ ] Missing data strategy
- [ ] Confidence tags
- [ ] Observed vs inferred labels
- [ ] Synthetic/demo data disclosure
- [ ] Backtesting
- [ ] Regression tests
- [ ] No fabricated evidence

---

# 79. The One Thing To Remember

If you forget every petroleum term in this document, remember this:

```text
CURRENT DEPTH
     |
     v
WHAT FORMATION AM I IN?
     |
     v
HOW FAR THROUGH THAT FORMATION AM I?
     |
     v
FIND THE SAME POSITION IN OLD WELLS
     |
     v
WHAT HAPPENED THERE?
     |
     v
WHAT IS LIKELY TO MATTER AHEAD?
```

Mathematically:

```text
MD
  -> TVDSS
  -> Formation
  -> xi
  -> Equivalent Offset Depth
  -> Historical Events
  -> Offset Ranking
  -> Ahead-of-Bit Risk
```

That is the Module 4 system.

---

# 80. Sources & Research References

## Primary project specification

- `eRTMAC-NWIS Module 4 — Geological, Drilling and Reservoir Correlation` — internal project master document supplied for this work.

## SIH26121 public problem statement

- [ace-ify/sih-hub — SIH26121](https://github.com/ace-ify/sih-hub/blob/main/ps/SIH26121.md)
- [SIH 26 Copilot — SIH26121](https://sih-26-copilot.vercel.app/problem/sih26-26121)

## Public solution repositories reviewed

- [n3ssdub3y/SIH_2026_PLANNS](https://github.com/n3ssdub3y/SIH_2026_PLANNS)
- [n3ssdub3y/SIH_2026_PLANNS/ARCHITECTURE.md](https://github.com/n3ssdub3y/SIH_2026_PLANNS/blob/main/ARCHITECTURE.md)
- [pallavi-a11y/eRTMAC-NWIS](https://github.com/pallavi-a11y/eRTMAC-NWIS)
- [tarumishra22/eRTMAC-NWIS](https://github.com/tarumishra22/eRTMAC-NWIS)
- [thor11223344/PetrolQ](https://github.com/thor11223344/PetrolQ)
- [xarjunpatil/SIH26121-eRTMAC-NWIS](https://github.com/xarjunpatil/SIH26121-eRTMAC-NWIS-Nearby-Wells-Intelligence-System-An-AI-Powered-Offset-Well)

## Research-use note

Public repositories are useful for architecture comparison and engineering ideas, but they are not evidence that a method is validated on OIL's proprietary data. OIL-private WCR/DDR/trajectory/reservoir data were not available through the public repositories reviewed here.

---

# 81. Core Computational Milestone & Acceptance Test

The core subsurface engine should first validate this exact numerical chain:

```text
ACTIVE WELL (Nahorkatiya-A1 / NHK-412)
   3200 m MD (35° inclination, +85m KB elevation)
      │
      ▼ (Minimum Curvature)
   2986 m TVDSS
      │
      ▼ (Formation Lookup)
   Barail Lower Sand (Top: 2940m TVDSS, Base: 3380m TVDSS, Thickness: 440m)
      │
      ▼ (Stratigraphic Ratio Calculation)
   xi = 0.105 (10.5% into formation)
      │
      ▼ (Offset Horizon Mapping into NHK-089)
   NHK-089 Barail Lower Sand (Top: 3180m TVDSS, Base: 3640m TVDSS, Thickness: 460m)
   Equivalent Depth = 3180 + (0.105 * 460) = 3228 m TVDSS
      │
      ▼ (Historical Event Retrieval within ±50m / ±0.12 xi)
   MATCH FOUND: "Total mud losses at 3228m TVDSS in Barail Lower Sand. Cured with nut plug."
```

Once this computational pipeline passes, the full intelligence system (dynamic ranking, risk corridor, mud margin, knowledge retrieval, and real-time alerts) builds smoothly on top.

---

# 82. Clean Vision & Conceptual Data Processing Blueprint

To transform Module 4 from an abstract mathematical model into a functioning engine, we anchor the implementation directly to the actual dataset in our workspace (`data/raw/`, `data/processed/`, `data/synthetic/`) and the geological realities of Oil India Limited's (OIL) Upper Assam operations.

```text
+---------------------------------------------------------------------------------------------------------+
|                                    MODULE 4 END-TO-END DATA FLOW VISION                                 |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  [ RAW DATA CORPUS IN WORKSPACE ]                                                                       |
|  * 760+ FORGE PDFs (Daily Drilling Reports DDRs + End of Well Reports EOWRs)                            |
|  * Well 1 (78B-32): 35 DDRs + EOWR + Sonic/Temp Logs                                                    |
|  * Well 2 (16A): 50+ DDRs + Drilling Summary Report                                                     |
|  * Well 3 (16B): 60+ DDRs + EOWR (May 2024)                                                             |
|  * Well 4 (56-32): 45+ DDRs + EOWR (68 MB)                                                              |
|  * Well 5 (58-32): 60+ DDRs + EOWR Archive                                                              |
|  * Excel Drilling Operations Logs                                                                       |
|                                                                                                         |
|                                 │                                                                       |
|                                 ▼ (Extraction & Upper Assam Stratigraphic Remapping)                    |
|                                                                                                         |
|  [ STRUCTURED SUBSURFACE REPOSITORY ]                                                                   |
|  * Wells Registry (Wellhead coordinates, elevation MSL, field, fault block)                             |
|  * Directional Surveys (MD, Inclination, Azimuth -> Minimum Curvature TVDSS)                            |
|  * Stratigraphic Tops (Formation names, Top/Base TVDSS, lithology, hazards)                             |
|  * Historical NPT Events (Lost Circulation, Stuck Pipe, Kicks + PDF source citations)                   |
|  * Mud & Pressure Records (Mud weight, viscosity, d-exponent, pore pressure)                           |
|  * Fault Compartments (Spatial boundaries preventing invalid cross-fault correlation)                   |
|                                                                                                         |
|                                 │                                                                       |
|                                 ▼ (Module 4 Engine Core)                                                |
|                                                                                                         |
|  [ SUBSURFACE CORRELATION & RISK PIPELINE ]                                                             |
|  1. Trajectory Normalizer: Active Well MD -> Minimum Curvature -> TVDSS                                 |
|  2. Stratigraphic xi Engine: Active TVDSS -> Formation Boundary Lookup -> xi Ratio (0.0 to 1.0)        |
|  3. Offset Horizon Mapper: xi Ratio -> Offset Formation Top/Base -> Equivalent TVDSS Depth              |
|  4. Proximity & Fault Barrier Filter: Geospatial Distance + Fault Block Consistency Check                |
|  5. Dynamic Ranking Engine: Omega(w, z) = w1*Dist + w2*Geol(xi) + w3*Traj + w4*Comp                    |
|  6. Ahead-of-Bit Projection: Project +50m to +200m TVDSS in 10m increments                              |
|  7. Risk Corridor Aggregator: Query Offset NPTs at Equivalent Horizons -> Hazard Probability            |
|  8. Mud Window / Margin Engine: Offset Mud Weights + Eaton PP / Hubbert-Willis FG vs Live MW            |
|  9. Geological Stick Plot: Multi-well Lithology Columns + Active xi Horizon Line + Incident Markers      |
|                                                                                                         |
|                                 │                                                                       |
|                                 ▼                                                                       |
|                                                                                                         |
|  [ INTERACTIVE DECISION SUPPORT & COCKPIT UI ]                                                          |
|  * Risk Corridor Track: Ahead-of-bit hazards with moving active bit position                             |
|  * Geological Stick Plot: Visual formation alignment across ranked offset wells                          |
|  * Dynamic Offset Leaderboard: Live re-ordering as the bit penetrates new formations                     |
|  * 1-Click Evidence Viewer: Direct bounding-box provenance on original DDR/WCR PDFs                      |
+---------------------------------------------------------------------------------------------------------+
```

---

# 83. Available Data Assets in Workspace

We have 5 core real-world well dossiers from the Utah FORGE Project (760+ PDF documents + spreadsheets) combined with a calibrated synthetic dataset for Upper Assam fields. Drilling mechanics (weight on bit, torque, mud losses, stuck pipe, fractures, rate of penetration) follow identical physical laws in geothermal and oil/gas operations.

### 83.1 Real Well Dossiers (`data/raw/`)

| Local Folder | Original Well Name | Remapped OIL Well Name | Field | Real Assets Available | Key Geological & Drilling Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data/raw/well_1` | FORGE 78B-32 | **Nahorkatiya-A1** *(Active Well)* | Nahorkatiya | 35 Daily Drilling Reports (PDFs), End of Well Report (EOWR), Sonic Log PDF, Temperature Log PDF | Highly deviated well (~35° inclination), extensive DDR mud property records, mud losses recorded at multiple intervals. |
| `data/raw/well_2` | FORGE 16A(78)-32 | **Nahorkatiya-A3** *(Offset 1)* | Nahorkatiya | 50+ Daily Drilling Reports (PDFs), Drilling Summary Report (11 MB PDF), EOWR with appendices | Deep offset well (~2,414 m TD), fractured basement, lost circulation and tight hole events. |
| `data/raw/well_3` | FORGE 16B(78)-32 | **Nahorkatiya-A5** *(Offset 2)* | Nahorkatiya | 60+ Daily Drilling Reports (PDFs), End of Well Report (68 MB PDF, May 2024), Excel operations logs | Modern production well, complete survey stations, high-resolution ROP and torque logs. |
| `data/raw/well_4` | FORGE 56-32 | **Moran-B2** *(Offset 3)* | Moran | 45+ Daily Drilling Reports (PDFs), EOWR (Final 22 July 2021 PDF), Daily morning Excel reports | Deep injection well, structural flank position, higher formation top depths due to regional dip. |
| `data/raw/well_5` | FORGE 58-32 | **Digboi-C1** *(Offset 4)* | Digboi | 60+ Daily Drilling Reports (PDFs), 58-32 EOWR archive | Deep exploration/monitoring well, historical overpull and tight hole incidents. |

### 83.2 Calibrated Offset Wells (`data/synthetic/oil_india_mock/`)

To support full 50 km field analysis and fault-block gating demonstrations:
- **15 Calibrated Offset Wells** (e.g., `NHK-089`, `NHK-145`, `NHK-201`, `MOR-034`, `MOR-099`, `DIG-012`, `BAG-005`):
  - Calibrated against USGS Bulletin 2208-D formation depths, thicknesses, porosities, and regional structural dip ($3^\circ - 15^\circ$ SE).
  - Contain realistic NPT histories: Tipam Sandstone (Lost Circulation), Barail Coal-Shale (Differential Sticking, Coalbed Gas Influx), Kopili Shale (Overpressure, Wellbore Washout/Keyseating).

---

### 83.3 Deep Multi-Modal Data Asset Audit Across Subfolders

Direct file inspection across subfolders reveals several distinct document archetypes and data streams that feed Module 4:

#### 1. 566-Page Modern Directional Well Dossier (`data/raw/well_4/End of Well Report-16B78-32-May_2024 (1).pdf`)
- **Spatial Coordinates:** Exact UTM Coordinates (Northing 13,987,765.96 ft / UTM 4,263,471, Easting 1,097,907.09 ft / UTM 334,642, Lat 38.501242, Long -112.882661), KB Elevation 5,447.65 ft, Ground Level 5,415.65 ft.
- **Complex Trajectory:** Kick-off depth 5,600 ft KB, Azimuth 105°, Build Rate 5.5°/100 ft, Inclination 65°, Total Measured Depth 10,700.97 ft (3,261 m), True Vertical Depth 8,262.48 ft (2,518 m), Horizontal step-out 4,079.22 ft (1,243 m).
- **Physical Offset Doublet Pair:** Explicitly engineered as an offset pair to Well 16A(78)-32 offset vertically by 300 ft TVD — the exact real-world analog for Module 4's offset well correlation.
- **Detailed BHA & RSS Records:** 31 distinct BHA runs documenting Rotary Steerable Systems (RSS), PDC bits, core stubs, bit dull gradings, and reaming operations.
- **Casing & Circulation Programs:** 22" hole to 1,036 ft & 16" casing, 14-3/4" hole to 9,800 ft, 7" production casing to TD, and high-rate circulation cooling tests.

#### 2. Multi-Sheet Operations & Completion Spreadsheets (`data/raw/well_3/.../completion/*.xlsx`)
- **Structured Tabs:** `['Daily Report', 'Data', 'WellEz Log']`.
- **Granular Fields:** 24-hour operations broken down into operational phases, rig phone numbers, safety meeting topics, accidents/incidents logs, consumables usage (barite, gels, polymers), and standardized NPT time-tracking codes.
- **Frac & Casing Stages:** Tracks perforated intervals, treating pressures, slurry volumes, and post-frac flowback rates.

#### 3. Specialized Subsurface EOWR Appendices (`data/raw/well_5/58-32_EOWR/`)
- **`BitSummary.pdf` (4 pages):** Full bit performance history detailing bit serial numbers, make, diameter (17.5", 12.25", 8.75"), jets, footage, hours, average ROP, WOB, RPM, jet velocity, pressure drops, hydraulic horsepower (HHP), and IADC dull wear gradings.
- **`CasingReports_All.pdf` (4 pages):** Casing shoe setting depths, nominal OD/ID, joint weights, casing grades (L-80, P-110, S-135), centralizer spacing, and Leak-Off Test (LOT / FIT) equivalent mud weights.
- **`CementJobReports_All.pdf` (4 pages):** Slurry volumes, pumping pressures, slurry densities, displacement rates, top of cement (TOC), and Cement Bond Log (CBL) quality evaluation.
- **`Coring Report.pdf` (14 pages):** Core intervals, recovered footage, core barrel jam incidents, fracture orientation, and rock quality designation (RQD).

#### 4. Individual Daily Drilling Detail & Graphical Reports (`data/raw/well_5/DailyDrillingReports_Well58-32/` & `data/raw/well_1/56-32 Daily Drilling Reports/`)
- **63+ Sequential Daily PDFs:** Daily graphical tracks and summary reports capturing the day-by-day drilling timeline, hookload variations, mud density increments, and real-time operational delays.

---

# 84. Conceptual Data Models for Subsurface Intelligence

Rather than rigid database constraints, Module 4 relies on clean conceptual entities:

### 84.1 Wells Entity
- **Identifiers:** `well_id`, `well_name`, `field_name` (Nahorkatiya, Moran, Digboi).
- **Spatial / Structural:** Wellhead Latitude/Longitude, KB Elevation (meters above MSL), Fault Block ID.
- **Drilling Context:** Total Depth (MD), Well Type (Vertical, Deviated, Horizontal), Status (Active/Drilling, Completed).

### 84.2 Directional Surveys Entity
- **Station Readings:** `well_id`, `md` (Measured Depth), `inclination` (degrees), `azimuth` (degrees).
- **Computed Trajectory:** `tvd` (True Vertical Depth), `tvdss` (TVD Subsea = TVD - Elevation), `northing`, `easting`, `dogleg_severity`.
- **Calculation Mode:** `MINIMUM_CURVATURE` (primary) or `VERTICAL_ASSUMPTION` (fallback).

### 84.3 Stratigraphic Formation Tops Entity
- **Interval Bounds:** `well_id`, `formation_name`, `top_md`, `top_tvdss`, `base_md`, `base_tvdss`, `thickness_tvdss`.
- **Geological Properties:** Stratigraphic order (1 = surface to n = basement), lithology classification (Sandstone, Shale, Coal, Carbonate).
- **Hazard Profile:** Dominant formation hazard (Lost Circulation, Stuck Pipe, Overpressure), Data confidence (Verified WCR, Inferred, Imputed).

### 84.4 Historical NPT Incidents Entity
- **Incident Details:** `event_id`, `well_id`, `formation_name`, `depth_md`, `depth_tvdss`, `xi_position` (0.0 to 1.0 within formation).
- **Classification & Severity:** Event type (`LOST_CIRCULATION`, `STUCK_PIPE`, `GAS_KICK`, `TIGHT_HOLE`), Severity rating (1 to 5), Duration (hours), Financial NPT cost estimate.
- **Narrative & Mitigation:** Operational narrative, remedial action taken, mitigation effectiveness (Effective, Partial, Failed).
- **Provenance Proof:** Source PDF document ID, page number, bounding-box coordinates `[x0, y0, x1, y1]`.

### 84.5 Mud & Pressure Logs Entity
- **Drilling Fluid Properties:** `well_id`, `depth_tvdss`, `xi_position`, `formation_name`, mud density (g/cc / SG), viscosity, plastic viscosity, yield point.
- **Pore Pressure & Fracture Margin:** d-exponent, calculated pore pressure gradient (Eaton method), estimated fracture gradient (Hubbert-Willis / Eaton).

### 84.6 Fault Compartments Entity
- **Structural Boundaries:** `block_id`, `block_name`, `field_name`, polygon boundary coordinates.
- **Barrier Logic:** Used to detect cross-fault offset wells and penalize or flag geological uncertainty.

---

# 85. Subsurface Correlation Engine Capabilities

Module 4 executes five core computational capabilities:

```text
                               +-----------------------------+
                               |     ACTIVE WELL TELEMETRY   |
                               |    Bit Depth (MD) = 3200m   |
                               +--------------┬--------------+
                                              │
                                              ▼
                               +-----------------------------+
                               | 1. Minimum Curvature Engine |
                               |   Calculates: TVDSS = 2986m |
                               +--------------┬--------------+
                                              │
                                              ▼
                               +-----------------------------+
                               | 2. Stratigraphic xi Engine  |
                               |  Barail Lower Sand [2940m]  |
                               |     xi = 0.105 (10.5% in)   |
                               +--------------┬--------------+
                                              │
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
        +-----------------------------+               +-----------------------------+
        |  3. Offset Horizon Mapping  |               | 4. Dynamic Offset Ranking   |
        |   For each offset well w:   |               |     Omega(w, z) Engine      |
        |  z_equiv = Top_w + xi*Thick |               |  Geol + Dist + Traj + Comp  |
        |  (e.g., NHK-089 -> 3228m)   |               |  (Re-ranks live with depth) |
        +--------------┬--------------+               +--------------┬--------------+
                       │                                             │
                       └──────────────────────┬──────────────────────┘
                                              ▼
                               +-----------------------------+
                               | 5. Ahead-of-Bit Risk Engine |
                               |  Projects [0m to +200m] TVD |
                               |  Aggregates Offset NPT Logs |
                               |  Outputs Risk Corridor JSON |
                               +--------------┬--------------+
                                              │
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
        +-----------------------------+               +-----------------------------+
        |  6. Mud Window / Margin     |               | 7. Correlation Stick Plot   |
        |  PPG (Eaton) vs FG vs MW    |               | Multi-Well Lithology Align  |
        |  Offset historical points   |               | Active Horizon Line + NPTs  |
        +-----------------------------+               +-----------------------------+
```

### 85.1 1. Trajectory & Minimum Curvature Normalization
- Converts discrete survey stations `(MD, Inc, Az)` into a continuous 3D wellbore trajectory.
- Calculates True Vertical Depth Subsea ($TVDSS = TVD - Elevation_{MSL}$), local northing/easting, and dogleg severity.
- Provides high-speed interpolation mapping any real-time Measured Depth ($MD$) to $TVDSS$.

### 85.2 2. Stratigraphic Ratio ($\xi$) Normalization
- Identifies which formation the active bit currently occupies.
- Normalizes position within the formation:
  $$\xi(d, well) = \frac{d_{tvdss} - Top_{tvdss}(well)}{Base_{tvdss}(well) - Top_{tvdss}(well)}$$
- Accounts for formation thickness variations and structural dip across the field.

### 85.3 3. Offset Horizon Mapping
- Translates the active $\xi$ position into the equivalent $TVDSS$ horizon inside each candidate offset well:
  $$z_{offset}^{equiv} = Top_{tvdss}(offset) + \xi \times Thickness_{tvdss}(offset)$$
- Queries historical operational and NPT events within an equivalent window ($\pm 50\text{m}$ or $\pm 0.12\xi$).

### 85.4 4. Dynamic Multi-Criteria Offset Ranking ($\Omega$)
$$\Omega(w, z) = w_1 S_{distance}(w) + w_2 S_{geological}(w, z) + w_3 S_{trajectory}(w) + w_4 S_{completion}(w)$$
- **Geological Relevance:** Prioritizes wells that penetrated the active formation and encountered events at similar stratigraphic positions.
- **Fault-Block Gating:** Applies cross-fault penalty flags if an offset well sits in a separated tectonic block.
- **Live Re-ranking:** As the drill bit penetrates from Tipam Sandstone into Barail Coal-Shale, the offset leaderboard dynamically re-ranks to highlight wells with relevant coalbed incident history.

### 85.5 5. Ahead-of-the-Bit Predictive Risk Corridor
- Projects $+50\text{m}$ to $+200\text{m}$ $TVDSS$ ahead of the current bit in $10\text{m}$ steps.
- Evaluates future formations and equivalent offset horizons.
- Aggregates historical incident frequencies (Lost Circulation, Stuck Pipe, Gas Kicks) weighted by offset $\Omega$ scores.
- Generates proactive alerts before the bit enters hazardous intervals.

### 85.6 6. Mud Window & Drilling Margin Correlation
- Computes Pore Pressure Gradient ($PPG$) from offset d-exponent trends (Eaton method) and recorded kicks.
- Computes Fracture Gradient ($FG$) bounds (Hubbert-Willis / Eaton).
- Overlays live mud weight against historical offset mud weights at equivalent $\xi$, giving clear warning when approaching fracture or influx margins.

---

# 86. Core API Capabilities & Conceptual Payloads

### 86.1 Stratigraphic Correlation Lookup (`/api/v1/correlation/xi`)
Returns current formation identity, normalized $\xi$ position, and mapped equivalent depths across offset wells.

```json
{
  "active_well_id": "NHK-412",
  "active_well_name": "Nahorkatiya-A1",
  "depth_md": 3200.0,
  "depth_tvdss": 2986.4,
  "current_formation": {
    "name": "Barail Lower Sand",
    "top_tvdss": 2940.0,
    "base_tvdss": 3380.0,
    "thickness_tvdss": 440.0,
    "lithology": "SANDSTONE",
    "primary_hazard": "LOST_CIRCULATION"
  },
  "xi_value": 0.1055,
  "offset_equivalents": [
    {
      "well_id": "NHK-089",
      "well_name": "Nahorkatiya-A3",
      "equivalent_depth_tvdss": 3228.5,
      "formation_top_tvdss": 3180.0,
      "formation_thickness": 460.0,
      "matching_npt_count": 3
    }
  ]
}
```

### 86.2 Ahead-of-the-Bit Risk Corridor (`/api/v1/correlation/risk_corridor`)
Provides a continuous depth track showing projected hazard probabilities and attached evidence.

```json
{
  "active_well_id": "NHK-412",
  "current_depth_md": 3200.0,
  "current_depth_tvdss": 2986.4,
  "corridor_points": [
    {
      "depth_ahead_m": 0.0,
      "depth_tvdss": 2986.4,
      "formation": "Barail Lower Sand",
      "xi": 0.1055,
      "lost_circulation_risk": 0.85,
      "stuck_pipe_risk": 0.12,
      "gas_kick_risk": 0.05,
      "composite_severity": "AMBER",
      "evidence_events": [
        {
          "event_id": "NPT-NHK089-04",
          "well_name": "NHK-089",
          "event_type": "LOST_CIRCULATION",
          "depth_tvdss": 3228.0,
          "severity": 4,
          "narrative": "Total mud losses at 3228m TVDSS while drilling Barail Lower Sand. Lost 35 bbl/hr.",
          "mitigation": "Pumped 30 bbl medium nut plug LCM pill + reduced pump rate to 1200 lpm.",
          "document_id": "DDR_NHK089_2015_03_14",
          "page_number": 2,
          "bbox": [120, 340, 510, 380]
        }
      ]
    }
  ]
}
```

### 86.3 Geological Stick Plot Visualization (`/api/v1/correlation/stick_plot`)
Delivers columnar lithology blocks, active $\xi$ horizon lines, and historical event glyphs for multi-well correlation display.

---

# 87. Functional Architecture & Responsibilities

Module 4 is organized into seven functional domains:

1. **Trajectory & Survey Domain:** Minimum curvature computation, survey interpolation, dogleg checks, and MD-to-TVDSS mapping.
2. **Stratigraphy & Geology Domain:** Formation top/base resolution, $\xi$ ratio calculation, uncertainty propagation, and regional dip extrapolation.
3. **Horizon Correlation Domain:** Forward/inverse $\xi$-to-TVDSS mapping, equivalent interval search, and continuous log profile alignment.
4. **Offset Ranking & Spatial Domain:** Multi-criteria $\Omega$ scoring, PostGIS distance queries, fault-block barrier gating, and real-time reranking.
5. **Ahead-of-Bit Risk Domain:** 200m depth projection, hazard aggregation, and continuous risk curve computation.
6. **Mud Margin & Geomechanics Domain:** Eaton d-exponent pore pressure trends, Hubbert-Willis fracture gradient bounds, and mud weight margin tracking.
7. **Document Provenance Domain:** Mapping incident records to source PDF pages, bounding-box coordinate retrieval, and 1-click citation display.

---

# 88. Phased Implementation Roadmap

### Phase 1: Subsurface Core Mathematics & Unit Tests
- Build Minimum Curvature trajectory conversion and TVDSS interpolator.
- Build Stratigraphic $\xi$ calculator and equivalent depth mapper.
- Validate with the primary numerical test case ($3200\text{m MD} \to 2986\text{m TVDSS} \to \text{Barail Lower Sand} \to \xi = 0.105 \to \text{NHK-089 at } 3228\text{m TVDSS}$).

### Phase 2: Repository Population & Data Mapping
- Ingest extracted records from the 5 FORGE real-world well dossiers remapped to Upper Assam OIL field names.
- Populate 15 calibrated offset wells reflecting USGS Bulletin 2208-D stratigraphy and regional dip ($3^\circ - 15^\circ$ SE).
- Define spatial fault block boundaries for Nahorkatiya and Moran.

### Phase 3: Dynamic Offset Ranking ($\Omega$) & Fault Gating
- Build multi-criteria scoring ($S_{dist}, S_{geol}, S_{traj}, S_{comp}$).
- Enforce fault-block barrier logic to flag cross-fault offsets.
- Connect live depth triggers to re-rank offset candidates dynamically as formation boundaries are crossed.

### Phase 4: Ahead-of-Bit Risk Corridor & Mud Margin
- Build $200\text{m}$ forward projection engine with historical event severity aggregation.
- Implement Eaton pore pressure and fracture margin calculations.
- Connect 1-click PDF bounding-box citation retrieval.

### Phase 5: REST Endpoints & WebSocket Integration
- Expose correlation, risk corridor, stick plot, and offset ranking endpoints.
- Connect real-time telemetry stream to trigger subsurface calculations on bit advance.
- Provide CSV/JSON export options for audit reporting.

### Phase 6: Cockpit UI Integration & Evaluation
- Connect the center track Risk Corridor chart and Geological Stick Plot.
- Connect the dynamic offset ranking panel and PDF evidence viewer.
- Validate end-to-end against the OIL drilling superintendent persona test cases.

---

# 89. Rigorous Verification & Ground Truth Validation Matrix

| Verification Test | Test Methodology | Expected Result / Acceptance Criterion | Pass/Fail Condition |
| :--- | :--- | :--- | :--- |
| **Test 1: Directional Survey Sanity** | Run Minimum Curvature on 35° deviated well (`Nahorkatiya-A1`) from MD 0 to 3,500m. | TVD at 3,200m MD is approximately 2,986m (accounting for KB elevation +85m). | Error $< 0.5\%$ vs commercial directional software benchmark. |
| **Test 2: Regional Dip Consistency** | Extract TVDSS formation tops across 10 wells ordered West to East across Nahorkatiya/Moran. | Tipam and Barail tops show systematic deepening to the SE at 50-100m TVDSS per km ($3^\circ - 8^\circ$ dip). | PASS if dip trend is monotonic; FAIL if random depth anomalies appear without faulting. |
| **Test 3: Stratigraphic Event Clustering** | Calculate $\xi$ for all historical Lost Circulation and Stuck Pipe incidents across all wells. | $> 85\%$ of Lost Circulation events cluster in Tipam ($\xi \in [0, 1]$); $> 80\%$ of Stuck Pipe events cluster in Barail Coal-Shale ($\xi \in [0, 1]$). | PASS if geological clustering confirmed; FAIL if events randomly scatter across unrelated formations. |
| **Test 4: Blind Hazard Prediction** | Hold out 1 historical well with known NPTs. Run Module 4 correlation using remaining wells to generate risk corridor. | $> 70\%$ of actual historical NPT events in the hold-out well predicted within $\pm 50\text{m}$ TVDSS equivalent horizon. | PASS if Recall $\ge 70\%$ at AMBER threshold. |
| **Test 5: Live Reranking Demonstration** | Simulate bit depth advancing from 1,800m TVDSS (Tipam) to 3,200m TVDSS (Barail Coal-Shale). | Offset well ranked #1 changes in real-time from a Tipam LC offset (`NHK-089`) to a Barail Stuck Pipe offset (`MOR-034`). | Leaderboard re-orders smoothly in Cockpit UI without UI freeze or delay $> 100\text{ms}$. |
| **Test 6: 1-Click PDF Provenance** | Click on any risk corridor event in the Cockpit UI. | System retrieves the exact DDR PDF, renders the page, and draws a yellow bounding-box highlight over the matching operational narrative. | Highlighting matches exact source sentence with 100% provenance accuracy. |

---

# 90. Summary: The Module 4 Production Guarantee

Module 4 is the intellectual brain of eRTMAC-NWIS. By anchoring directly to real data, adhering strictly to minimum curvature 3D trigonometry, normalizing for structural dip via the stratigraphic ratio $\xi$, enforcing fault-block boundaries, projecting proactive 200m risk corridors, and providing 1-click bounding-box proof back to original DDR/WCR documents, Module 4 delivers a sovereign, air-gapped, physics-grounded decision support platform tailored specifically for Oil India Limited.
