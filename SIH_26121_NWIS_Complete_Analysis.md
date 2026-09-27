# SIH 26121 — NWIS Complete Problem, Research & Solution Analysis

**Problem Statement ID:** 26121  
**Title:** eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations  
**Organization:** Oil India Limited  
**Category:** Software  
**Theme:** Smart Automation

---

## 1. Executive Summary

The core problem in PS 26121 is **not the absence of drilling data** and it is not simply a GIS, RAG, or machine-learning problem.

Oil India already has real-time drilling monitoring capabilities through eRTMAC and is expanding its broader digital ecosystem. The deeper gap described by the PS is the ability to turn distributed historical offset-well knowledge into **context-aware, depth-aware and evidence-backed intelligence for the active well at decision time**.

The strongest interpretation of the PS is:

> **NWIS should dynamically determine which historical offset-well intervals are relevant to the active well, correlate their geological and operational history with the current drilling context, and produce explainable early warnings backed by historical evidence.**

The central intelligence loop is:

```text
ACTIVE WELL
    ↓
CURRENT CONTEXT
(depth + formation + location + trajectory + telemetry)
    ↓
DYNAMIC OFFSET SELECTION
    ↓
RELEVANT WELLS / RELEVANT INTERVALS
    ↓
HISTORICAL EVENTS + DOCUMENT EVIDENCE
    ↓
CURRENT-vs-HISTORICAL COMPARISON
    ↓
RISK / PATTERN ASSESSMENT
    ↓
PROACTIVE EARLY WARNING
    ↓
WHY?
    ↓
SOURCE EVIDENCE + HISTORICAL MITIGATION
    ↓
ENGINEER DECISION
```

The recommended SIH prototype should **not** try to implement every advanced technology discussed in current research. A focused architecture using structured data, geospatial search, dynamic similarity, depth/formation correlation, document intelligence, hybrid retrieval, anomaly detection, limited risk ML and evidence-grounded AI is more technically defensible and more achievable.

---

# 2. What OIL Already Has

This is essential to understand before designing the system.

OIL publicly describes **eRTMAC (Real Time Data Monitoring and Analysis Centre)** as a system for real-time drilling monitoring, transmission of critical well data and continuous engineering analysis for drilling and safety decisions.

OIL also describes its broader digitalisation programme, including DRIVE 2.0, a Command and Control Centre, an OT Data Lake and other digital initiatives. OIL's current digitalisation material also lists G&G analytics using Generative AI, Digital Oil Field work, intelligent well planning/rig scheduling and AI-enabled drill-bit performance management.

An OIL eRTMAC procurement document additionally describes combining real-time rig-site data with historical data and references WITSML-based historical data.

### Correct product positioning

NWIS should therefore be positioned as:

```text
OIL DIGITAL ECOSYSTEM

     eRTMAC
       │
       │ current / real-time context
       ▼
   ACTIVE WELL
       │
       ├───────────────────────┐
       │                       │
       ▼                       ▼
 historical records       NWIS intelligence
 DDR / WCR / Mud Logs          │
 G&G / surveys / etc.          ▼
                         contextual decision support
```

### Do NOT claim

> “OIL has real-time data but no digital platform.”

That is too broad and inconsistent with OIL's own digitalisation material.

### Better positioning

> “OIL already generates and stores large amounts of real-time and historical drilling data. NWIS turns that distributed information into contextual, depth-aware offset intelligence at the moment an engineer needs it.”

---

# 3. What Is an Offset Well?

An **offset well** is an existing wellbore located near a proposed/current well and used to provide information for planning and operational decisions.

The practical value is not merely geographic proximity. A relevant offset can provide knowledge about:

- formation behaviour
- drilling parameters
- pressure behaviour
- mud losses
- kicks
- stuck pipe
- borehole instability
- casing decisions
- cementing
- NPT
- operational mitigation
- lessons learned

The central NWIS question is therefore:

> **Which historical wells and which intervals inside those wells are actually relevant to what is happening in the active well right now?**

---

# 4. Decomposing the PS

The PS can be reduced to four core user problems.

## Problem 1 — Find nearby and relevant wells

The PS asks for an interactive geospatial map of nearby wells.

### Basic solution

```text
Active well
   ↓
Radius search
   ↓
Nearby wells on map
```

### Limitation of the basic solution

Distance alone does not tell the engineer which well is useful.

A well 12 km away may be much more relevant than a well 5 km away if it shares:

- formation
- depth interval
- trajectory
- drilling section
- historical event behaviour

### Optimal solution

Use two stages:

```text
Stage 1 — Spatial candidate retrieval
        ↓
Stage 2 — Contextual relevance ranking
```

Potential ranking dimensions:

- geographical proximity
- formation similarity
- depth overlap
- trajectory similarity
- hole-section similarity
- drilling-condition similarity
- historical-event similarity

