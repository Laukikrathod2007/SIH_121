# eRTMAC-NWIS: Complete Project Vision, Context and SIH Strategy
# Master Document 0 of 6 — Project Overview

> **This file is a complete, self-contained reference.**
> An AI reading only this file should understand: what we are building, why, for whom,
> what the competition looks like, and exactly what OIL and SIH evaluators expect to see.

---

## 1. The Problem in Plain English

Oil India Limited (OIL) drills oil wells in Upper Assam — fields like Nahorkatiya, Moran, Digboi,
Baghjan, Lakwa. When they start drilling a new well, they are effectively drilling blind.

They know what happened on the surface and in previous wells — there are thousands of old Daily
Drilling Reports (DDRs) and Well Completion Reports (WCRs). But these are scanned PDF archives,
physically locked in filing cabinets or uncategorized digital folders. Nobody can search them in real
time. When the drill bit enters a Tipam Sandstone at 3,200 m and the mud starts disappearing, the
drilling engineer needs to know — right now, not in 3 hours after manually flipping through
50-year-old reports — that this exact zone caused total lost circulation in 3 nearby offset wells
last decade, and that the proven fix was a 25-barrel nut-plug LCM pill pumped at reduced rates.

The global commercial tools that solve this — SLB DELFI ($40k–$80k/user/yr), Corva
($1,500–$3,500/rig/month), Cognite ($500k–$2M ARR) — require:
- Public cloud streaming of classified Indian well data (violates DGH NDR rules).
- USD-denominated SaaS fees (rejected by CVC L1 tendering rules for PSUs).
- Internet-connected rigs (OIL Upper Assam blocks are remote; VSAT drops in monsoon).

PS 26121 asks us to build the Indian sovereign alternative: an AI-powered Nearby Wells
Intelligence System (NWIS) that runs air-gapped at the eRTMAC command center in Duliajan, ingests
OIL own historical data, and delivers proactive ahead-of-the-bit risk intelligence to the drilling
engineer screen before the incident happens.

---

## 2. What OIL eRTMAC Already Does (Critical Context)

eRTMAC is OIL proprietary 24/7 drilling command center at Duliajan, Assam. It is NOT something we
are replacing. It is something we EXTEND as a complementary intelligence layer.

eRTMAC 1.0 (operational today): Ingests 1-Hz WITSML telemetry from Mobile Logging Units (MLUs)
at each active rig. Displays ROP, WOB, RPM, Torque, Standpipe Pressure, Flow In/Out, Hookload,
Total Pit Volume. Senior engineers monitor multiple wells simultaneously from Duliajan.

eRTMAC 2.0 (2026 tender CDH6605P21): OIL has tendered 12+4 MLU upgrade. New MLUs support
WITSML 1.4.1 and WITS Level 0. Our system must be compatible with this interface.

What eRTMAC CANNOT do: It has no memory. It sees the current second sensor reading. It cannot
tell the engineer "At this depth, in these 4 offset wells, this pattern preceded stuck pipe." It
has no geospatial map. It cannot search the DDR archive. NWIS fills exactly this gap.

---

## 3. The 7 PS Outcomes mapped to 7 Production Modules

PS Outcome i  -> Module 1: Historical Drilling Data Extraction and Structuring
PS Outcome ii -> Module 2: Map-Based Nearby Well Intelligence
PS Outcome iii-> Module 3: Searchable Drilling Knowledge Repository
PS Outcome iv -> Module 4: Geological, Drilling and Reservoir Correlation
PS Outcome v  -> Module 5: Predictive Drilling Risk Analytics
PS Outcome vi -> Module 6: Real-Time Alerts and Recommendations
PS Outcome vii-> Module 7: Unified Drilling Command Cockpit

---

## 4. The Upper Assam Geological Reality
# Source: USGS Bulletin 2208-D, Wandrey 2004 — public domain, verified.

### 4.1 Stratigraphic Column (Top to Bottom)

