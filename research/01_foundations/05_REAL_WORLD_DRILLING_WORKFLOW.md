# SIH 26121 — Real-World Drilling Workflow & The Historical Knowledge Gap

## 1. Executive Summary
This document reconstructs the complete lifecycle of a drilling project in an upstream operator like Oil India Limited (OIL), tracing how operational information is generated, consumed, fragmented, and lost across three distinct phases: **Pre-Drill Planning**, **Active Well Execution**, and **Post-Drill Review**. It explicitly isolates where manual cognitive friction occurs and where NWIS acts as a force multiplier.

---

## 2. Phase 1: Pre-Drill Well Planning Workflow

Before a drilling rig arrives on location (spud date), a well undergoes 3 to 12 months of intensive planning by a multidisciplinary asset team:

```
[PRE-DRILL PLANNING TIMELINE: 3–12 MONTHS]
Subsurface G&G Interpretation (Seismic, Stratigraphy, Reservoir Limits)
       ↓
Offset Well Identification (Manual search in folders, paper archives, shared drives)
       ↓
Pore Pressure & Fracture Gradient (PPFG) Prediction from Offset Logs
       ↓
Trajectory & Anti-Collision Planning (Wellpath design: KOP, Build, Hold, Target)
       ↓
Casing Seat Selection & Sizing (Ensuring safe mud weight margins)
       ↓
Drilling Fluid & Rheology Formulation (Mud weight window, chemistry)
       ↓
Drilling Programme Authoring (Detailed operational playbook issued to rig)
```

### The Knowledge Breakdown in Pre-Drill Planning:
- **How Offsets Are Chosen Today:** Well planners typically draw a circle on a map and ask colleagues for well numbers within 5–10 km. If a well was drilled in 2012 by an engineer who left the company, its critical lessons (e.g. *"Bit balling occurs in the upper Tipam sand if WOB exceeds 12 tonnes"*) are completely overlooked unless explicitly written in an executive summary.
- **The PDF Digging Burden:** The planning engineer spends **40–60 hours per well** opening dozens of PDF files, copying casing depths by hand into spreadsheets, and manually cross-referencing mud weight graphs.
- **Where NWIS Intervenes:** NWIS automatically discovers and ranks offset wells by stratigraphic and operational relevance, compiles historical NPT registers across the planned trajectory, and extracts formation-specific casing/mud benchmarks in minutes.

---

## 3. Phase 2: Active Well Execution Workflow (Real-Time Drilling)

Once the drill bit starts turning, operations run in continuous 12-hour shifts. Real-time data streams from the rig floor to the on-site cabin and remotely to Oil India's **eRTMAC Command Centre**:

```
[REAL-TIME DRILLING OPERATIONAL LOOP]
Rig Sensors & MWD/LWD Pulsers (Telemetry streamed every 1–5 seconds)
       ↓
Surface Sensor Acquisition Unit & Mud Logging Unit (Aggregates WITS/WITSML)
       ↓
Telemetry Transmission via Satellite/Fiber to eRTMAC Command Centre
       ↓
Continuous Monitoring by Shift Engineers (Visualizing ROP, WOB, Torque, SPP)
       ↓
Geological Steering & Formation Top Verification (Matching LWD Gamma Ray to Prog)
       ↓
OPERATIONAL EVENT OCCURS (e.g., unexpected torque rise, slight mud loss)
       ↓
CRITICAL BOTTLENECK: What caused this? Has this happened before?
       ↓
MANUAL SEARCH OR GUESSWORK (Phone calls, memory, search through old DDRs)
       ↓
Operational Decision (Adjust mud weight, pull out of hole, spot pill)
```

### The Information Bottleneck During Active Drilling:
1. **The Clock Is Ticking:** At ₹1,000+ per minute of rig operating time, a drilling supervisor has at most **15 to 30 minutes** to respond to a deteriorating downhole condition before it escalates into a catastrophic stuck pipe or kick.
2. **Context Switching Under Stress:** The engineer in the eRTMAC center or rig cabin cannot navigate 10 nested directories on an intranet to find what mud weight was used in Well `NH-05` when it hit the same limestone stringer five years ago.
3. **Reactive vs. Proactive Alarms:** eRTMAC displays live curves. If mud flow out drops, eRTMAC shows the drop *now*. But it does not tell the engineer: *"You are 20 meters above the fractured thief zone where offset well NH-09 lost 40 m³ of mud"*.
4. **Where NWIS Intervenes:** NWIS runs continuously alongside eRTMAC. It reads current bit depth and formation, continuously compares the active well against the relevant offset depth corridor, and delivers an **Early Warning** with specific historical precedent before the bit penetrates the danger zone.

---

## 4. Phase 3: Post-Well Documentation & Knowledge Archiving

After reaching Total Depth (TD), running wireline logs, setting production casing, and testing the reservoir, the rig demobilizes.