The result should be explainable.

Example:

```text
WELL X05

Distance               11.4 km
Formation similarity   91%
Depth overlap          88%
Trajectory similarity 79%
Event similarity       94%

Overall relevance      HIGH
```

The percentages above are illustrative unless actually calculated from the prototype data.

### Research basis

Research on automated offset-well selection has explored geological information, trajectories, casing designs, drilled intervals and operational parameters instead of simple geographic selection.

Research on well similarity has also explored **well-level and interval-level similarity**, which is directly relevant to NWIS.

---

# 5. Problem 1 — Best Design Decision

## Use a Dynamic Offset Relevance Engine

The relevance of an offset should be able to change as the active well changes.

At 2,000 m:

```text
Well A = highly relevant
Well B = moderate
Well C = low
```

At 3,200 m:

```text
Well A = moderate
Well B = highly relevant
Well C = highly relevant
```

Reasons can include a formation change, a new drilling section, a new trajectory context or a change in the current telemetry state.

### Strongest differentiator

> **“Nearby” is not the same as “relevant.”**

---

# 6. Problem 2 — Historical Knowledge Is Fragmented

The PS states that useful information can live across:

- Well Completion Reports
- Daily Drilling Reports
- mud logging information
- drilling databases
- historical well parameters
- reservoir/geological records
- casing programs
- cementing records
- incident records
- individual experience

OIL's own drilling-related documentation specifies rich well records such as depth, formations, BHA, drilling parameters, DDRs, mud reports, deviation records, casing/tubular information, bit performance, lithology, cementing, drilling complications and remedies.

### Why this matters

The problem is not that the information does not exist.

The problem is that the engineer has to spend time traversing different formats and sources before reaching an answer.

---

# 7. Current Industry Solutions for Historical Knowledge

Several commercial systems address parts of this problem:

### Peloton WellView

Provides structured well lifecycle information, historical data, reporting and benchmarking.

### Halliburton OpenWells

Provides operational data management, NPT analysis, offset benchmarking and lessons learned.

### Cognite — Know Your Well

A particularly close conceptual reference. Cognite describes a system for finding relevant offset-well information quickly, reducing dependence on individual engineer memory and surfacing lessons learned across drilling information.

### SLB — Tela Offset Wells Insights

Uses AI to consolidate offset-well data from reports, databases, folders, PDFs and images into contextual information for drilling engineers.

### Halliburton historical/NLP workflows

Use natural-language processing and document extraction to turn historical drilling reports into operationally useful information.

---

# 8. Optimal Solution for Problem 2

Do **not** build only a vector database over PDFs.

Use a hybrid historical knowledge pipeline:

```text
Historical PDF / report / scan
          ↓
      Parser / OCR
          ↓
   Event & entity extraction
          ↓
   ┌───────────────┐
   │               │
   ▼               ▼
Structured DB    Search index
   │               │
   │          BM25 + Vector
   │               │
   └───────┬───────┘
           ▼
     Evidence retrieval
           ↓
          LLM
           ↓
     Answer + sources
```

### Store facts structurally

Example:

```text
Event: MUD_LOSS
Well: W23
Depth: 3245–3262 m
Formation: Formation C
Severity: High
Mitigation: LCM treatment
Source: DDR_W23_2024.pdf
Page: 47
```

### Why hybrid retrieval is better

A precise drilling question such as:

> “Which nearby wells had mud loss around 3250 m?”

should be solved with structured filtering first:

1. find relevant wells
2. filter formation
3. filter depth
4. filter event type
5. rank by relevance
6. retrieve narrative evidence
7. produce an explanation

RAG should provide contextual evidence, not replace the data model.

---

# 9. Event Extraction from Drilling Reports

A directly relevant peer-reviewed study investigated automatic event extraction from DDRs, including events such as:

- kick
- loss of circulation
- stuck pipe
- bump
- drag

It compared rule-based and transformer-based approaches.

The important design lesson for NWIS is:

> **Use NLP/LLM extraction with validation, not uncontrolled LLM-only extraction.**

An event should become a normalized object with:

- well
- depth
- formation
- event type
- severity
- consequence
- mitigation
- NPT
- date
- source document
- page
- extraction confidence

The original evidence should always be preserved.

---

# 10. Problem 3 — Cross-Well Correlation

This is one of the hardest parts of the PS.

The system has to correlate:

- drilling parameters
- reservoir/geological context
- formation
- depth
- historical incidents
- current drilling state
- potentially trajectory and well design

A simple example:

```text
W03
Formation C
3238–3260 m
Mud loss

W05
Formation C
3244–3268 m
Mud loss

W09
Formation C
3240–3255 m
Torque spike

ACTIVE WELL
Formation C
Current depth = 3220 m
```