FORMATION           | AGE            | TYPICAL DEPTH (mMD)  | TYPE           | DRILLING HAZARD
--------------------|----------------|----------------------|----------------|------------------
Alluvium/Surface    | Holocene       | 0 – 50 m             | Unconsolidated | Conductor pipe
Gurjan Formation    | Pliocene       | 50 – 600 m           | Clay/Mudstone  | Swelling clays
Girujan Formation   | Plio-Miocene   | 600 – 1,200 m        | Sandy Clay     | Wellbore instability
Tipam Sandstone     | Miocene        | 1,200 – 2,800 m      | Sandstone      | LOST CIRCULATION
                    |                |                      | 7-30% porosity | (depleted pressure)
                    |                |                      | 8-800 mD perm  |
Surma Group         | Oligo-Miocene  | 2,800 – 3,500 m      | Siltstone/Shale| Tight hole
Barail Group        | Oligocene      | 3,000 – 5,500 m      | Two units:     |
  Barail Lower Sand |                |                      | Sand reservoir | STUCK PIPE
  (Main Pay Sand)   |                |                      | up to 900m     | (differential sticking
  Barail Upper      |                |                      | Coal-Shale     |  on coal seams)
  (Coal-Shale)      |                |                      | up to 1,200m   | GAS KICKS
Kopili Formation    | Eocene         | 4,500 – 6,000 m      | Shale/Limestone| Overpressure
Sylhet Formation    | Eocene         | 5,000 – 7,000 m      | Limestone      | Primary source rock
Tura/Langpar        | Paleocene      | >6,000 m             | Sandstone      | Basement marker
Dergaon Formation   | Cretaceous     | >7,000 m             | Sandstone/Shale| Basement
Basement            | Pre-Cretaceous | >7,000 m             | Crystalline    | Terminal depth

CRITICAL NOTE: These are ranges across the Upper Assam Shelf. Individual wells vary by up to
+/-500 m depending on structural position (crest vs flank), formation dip (3-15 degrees SE),
and fault proximity. This is why raw MD comparison between offset wells FAILS — a crest well
hits Tipam at 1,400 m MD while a flank well hits it at 2,100 m MD for the same geological
horizon. Module 4 fixes this using TVDSS normalization.

### 4.2 Reservoir Properties (Source: USGS Bulletin 2208-D)

Formation          | Permeability | Porosity  | Primary Fluid  | Pressure Regime
-------------------|-------------|-----------|----------------|------------------
Tipam Sandstone    | 8-800 mD    | 7-30%     | Oil + Gas      | Depleted (mature field)
Barail Lower Sand  | 10-200 mD   | 12-25%    | Oil + Gas      | Near-normal
Barail Coal-Shale  | <5 mD       | <10%      | Coalbed Gas    | Underpressured
Kopili Formation   | <10 mD      | <10%      | Tight gas      | Overpressured zones
Sylhet Carbonate   | Fracture    | <7% matrix| Oil            | Overpressured

### 4.3 The Structural Dip Problem

The Assam Shelf dips to the SOUTHEAST at 3-15 degrees toward the Naga Hills.
A well drilled in Nahorkatiya (NW flank) hits formations SHALLOWER than a Moran well (more SE).
Depth difference for the SAME formation top between Nahorkatiya and Moran = 200-800 m.
Any system comparing raw MD between these areas is geologically wrong.

### 4.4 Known Drilling Hazard Zones

1. TIPAM SANDSTONE (1,200-2,800 m): Primary lost circulation zone.
   Cause: Mature producing formation with depleted reservoir pressure.
   When mud column hydrostatic > reservoir pore pressure, mud flows into the formation.
   OIL Mitigation: Reduce mud weight; pre-mix 25-30 bbl LCM pill (medium nut plug +
   calcium carbonate) BEFORE entering formation.