```
[POST-WELL DOCUMENTATION TIMELINE: 30–90 DAYS POST-RIG]
Daily Tour Sheets & Mud Logging Logs Archived
       ↓
Geologist & Drilling Engineer Author the Well Completion Report (WCR)
       ↓
Post-Well Action Review (PWAR) Meeting Held (Key successes & failures discussed)
       ↓
Lessons Learned Documented (Usually as an appendix in the WCR PDF)
       ↓
PDF Uploaded to Network Share / Document Archive Server
       ↓
KNOWLEDGE BECOMES TRAPPED & FORGOTTEN (Institutional Amnesia)
```

### The Institutional Amnesia Problem:
- **The "PDF Black Hole":** Once a WCR is converted to a PDF and uploaded to a corporate server or archived as a paper binder, it ceases to be active intelligence. It becomes passive data.
- **Loss of Nuance:** DDR daily narratives contain rich, informal engineering observations (e.g. *"Noticed tight hole at 2,410 m while reaming; pipe surged when running back in"*). These critical micro-events are almost never transferred to the high-level executive summary of the WCR.
- **Staff Turnover:** In state-owned enterprises (PSUs) like OIL, engineers rotate fields every 3–5 years or retire. The tribal knowledge accumulated over a 35-year career walks out the door.
- **Where NWIS Intervenes:** NWIS ingests both WCRs and daily DDRs via OCR and NLP, decomposing long-form operational text into structured, indexed events linked to specific depth intervals and formations, preserving institutional memory indefinitely.

---

## 5. Detailed Breakdown: Where Friction Lives Today

The following operational friction matrix identifies the exact human points of failure in current workflows and maps them to NWIS solutions:

| Workflow Stage | Current Manual Activity | Operational Friction & Failure Mode | NWIS Solution |
| :--- | :--- | :--- | :--- |
| **Offset Selection** | Engineer manually scans field maps; selects nearest 3 wells by distance. | Ignores structural faults, dip, and stratigraphic pinch-outs; selects non-comparable wells. | Multi-dimensional relevance engine incorporating geology, formation tops, and trajectory similarity. |
| **Historical Retrieval** | Searching through scanned PDFs in file shares using basic keywords. | Scanned documents, OCR errors, non-standard naming conventions cause zero search results. | AI/OCR extraction pipeline + hybrid dense vector and keyword search over extracted facts. |
| **Risk Identification** | Reading hundreds of pages of daily narrative logs across 5 wells. | Cognitive overload; engineers miss subtle precursors mentioned on day 34 of a 90-day well. | Automated historical risk register highlighting loss zones, kicks, and stuck pipe incidents per interval. |
| **Real-Time Context** | Looking at live eRTMAC strip charts while consulting a paper drilling programme. | No dynamic link between what is happening on the rig floor and what happened historically. | Live sync with eRTMAC telemetry; real-time projection of historical risk corridors ahead of the bit. |
| **Mitigation Selection** | Engineer relies on personal habit (e.g. *"Whenever I see losses, I pump mica"*). | Sub-optimal or failed treatments; ignores proven solutions discovered in previous offset wells. | Contextual surfacing of historically successful mitigation measures with source document citations. |

---

## 6. The Target Integrated Workflow: eRTMAC + NWIS

The target future workflow operates as an augmented human-in-the-loop intelligence loop:

```
[LIVE RIG FLOOR]
Sensors (WOB, Torque, ROP, SPP, Flow, Pits)
       │
       ▼ (WITS / WITSML Telemetry)
[OIL eRTMAC 2.0 CLOUD PLATFORM]
Real-time monitoring, telemetry cleaning, live alarm triggers
       │
       │ (Active Well State: Bit Depth = 3,180 m, Formation = Barail Sand, Telemetry)
       ▼
[eRTMAC-NWIS PLATFORM]
├── 1. Dynamic Offset Selector: Ranks W-03, W-05, W-09 as key offsets.
├── 2. Stratigraphic Aligner: Correlates 3,180 m to 3,210–3,240 m in offsets.
├── 3. Historical Risk Engine: Detects 2 severe mud losses in this corridor.
├── 4. Anomaly Evaluator: Detects live torque fluctuation + ROP drilling break.
└── 5. Early Warning Generator:
       "CAUTION: Approaching loss zone in 20 m.
        Offset W-03 lost 25 m³/hr at this interval.
        Recommended action: Pre-treat active system with 30 kg/m³ LCM; limit ECD to 1.28 SG."
       │
       ▼ (Proactive Alert + Source Citations: W-03 DDR Day 41, Page 3)
[DRILLING ENGINEER / RIG SUPERINTENDENT]
Reviews evidence, verifies original report snippet, authorizes mud pre-treatment.
       │
       ▼
[SAFE WELL PENETRATION — ZERO NPT]
```

This workflow demonstrates that NWIS does not replace eRTMAC or human drillers; it equips both with instantaneous, contextual institutional memory.