The important question is whether these historical intervals are genuinely comparable.

---

# 11. Depth Correlation Must Be Interval-Aware

Do not represent an event merely as:

> “Well W03 had mud loss.”

Represent it as:

> “Well W03 experienced mud loss in Formation C between approximately 3238 and 3260 m.”

The system should use, where available:

- measured depth (MD)
- true vertical depth (TVD)
- formation interval
- trajectory
- hole section
- operational state

WITSML provides standardized concepts for wellbore trajectories, logs and time/depth-indexed drilling data.

### Important implication

Two whole wells may be only moderately similar while one interval in one well may be highly relevant to the current interval.

That is why **interval-level similarity** is particularly valuable.

---

# 12. Optimal Cross-Well Correlation Architecture

```text
Current well context
       │
       ├── location
       ├── formation
       ├── MD / TVD
       ├── trajectory
       ├── drilling section
       └── current telemetry
              ↓
      candidate offset wells
              ↓
       well-level similarity
              ↓
      interval-level similarity
              ↓
      historical event matching
              ↓
        contextual relevance
```

### Do not make GNN mandatory

GNNs are an interesting research direction, but not every graph-based paper maps directly to drilling offset relevance.

For example, graph-based reservoir connectivity studies do not automatically establish that a GNN is the correct model for your offset-well similarity problem.

For an SIH prototype, a transparent feature-based similarity engine is more defensible and easier to validate.

A learned/GNN approach can be future research.

---

# 13. Signature Feature — Historical Risk Corridor

This should be one of the main visual/technical features of NWIS.

Example:

```text
ACTIVE WELL
Formation C
Current depth = 3220 m

Historical events:

W03 → 3238–3260 m → Mud loss
W05 → 3244–3268 m → Mud loss
W09 → 3240–3255 m → Torque spike

              HISTORICAL RISK CORRIDOR
              3235 ───────────── 3270 m
                         ↑
                    Current = 3220 m
                    Distance = 15 m
```

Instead of saying:

> “This well had mud loss.”

NWIS can say:

> **“The active well is approaching an interval where multiple relevant offset wells experienced similar events.”**

This directly satisfies the PS's proactive-alert requirement.

---

# 14. Problem 4 — Risk Prediction and Proactive Alerts

The PS specifically calls for predictive analytics for:

- mud losses
- stuck pipe
- overpressure/kicks
- torque spikes
- cementing issues

The important distinction is:

### Detection

Something abnormal has already happened.

### Prediction / early warning

The current state is becoming similar to a state that historically preceded a problem.

NWIS should focus on the second.

---

# 15. What Current Research Says About Drilling-Risk AI

Current research confirms strong activity in:

- stuck-pipe prediction
- kick early warning
- lost-circulation prediction
- torque prediction
- drilling anomaly detection
- real-time precursor identification
- explainable ML

But research also repeatedly identifies limitations in:

- data quality
- class imbalance
- generalisation between wells/fields
- variable selection
- spatial/temporal bias
- false alarms
- interpretability
- robustness
- data leakage

Therefore avoid presenting one model's published result as a guaranteed result for OIL.

For example, a study may report excellent accuracy on a particular dataset, but that does not mean an unseen OIL field will reproduce that performance.

---

# 16. Optimal Risk Engine

For SIH, use a hybrid risk engine rather than trying to build a fully autonomous AI controller.

### Layer 1 — Historical prior

Example:

```text
5 relevant offset wells
3 experienced mud loss
same formation
similar interval
```

### Layer 2 — Current anomaly

Monitor current telemetry for abnormal behaviour.

Potential variables include:

- torque
- ROP
- WOB
- SPP
- flow rate
- mud weight
- ECD
- hook load
- other available channels

### Layer 3 — Predictive model

Use ML where data supports it.

Potential methods:

- gradient boosting
- random forest
- anomaly detection
- autoencoder/time-series methods
- other validated models

### Combined context

```text
Historical evidence
      +
Current anomaly
      +
Formation/depth context
      +
ML signal
      ↓
Contextual risk
```

This is more explainable than:

```text
XGBoost → 82%
```

---

# 17. Proactive Warning Should Be Lead-Time Aware

The system should warn before an event where historical evidence supports that behaviour.

Example:

```text
Current depth: 3220 m
Historical corridor: 3235–3270 m
Distance: 15 m
Relevant wells: 3
Current telemetry: torque trend abnormal

STATUS: EARLY WARNING
```

Then as the well progresses:

```text
3220 m → Early warning
3240 m → Risk escalating
3245 m → Historical risk corridor entered
```

This is much closer to the wording and intent of the PS than post-event reporting.

---

# 18. Do Not Alert from One Signal Alone

A better alert combines multiple evidence streams.