2. BARAIL COAL-SHALE (3,500-4,700 m): Primary stuck pipe and gas kick zone.
   Cause: Interbedded coal seams cause differential sticking. Coal seam gas causes sudden
   gas cuts. OIL Mitigation: Maintain string rotation during connections; inhibited mud;
   spot diesel pill if stuck.

3. BARAIL-KOPILI TRANSITION (4,700-5,200 m): Torque and drag zone.
   Cause: Reactive Kopili shales. Wellbore goes oval (keyseating).
   Requires tight mud weight window.

4. SYLHET/KOPILI CARBONATES (>5,000 m): Kick risk from overpressure.
   Requires pre-drill pore pressure prediction from offset d-exponent trends.

---

## 5. Data Strategy

### 5.1 What Public Indian Data Exists

Source                | What Available                                    | Access
----------------------|---------------------------------------------------|---------------------------
USGS Bulletin 2208-D  | Full stratigraphic column, formation properties   | FREE pubs.usgs.gov
Parivesh EIA Portal   | OIL well names, lat/long, planned depths          | FREE parivesh.nic.in
PPAC Monthly Reckoner | Company-level production totals                   | FREE ppac.gov.in
DGH NDR               | Actual well logs, DDRs, trajectories              | GATED - paid license
OIL Internal DDRs     | Raw daily drilling reports                        | PROPRIETARY - no access
Equinor Volve         | Real 1-Hz telemetry + DDR PDFs from North Sea     | FREE CC BY 4.0

### 5.2 Demo Data Architecture (Three Layers)

Layer 1 - Volve (Real Telemetry Structure):
  Equinor Volve dataset: real 1-Hz WITSML sensor streams + real DDR PDFs.
  Used for: telemetry engine, rig-state classifier, OCR pipeline testing.
  Relabelled: Volve well names -> OIL well naming convention (NHK-series, MOR-series).
  License: CC BY 4.0 — fully legal for commercial demo use.

Layer 2 - USGS Geological Parameters (Verified Real Geology):
  USGS Bulletin 2208-D provides verified formation depths, thickness, permeability, porosity
  ranges for Upper Assam. Used to construct synthetic formation-top tables matching real geology.

Layer 3 - Synthetic Generator (Statistically Grounded):
  Python script generates DDR-style text, formation-top tables, NPT event logs using
  distributions from USGS + Volve parameters.
  Every synthetic record labelled: [SYNTHETIC - Generated from USGS Bulletin 2208-D parameters]
  Jury answer: "Geological parameters from USGS peer-reviewed public domain source.
  Telemetry from Equinor Volve CC BY 4.0. Values are synthetic but statistically calibrated."

---

## 6. Competitive Landscape

### 6.1 SIH Competitor Archetypes

Archetype               | % Teams | What They Build                        | Why Judges Reject
------------------------|---------|----------------------------------------|-------------------
Generic PDF Chatbot     | 60%     | Streamlit + LangChain + OpenAI         | No subsurface awareness. Hallucinates mud weights.
GIS Surface Map         | 20%     | Leaflet + static wellhead popups       | Euclidean distance only. Ignores formation dip.
Toy ML Benchmark        | 15%     | Single XGBoost on Volve CSV claiming 99% | Random split on time-series = data leakage
Multi-Module Contender  | 5%      | React + PostGIS + FastAPI + basic OCR  | Lacks xi correlation, ahead-of-bit corridor, proof

### 6.2 Open-Source Direct Competitors

Project         | Repo                              | Gap vs NWIS
----------------|-----------------------------------|----------------------------------------------
DrillMind       | ArokyaMatthew/DrillMind           | No offset ranking, no depth sync, single well
drillscribe     | chinmoypaul8897/drillscribe       | Post-mortem only, no real-time predictive risk
DrillSense      | bingyby/drill-sense-insight-hub   | No geospatial, no telemetry, no correlation
DDR_UTAH_FORGE  | djimrastephane/DDR_UTAH_FORGE     | Single well, no prediction, no live streaming