```text
               CURRENT TELEMETRY
                      │
                anomaly signal
                      │
Historical offsets ───┼── Formation / depth
                      │
                      ▼
                 Risk engine
                      │
                      ▼
                Contextual risk
```

For example:

```text
Historical evidence    HIGH
Current anomaly        MEDIUM
ML prediction          HIGH
Depth proximity        HIGH
Formation similarity   HIGH

Overall contextual risk: HIGH
```

The exact aggregation formula should be validated against your dataset.

---

# 19. Risk-Specific Strategy

| Risk | Recommended approach |
|---|---|
| Mud loss | Historical risk corridor + formation/depth context + pressure/mud anomalies + ML where supported |
| Stuck pipe | Historical events + torque/hookload/ROP trends + anomaly/precursor detection |
| Kick/overpressure | Multi-parameter anomaly detection + pressure/flow/mud context + historical analogs |
| Torque spike | Time-series anomaly/prediction + historical analog comparison |
| Cementing issue | Historical casing/cement-job comparison; predictive only when sufficient labelled data exists |

Do not assume all five risks require the same model.

---

# 20. Historical Mitigation / Recommendation Layer

The system should not make unsupported autonomous drilling commands.

Avoid a prototype output such as:

> “Reduce WOB to 18.3 kN immediately.”

unless there is a validated engineering control model, approved operating envelope and suitable domain validation.

Instead, provide:

```text
Risk detected
    ↓
Relevant historical cases
    ↓
What happened
    ↓
What was done previously
    ↓
Source evidence
    ↓
Engineer review
```

Example:

> “Three comparable offset wells experienced mud loss in this interval. Historical mitigation included LCM treatment. Review supporting reports before selecting the operational response.”

This keeps the system in the correct **human-in-the-loop decision-support** role.

---

# 21. Evidence Is a First-Class System Component

Every important output should expose:

```text
WHAT
Risk / event / pattern

WHY
Depth + formation + telemetry + historical evidence

WHICH WELLS
Supporting offset wells

WHERE
Depth / interval

SOURCE
Document + page

QUALITY
Data quality / evidence strength
```

The user should be able to go from:

**Alert → reason → supporting wells → historical event → original page**

without leaving the workflow.

This is one of the strongest ways to make the prototype trustworthy.

---

# 22. Separate Different Kinds of Confidence

Do not use a single “confidence” field for everything.

Keep separate concepts such as:

- model probability
- similarity score
- evidence strength
- extraction confidence
- data quality
- historical sample size

Example:

```text
Risk: HIGH

Model probability: 0.78
Historical evidence: HIGH
Data quality: GOOD
Relevant historical cases: 4
```

A probability of 0.78 should not automatically be presented as “78% chance of failure” unless the model has been properly calibrated for that interpretation.

---

# 23. Include “Insufficient Historical Evidence”

This is an important reliability feature.

If there are no relevant analogs, the system must not automatically interpret that as low risk.

Correct:

> **Insufficient historical analog evidence.**

Incorrect:

> **Low risk.**

Similarly:

```text
Historical evidence: LOW
Current anomaly: HIGH
ML signal: MEDIUM
```

should produce a cautious state rather than false certainty.

---

# 24. Digital Twin — What To Use and What Not To Use

Digital twins are an active research/industry direction in drilling.

However, a full high-fidelity physics-based digital twin is not necessary for the SIH MVP.

### Recommended

Build a lightweight **Drilling Context / Replay Model**.

It should represent:

- current well state
- depth progression
- formation
- trajectory
- telemetry
- historical analogs
- risk state

Then replay the active well through depth.

### Avoid

A large physics simulation stack that takes the project away from the core PS.

### Why

The demo value comes from showing:

```text
Current state
   ↓
approaching historical corridor
   ↓
risk changes
   ↓
alert appears
```

A full digital twin is a potential future research/production extension.

---

# 25. Knowledge Graph — Recommended Scope

A knowledge graph can be useful, but it does not need to become a huge separate enterprise platform.

Represent relationships such as:

```text
Well X
 ├── encountered → Formation C
 ├── experienced → Mud Loss
 ├── occurred_at → 3248 m
 ├── mitigated_by → LCM
 └── documented_in → DDR-X-03
```

A relational database with explicit relationships plus vector retrieval can provide most of the MVP value.

A graph-specific implementation can be added later where it genuinely improves multi-hop reasoning.

---

# 26. Agentic AI — Recommended Scope

Use an AI agent as an **orchestrator**, not as the drilling decision-maker.

Example tools:

```text
find_nearby_wells()
rank_offset_wells()
query_events()
query_depth_interval()
compare_wells()
search_reports()
retrieve_source_page()
get_current_telemetry()
calculate_risk_context()
```

Workflow:

```text
Engineer question
      ↓
Agent
      ↓
Domain tools
      ↓
Structured + document evidence
      ↓
LLM explanation
```

This is much more defensible than a multi-agent swarm where every agent is essentially a prompt wrapper.

---

# 27. What NOT to Make Core MVP

The following technologies are interesting but should not be required to prove PS 26121:

### GNN
Keep as future research unless a strong dataset/use case justifies it.

### PINN
Use only if you have a genuinely suitable physics problem and validation data.

### DRL
Do not use for autonomous drilling-parameter prescriptions in the MVP.

### Federated learning
Useful for cross-region/cross-operator training under privacy constraints, but not necessary to solve the core retrieval/context problem.

### Full digital twin
Future extension, not MVP requirement.

### Huge multi-agent swarm
Not needed.

### Decorative 3D rig
Not necessary.

### Generic chatbot
Not sufficient.

---

# 28. Recommended Overall Architecture

```text
                         OIL DIGITAL ECOSYSTEM
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                  eRTMAC       Historical     G&G / Well
               real-time data    records         data
                    │             │             │
                    └─────────────┼─────────────┘
                                  ▼
                         ┌──────────────────┐
                         │ CURRENT CONTEXT  │
                         │ Well / Depth /   │
                         │ Formation / Geo  │
                         │ Trajectory /     │
                         │ Telemetry        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ OFFSET ENGINE    │
                         │ spatial +        │
                         │ contextual       │
                         │ similarity       │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
             Historical DB   Document RAG   Telemetry ML
                    │             │             │
                    └─────────────┼─────────────┘
                                  ▼
                         ┌──────────────────┐
                         │    RISK ENGINE   │
                         │ History + rules  │
                         │ + anomaly + ML   │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │ HISTORICAL RISK  │
                         │ CORRIDOR         │
                         │ + LEAD TIME      │
                         └────────┬─────────┘
                                  ▼
                         ┌──────────────────┐
                         │ EVIDENCE ENGINE  │
                         │ wells + events + │
                         │ docs + pages     │
                         └────────┬─────────┘
                                  ▼
                            AI EXPLANATION
                                  │
                                  ▼
                            ENGINEER ALERT
                                  │
                                  ▼
                         HUMAN DECISION
```

---

# 29. Recommended Technology Direction

## Frontend

- React
- TypeScript
- Tailwind CSS
- Leaflet or Mapbox
- Plotly / Recharts

## Backend

- Python
- FastAPI

## Database

- PostgreSQL
- PostGIS

## Retrieval

- pgvector or Qdrant
- BM25 + semantic search

## Document processing

- PyMuPDF
- OCR where necessary
- structured extraction pipeline

## ML

- scikit-learn
- gradient boosting where appropriate
- anomaly detection
- SHAP/XAI where appropriate

## AI

- local/offline-capable model via Ollama where practical
- tool-augmented AI interface

## Deployment

- Docker
- docker-compose

Avoid unnecessary microservices.

---

# 30. Data Strategy for SIH Prototype

Actual OIL operational data may not be available to the student team.

Use:

### Public data

Legitimate open datasets such as:

- Equinor Volve
- FORCE 2020
- other appropriate public drilling/well-log datasets
- DataDrill where suitable

### Synthetic demonstration data

Build realistic but explicitly labelled prototype records for:

- 10–20 wells
- formations
- coordinates
- trajectories
- drilling parameters
- historical events
- DDR-like reports
- WCR-like records
- simulated telemetry

Never present synthetic records as actual OIL confidential information.

The purpose is to prove that the architecture can accept real OIL data later.

---

# 31. WITSML and Data Standards

WITSML is important because it provides an established oil-and-gas data model for well-related information such as:

- wellbores
- trajectories
- logs
- mud logs
- drilling data
- reports
- time/depth-indexed information

NWIS should therefore use a domain model that can be mapped to WITSML concepts rather than inventing an incompatible data model.

A complete OSDU implementation is not required for SIH, but future enterprise integration should remain compatible with the broader industry data-standard direction.

---

# 32. Main User Experience

The system should not have dozens of pages.

The most important experience is one operational cockpit.

Example:

```text
┌────────────────────────────────────────────────────────┐
│ ACTIVE WELL: OIL-X07               DEPTH: 3220 m      │
│ FORMATION: C                        STATUS: DRILLING   │
├─────────────────────────────┬──────────────────────────┤
│                             │ CURRENT RISK             │
│            MAP              │ Mud loss: MEDIUM        │
│                             │ Stuck pipe: LOW         │
│       active + offsets      │ Kick: LOW               │
│                             │                          │
├─────────────────────────────┼──────────────────────────┤
│       DEPTH CORRELATION     │ UPCOMING RISK           │
│                             │                          │
│ current depth               │ 3235–3270 m             │
│ historical events           │ 3 relevant wells        │
│ formation intervals         │ 15 m away               │
├─────────────────────────────┴──────────────────────────┤
│ WHY THIS ALERT?                                        │
│ • Similar offsets experienced mud loss                 │
│ • Current depth approaching historical corridor        │
│ • Current telemetry pattern is changing                │
│                                                        │
│ EVIDENCE                                               │
│ W03 DDR p.42 | W05 WCR p.118 | W09 MudLog p.31       │
└────────────────────────────────────────────────────────┘
```