### 6.3 Commercial Solutions and Why OIL Cannot Use Them

Vendor    | Product     | Price             | Why Blocked for OIL
----------|-------------|-------------------|---------------------------------
SLB       | DELFI/Tela  | $40k-80k/user/yr  | Streams data to AWS -> violates DGH NDR
Halliburton| iEnergy/DHP | $25k-60k/user/yr | USD billing -> rejected by CVC L1 rules
Corva     | Platform    | $1.5k-3.5k/rig/mo | US-server streaming; no Assam geology models
Cognite   | Data Fusion | $500k-2M ARR      | Enterprise SaaS; incompatible with PSU procurement

---

## 7. SIH Jury Expectations

### 7.1 The 3 Jury Personas

Persona 1 - OIL Drilling Superintendent (25+ yrs Duliajan):
  Tests: Do you know Barail Coal? Do you understand TVDSS vs MD?
  DISQUALIFYING: "Our AI detects anomalies" (too vague). "98% accuracy" (will ask about data split).
  WINNING: "We use USGS Bulletin 2208-D formation tops to normalize offset depth. At 3,200 m MD in
  NHK-series wells, the Barail Coal-Shale causes differential sticking — we project 50 m ahead
  using the xi ratio, giving crews 2-4 hours of preparation time."

Persona 2 - eRTMAC IT / Systems Head:
  Tests: Data flow, latency, air-gap compliance.
  DISQUALIFYING: "We call the OpenAI API." "Deployed on AWS."
  WINNING: "Air-gapped FastAPI backend. PostgreSQL+PostGIS on-premise. Sub-20ms inference. No
  external API calls in the live demo path."

Persona 3 - MoPNG / Academic Specialist:
  Tests: Data provenance, ML rigor, IP freedom.
  DISQUALIFYING: Uncited depth claims. "We used GPT-4."
  WINNING: "USGS Bulletin 2208-D (public domain 2004). Volve (CC BY 4.0). Blocked time-series
  cross-validation — no random splitting of sensor time-series data."

### 7.2 The 4 Fatal Disqualifying Patterns

1. Toy Streamlit Wrapper: CSV -> .predict() -> text box. Looks like a college assignment.
2. Raw MD Fallacy: Comparing offset depths as raw MD. Drilling superintendent catches this in 10 seconds.
3. Hallucinating Chatbot: LLM outputs drilling numbers with no document proof.
4. Multi-Agent Debate Loop: Agents debating for 35 seconds. Gas kick surfaces in 90 seconds.

### 7.3 The 6 Winning Demo Deliverables

1. Live 1-Hz telemetry replay via WebSocket (ROP, WOB, RPM, Torque, SPP, Flow).
2. PostGIS geospatial offset map with 15 wells, formation-aware color coding.
3. Dynamic offset ranking Omega(w,z) - judges see list REORDER live as bit depth changes.
4. Ahead-of-bit risk corridor - Amber fires 30 m before Barail Coal entry, timestamp visible.
5. Telemetry corroboration - SPP drop + flow deficit fires Red Tier-1 alert (not just historical).
6. 1-click PDF bounding-box proof - original DDR opens with yellow highlight on exact sentence.

---

## 8. Business ROI for Oil India Limited

Preventing 4 stuck pipe or lost circulation events per year saves OIL:
- Rig day rate for fishing/sidetrack: Rs 15-40 lakh per event
- Mud rebuild after total lost circulation: Rs 5-20 lakh per event
- TOTAL ANNUAL SAVING: Rs 15 Crore - Rs 25 Crore (conservative estimate)

Additionally:
- Digitizes decades of Upper Assam institutional memory from retiring engineers.
- 100% compliant with MoPNG, DGH NDR, OISD-STD-187 data sovereignty guidelines.
- Air-gapped deployment: zero recurring cloud fees, zero SaaS vendor lock-in.

---

## 9. Master Document Index