The map, depth correlation and evidence are more important than decorative visual effects.

---

# 33. Live / Simulation Mode

Because actual eRTMAC live data will not be available for the prototype, use deterministic replay/simulation.

Example progression:

```text
3180 m
 ↓
3200 m
 ↓
3220 m
 ↓
3240 m
 ↓
3250 m
```

At each point, update:

- telemetry
- relevant offsets
- risk
- historical corridor distance
- alerts

The demo should be repeatable and resettable.

---

# 34. Benchmarking / Validation

The prototype should measure actual behaviour rather than invent claims.

## Retrieval

- Precision@5
- Recall@5
- MRR

## Extraction

- event extraction accuracy
- depth extraction accuracy
- formation extraction accuracy

## RAG

- answer correctness
- citation correctness
- citation coverage
- hallucination/error rate

## Risk

- precision
- recall
- F1
- false-alarm rate
- lead time

## System

- ingestion time
- query latency
- retrieval latency
- model latency
- offline behaviour

Do not claim industrial performance from a small synthetic dataset.

---

# 35. Reliability Principles

NWIS should:

- preserve source evidence
- distinguish model probability from evidence strength
- show uncertainty
- avoid unsupported recommendations
- handle insufficient historical evidence
- degrade gracefully if AI services fail
- support offline operation where practical
- use deterministic logic where it improves trust
- maintain human oversight

The prototype should answer:

> **Why did you raise this alert?**

and be able to show the chain from current state to historical evidence.

---

# 36. What Current Industry Products Teach Us

## SLB

The current DrillOps ecosystem integrates real-time and historical information, multiwell analysis, risk objects and operational decision support.

**Lesson:** integrate high-frequency current signals with lower-frequency contextual history.

## SLB Tela

Uses AI to consolidate heterogeneous offset-well information.

**Lesson:** the document/retrieval problem is real, but a generic chatbot is not enough.

## Halliburton

Current offset-well analysis work combines selection of relevant wells with document analysis, hazards, NPT, losses, instability and depth-linked lessons.

**Lesson:** relevance + historical extraction + depth context is an established industrial pattern.

## Baker Hughes

Current drilling-hazard products use offset analysis, interactive maps, hazard prediction and dynamic risk registers.

**Lesson:** the map is useful, but the intelligence layer is what makes the product operationally valuable.

## Weatherford

Centro combines real-time information, analytics, predictive algorithms, smart alarms and multiwell context.

**Lesson:** real-time analytics need contextualisation and alert quality.

## NOV

KAIZEN compares current drilling performance to offset information and supports optimization.

**Lesson:** historical offset data can become a live reference baseline.

## Cognite

Know Your Well focuses on finding relevant historical information and reducing dependency on individual engineer memory.

**Lesson:** “institutional memory” is a genuine industrial use case.

---

# 37. Current Research Directions Relevant to NWIS

These are the research areas worth following.

## 1. Automated offset-well selection

How to choose analog wells using more than distance.

## 2. Well/interval similarity learning

How to identify comparable wells and comparable depth intervals.

## 3. Depth-aware interwell correlation

How to align historical events with current formation/depth context.

## 4. DDR NLP

How to extract events/entities from drilling reports.

## 5. Hybrid RAG / tool-augmented drilling AI

How to query structured measurements and narrative reports together.

## 6. Real-time anomaly detection

How to identify early deviations from normal drilling behaviour.

## 7. Stuck-pipe prediction

How to detect precursors rather than only the incident.

## 8. Mud-loss prediction

How to combine geological, drilling and pressure/mud parameters.

## 9. Kick/overpressure early warning

How to fuse multiple time-series signals.

## 10. Torque prediction

How current drilling situations can be compared to similar historical scenarios.

## 11. Digital twins

How dynamic well representations can connect current states with predictive/optimization systems.

## 12. Physics-informed ML

How engineering constraints can improve robustness.

These are research directions, not requirements that all need to be implemented in the SIH prototype.

---

# 38. Important Research Interpretation Rules

Do not make these mistakes:

### Mistake 1
A paper uses a GNN → therefore GNN is optimal for NWIS.

**Wrong.** The paper's task may be different.

### Mistake 2
A paper reports 97% accuracy → therefore NWIS will get 97%.

**Wrong.** Dataset, class balance, leakage, calibration and domain transfer matter.

### Mistake 3
A digital-twin paper exists → therefore a full digital twin is necessary.

**Wrong.** A research direction is not automatically an MVP requirement.

### Mistake 4
A product uses agents → therefore NWIS needs many agents.

**Wrong.** The business outcome matters more than agent count.

### Mistake 5
An LLM can read PDFs → therefore structured extraction is unnecessary.

**Wrong.** Precise depth/event filtering and auditability benefit from structured data.

---

# 39. Corrected View of an Over-Advanced Architecture

An earlier research analysis proposed:

- multimodal VLM
- agentic SQL
- dynamic knowledge graph
- GNN/DHGC
- PINN
- causal AI
- DRL
- federated learning
- knowledge-embedded digital twin

Some of these are genuine research directions, but this is not the optimal MVP.

### Better allocation

| Component | Decision |
|---|---|
| OCR | KEEP |
| NLP/event extraction | KEEP |
| VLM | selective use |
| agentic SQL/tool layer | KEEP in focused form |
| hybrid RAG | KEEP |
| lightweight relationship model/knowledge graph | optional but useful |
| dynamic offset relevance | CORE |
| interval/depth correlation | CORE |
| anomaly detection | KEEP |
| risk ML | KEEP for selected risks |
| SHAP/XAI | KEEP where model supports it |
| GNN | future research |
| PINN | future research |
| DRL | future research |
| federated learning | future research |
| full digital twin | future research |
| lightweight replay/context model | KEEP |
| evidence/citations | CORE |
| uncertainty/evidence quality | ADD |

---

# 40. The Single Most Important Differentiator

The system should answer:

> **“Why is this historical well relevant to me right now?”**

That question is stronger than:

> “Which wells are nearby?”

and stronger than:

> “What does the chatbot know?”

A good answer should be:

```text
Well X05 is highly relevant because:

• it is geographically close
• it shares the current formation
• its drilled interval overlaps the current depth
• its trajectory is comparable
• it experienced a similar historical event
• current telemetry resembles the pre-event pattern

Supporting evidence:
DDR X05 — page 117
WCR X05 — page 42
```

That is contextual intelligence.

---

# 41. Proposed Final Product Concept

## NWIS — Contextual Offset Intelligence

### Four questions

**FIND**  
Which offset wells are relevant?

**UNDERSTAND**  
What happened there?

**CORRELATE**  
Does the active well resemble the historical situation?

**WARN**  
Is the active well approaching a historically risky situation?

### Fifth layer

**PROVE**  
Can the system show the evidence behind its conclusion?

---

# 42. Final Architecture to Defend at SIH

```text
                 CURRENT ACTIVE WELL
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          Location    Formation    Telemetry
              │          │          │
              └──────────┼──────────┘
                         ▼
              DYNAMIC OFFSET SEARCH
                         ▼
              CONTEXTUAL RELEVANCE
                         ▼
              RELEVANT WELL INTERVALS
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
       Event DB      Document RAG    Anomaly ML
           │             │             │
           └─────────────┼─────────────┘
                         ▼
                   RISK ENGINE
               history + rules + ML
                         ▼
                HISTORICAL CORRIDOR
                         ▼
                    LEAD TIME
                         ▼
                 EVIDENCE ENGINE
                         ▼
                 EXPLAINABLE ALERT
                         ▼
                ENGINEER DECISION
```

---

# 43. Final Recommended Positioning for the SIH Presentation

### Weak positioning

> “We built an AI chatbot for Oil India drilling data.”

### Better positioning

> “We built an AI-powered nearby-well knowledge system.”

### Strong positioning

> **“NWIS dynamically identifies the historical offset-well intervals that are most relevant to the active well, correlates those historical events with current drilling conditions, and provides evidence-backed early warnings to the drilling engineer.”**

### Core message

> **Nearby is not the same as relevant. NWIS finds the history that matters right now.**

---

# 44. Practical MVP Boundary

The strongest initial prototype should prove one end-to-end loop:

```text
10–20 wells
      ↓
interactive map
      ↓
radius filtering
      ↓
dynamic relevance ranking
      ↓
depth/formation correlation
      ↓
historical events
      ↓
supporting documents
      ↓
live telemetry simulation
      ↓
historical risk corridor
      ↓
early warning
      ↓
WHY THIS ALERT?
      ↓
evidence + historical mitigation
```

If this loop works reliably, it demonstrates the core of PS 26121.

Everything else is secondary.

---

# 45. Sources and Reference Categories

## Primary OIL sources

- Oil India — Technology / eRTMAC
  https://www.oil-india.com/leveraging-technology

- Oil India — Digitalisation / DRIVE
  https://www.oil-india.com/digitalfootprint

- OIL eRTMAC procurement material
  https://www.oil-india.com/files/oldtender/national/CORR6_CDH6605P21.pdf