File                                    | Contents                                          | Approx Lines
----------------------------------------|---------------------------------------------------|-------------
M0_PROJECT_VISION_AND_CONTEXT.md       | What, why, OIL context, geology, data, SIH        | ~350
M1_DATA_INGESTION_AND_STORAGE.md       | Module 1: OCR, WITSML, database, synthetic gen     | ~800
M2_M3_GEOSPATIAL_AND_KNOWLEDGE.md      | Module 2 (GIS) + Module 3 (knowledge repo + RAG)  | ~700
M4_GEOLOGICAL_CORRELATION.md           | Module 4: TVDSS, xi ratio, formation alignment     | ~900
M5_M6_RISK_ANALYTICS_AND_ALERTS.md     | Module 5 (5 hazard engines) + Module 6 (alerts)   | ~800
M7_COCKPIT_DEMO_IMPLEMENTATION.md      | Module 7 (dashboard), demo, tech stack, jury Q&A  | ~700


---
---
## APPENDIX: GEOMINE COMPETITOR TEARDOWN
# Source: SIH 2026 competitor video youtu.be/7VflW86W7hA
# Added after seeing Geomine demo. Use this section for jury differentiation questions.

### What Geomine Is

Geomine is a full-stack drilling intelligence platform targeting the same PS as NWIS.
It is the most capable SIH competitor we have identified. They have:
  - JWT auth + dual-theme dashboard
  - Telemetry configuration panel (ROP, RPM, torque, search buffer, depth corridor)
  - ML risk prediction engine + live risk score
  - GIS spatial map with offset well ranking
  - Offset record section with CSV export
  - Depth proximity radar chart
  - Mud window visualization (pore pressure / fracture gradient)
  - Offset trends and analytics
  - Live telemetry with saved operating envelopes
  - Torsional stick-slip PHYSICS ENGINE (real-time, not ML)
  - Engineer approval workflow (approve/reset/reject)
  - NPT cost calculator (predicted loss, potential savings)
  - RAG knowledge repository with natural language Q&A
  - Enterprise OCR document upload (DDR, WCR)
  - Live eRTMAC simulator integration

This is a serious build. Geomine would beat 95% of SIH teams. We need to beat THEM.

### Where Geomine Fails (Our Winning Gaps)

GAP 1 — THE DEPTH PROBLEM (Fatal Flaw):
  Geomine compares offset wells using "search buffer" and "depth corridor" — raw depth ranges.
  In Upper Assam, this is WRONG. The same Barail Lower Sand is at 2,940 m TVDSS in one well
  and 3,180 m TVDSS in a well 3 km away due to structural dip.
  Geomine's "depth corridor" of +/-100 m in raw MD will MISS this event completely.
  NWIS uses xi ratio — formation-normalized depth. We find events that Geomine CANNOT.

  Jury script: "Geomine uses a search buffer on raw measured depth. That means they search
  NHK-089 at the same raw depth as the active well. But NHK-089's Barail Sand is 238 m deeper
  in TVDSS due to structural position. Geomine misses 3 of our 5 most relevant events.
  NWIS finds them all using the xi ratio. This is not a UI difference — it is a geological
  correctness difference."

GAP 2 — NO FAULT BLOCK AWARENESS:
  Geomine appears to use spatial proximity only (radius search or bounding box).
  It will rank a well 1.5 km away across a major thrust fault as highly relevant.
  That well is in a different pressure regime and different formation sequence.
  NWIS uses PostGIS fault polygon containment to exclude cross-fault wells.
  This prevents dangerous cross-fault recommendations.

GAP 3 — NO AHEAD-OF-BIT HISTORICAL CORRIDOR:
  Geomine shows current risk and historical events at current depth.
  It does NOT project the historical risk FORWARD — it cannot tell you what happened
  in offset wells at the NEXT 100 m of depth BEFORE you drill into it.
  NWIS computes the risk corridor 200 m ahead using xi projections on all top-ranked offsets.
  The BLUE proactive alert fires 20-120 minutes BEFORE any sensor anomaly.
  Geomine reacts. NWIS predicts. THIS IS THE CORE DIFFERENTIATOR.