- OIL drilling / mud-logging documentation
  https://www.oil-india.com/files/oldtender/global/Doc_CDG8459P16.pdf

## Industry systems

- Cognite — Know Your Well / Drilling & Wells
  https://hub.cognite.com/drilling-wells-443/welcome-to-the-drilling-wells-group-on-cognite-hub-4996

- SLB — DrillOps Performance Insights
  https://www.slb.com/products-and-services/delivering-digital-at-scale/software/delfi/delfi-solutions/drillops/drillops-performance-insights

- SLB — Tela Offset Wells Insights
  https://www.slb.com/products-and-services/delivering-digital-at-scale/artificial-intelligence-solutions/innovation-factori/tailored-solutions/tela-agentic-ai-assistant-for-offset-wells-insights

- SLB — DrillPlan
  https://www.slb.com/products-and-services/delivering-digital-at-scale/software/delfi/delfi-solutions/drillplan/DrillPlan-Features

- Halliburton — Digital Well Construction
  https://www.halliburton.com/en/software/decisionspace-365-enterprise/digital-well-construction

- Halliburton — iVRO
  https://www.halliburton.com/en/products/integrated-virtual-remote-operations

- Baker Hughes — Drilling Hazard Prevention
  https://www.bakerhughes.com/oilfield-services-and-equipment-digital/well-planning/drilling-hazard-prevention

- Baker Hughes — JewelSuite
  https://www.bakerhughes.com/oilfield-services-and-equipment-digital/well-planning/jewelsuite-well-engineering

- Weatherford — Centro
  https://www.weatherford.com/drilling-and-evaluation/drilling-services/centro-well-construction-optimization-platform/

- NOV — KAIZEN
  https://www.nov.com/products/kaizen-intelligent-drilling-optimizer

- Peloton — WellView
  https://www.peloton.com/products/well-data-lifecycle/wellview

- Corva — Drilling
  https://www.corva.ai/energy/drilling

## Open-source / technical references

- DrillMind
  https://github.com/ArokyaMatthew/DrillMind

- DrillSense
  https://github.com/poetabdullah/DrillSense

- DDR_UTAH_FORGE
  https://github.com/djimrastephane/DDR_UTAH_FORGE

- Webviz Subsurface Components
  https://github.com/equinor/webviz-subsurface-components

## Data / standards

- Equinor Volve dataset
  https://www.equinor.com/energy/volve-data-sharing

- Energistics WITSML
  https://docs.energistics.org/WITSML/

## Research starting points

- TADI — Tool-Augmented Drilling Intelligence
  https://arxiv.org/abs/2605.00060

- Similarity Learning for Wells Based on Logging Data
  https://www.sciencedirect.com/science/article/pii/S0920410522005587

- Automatic Event Identification and Extraction from Daily Drilling Reports
  https://www.sciencedirect.com/science/article/pii/S0920410521005982

- Review of Stuck Pipe Prediction Methods and Future Directions
  https://jpt.spe.org/review-of-stuck-pipe-prediction-methods-and-future-directions

- Real-time drilling torque prediction with just-in-time learning
  https://www.sciopen.com/article/10.1016/j.petsci.2024.12.014

- Digital Twins for Real-Time Scenario Analysis during Well Construction
  https://www.mdpi.com/1996-1073/15/18/6584

- DataDrill public dataset / drilling pressure and kick research
  https://connect.spe.org/blogs/bruno-mapurunga/2025/06/26/datadrill-public-dataset-for-formation-pressure-pr

---

# 46. Accuracy / Interpretation Notes

1. Vendor product pages are useful for understanding product capabilities but may contain vendor-reported customer outcomes; they are not automatically independent benchmarks.
2. Research-paper results are tied to their datasets, assumptions and experimental setups and should not be transferred directly to OIL deployment.
3. Published research supports the component techniques, but there is no verified universal “best architecture” for drilling intelligence.
4. The strongest claims for SIH should therefore be about the **prototype's measured behaviour**, not about guaranteed industrial outcomes.
5. Synthetic prototype data must be explicitly labelled and must not be represented as confidential OIL data.
6. Human-in-the-loop decision support is the safest and most defensible framing for an SIH prototype involving drilling operations.

---

# 47. Final One-Paragraph Definition

**NWIS is an AI-assisted institutional-memory and decision-support layer for drilling operations. It combines current active-well context with geospatial, geological, trajectory, drilling and historical document information to dynamically identify the most relevant offset-well intervals. It correlates historical drilling events with current well conditions, detects emerging risk patterns, warns engineers when the active well approaches historically problematic intervals, and provides the underlying evidence and historical mitigation so that qualified engineers can make faster, better-informed operational decisions.**

---

# 48. The Core Principle

> ## **Do not build an AI system that merely knows drilling history. Build a system that knows which history matters to the drilling engineer right now.**