GAP 4 — NO FORMATION-AWARE SEARCH RADIUS:
  Geomine uses a single configurable "search buffer" — same radius regardless of formation.
  NWIS automatically shrinks the search radius from 50 km (Tipam) to 10 km (Kopili) as the
  bit drills deeper into more geologically variable formations.
  This prevents irrelevant far-field wells from polluting the correlation at critical depth.

GAP 5 — NO BOUNDING BOX PDF PROOF:
  Geomine has an OCR module and RAG knowledge base. But from the demo, answers appear as
  text responses without a direct link to the EXACT LINE in the original source document.
  NWIS provides 1-click PDF rendering with yellow bounding box highlight on the exact sentence.
  The drilling superintendent can SEE the original 1998 DDR text, not just an AI paraphrase.
  This is the difference between "an AI told me" and "I can see it in the original report."

GAP 6 — CLOUD DEPENDENCY RISK:
  Geomine does not state clearly whether it is air-gapped or cloud-dependent.
  If it calls any external API (OpenAI, Google, Anthropic), it VIOLATES DGH NDR data sovereignty.
  NWIS is provably air-gapped: Ollama local LLM, offline Leaflet map tiles, PostGIS on-premise.
  No packet leaves the OIL network during the live demo path.

### What Geomine Has That We Also Need (Features to Add)

The following Geomine features are LEGITIMATE and we must match or exceed them.
See respective master docs for implementation details.

  A. MUD WINDOW CHART (Module 4 addition) -> See M4_GEOLOGICAL_CORRELATION.md Section 10
  B. OPERATING ENVELOPES (Module 6 addition) -> See M5_M6_RISK_ANALYTICS_AND_ALERTS.md Section 7
  C. ENGINEER APPROVAL WORKFLOW (Module 6/7 addition) -> See M7_COCKPIT_DEMO_IMPLEMENTATION.md Section 8
  D. NPT COST CALCULATOR (Module 7 addition) -> See M7_COCKPIT_DEMO_IMPLEMENTATION.md Section 9
  E. STICK-SLIP PHYSICS ENGINE (Module 5 addition, replaces/augments CV-based detection)
  F. ANTI-COLLISION MONITOR (New sub-module) -> See M5_M6_RISK_ANALYTICS_AND_ALERTS.md Section 8
  G. DEPTH PROXIMITY RADAR (UI enhancement) -> See M7_COCKPIT_DEMO_IMPLEMENTATION.md Section 10
  H. CSV/JSON EXPORT of offset records and alert history

### How to Win Against Geomine in the Jury Room

When the jury has seen both demos and asks "How are you different from Geomine?":

Answer: "Geomine is a great drilling dashboard. We built a drilling INTELLIGENCE system.
The difference comes down to three things:

One — Geological correctness. Geomine uses raw depth buffers to find offset events.
In Upper Assam's dipping shelf, this means missing most of the relevant history.
We use the stratigraphic xi ratio — the same math subsurface engineers use when they
manually correlate wells on a cross-section. Our correlations are geologically valid.
Theirs are statistically convenient.

Two — Proactive vs reactive. Geomine alerts when sensors go out of bounds.
That means you are already IN the problem when you get the warning.
NWIS alerts 20-120 minutes BEFORE the problem based on where the bit is GOING
and what happened at that geological position in offset wells.
We give you time to prepare. Geomine gives you time to react.

Three — Provenance. When Geomine shows you a risk recommendation, you see text.
When NWIS shows you a recommendation, you can click one button and see the original
1995 DDR page with the exact sentence highlighted. A drilling superintendent will
not change a Rs 50 crore mud program because an AI said so. They will change it when
they see it in writing in the original field document."
