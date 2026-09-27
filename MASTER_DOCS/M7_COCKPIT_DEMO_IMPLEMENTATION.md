# eRTMAC-NWIS: Module 7 — Cockpit, Demo Script, Tech Stack and Jury Defense
# Master Document 5 of 6

> An AI reading this file can build Module 7 and execute the full demo.
> This covers: The unified drilling cockpit UI, the complete demo script,
> the full tech stack with exact libraries, and answers to every jury question.

---

## MODULE 7: Unified Drilling Command Cockpit

### 7.1 Cockpit Layout (Three-Panel Design)

The cockpit is a single-page browser application. Layout:

  +------------------+------------------------------------------+------------------+
  | LEFT PANEL       |         CENTER PANEL                     | RIGHT PANEL      |
  | (300px)          |         (flexible)                       | (320px)          |
  |                  |                                          |                  |
  | ACTIVE WELL      |     GEOSPATIAL MAP                       | ALERT FEED       |
  | STATUS           |     (full height, ~50% of center)        | (scrollable)     |
  |                  |                                          |                  |
  | Well: NHK-412    |  [Interactive Leaflet map]               | [RED] AMBER...   |
  | Depth: 3,215 m   |  - Well markers                          | [AMBER] Barail...|
  | TVDSS: 2,990 m   |  - Active radius ring                    | [BLUE] Entering..|
  | Formation:       |  - Fault polygons                        |                  |
  |  Barail Lower    |  - Omega-ranked offsets                  | KNOWLEDGE QUERY  |
  |                  |                                          |                  |
  | TELEMETRY        |     RISK CORRIDOR + LIVE CHART           | [Search box]     |
  | GAUGES           |     (~50% of center)                     | [Top results]    |
  |                  |                                          | [View Source]    |
  | ROP: 8.4 m/hr    |  [Depth track chart]                     |                  |
  | WOB: 89 kN       |  [LC risk band]                          | OFFSET RANKING   |
  | RPM: 85          |  [SP risk band]                          |                  |
  | TQA: 4.2 kNm     |  [Kick risk band]                        | #1 NHK-089  0.87|
  | SPP: 12,400 kPa  |  [Active bit marker moving down]         | #2 NHK-145  0.72|
  | Flow In: 1400    |                                          | #3 MOR-034  0.61|
  | Flow Out: 1285   |  REAL-TIME SENSOR CHART (last 30 min)   | #4 NHK-201  0.58|
  | Pit Vol: 342 m3  |  [Multi-line time series plot]           | #5 MOR-099  0.44|
  |                  |                                          |                  |
  | RIG STATE:       |                                          |                  |
  | ROTARY_DRILLING  |                                          |                  |
  +------------------+------------------------------------------+------------------+

### 7.2 The Live Telemetry Gauge Panel (Left Panel)

Each gauge uses a React component with color-coded bands:

  ROP Gauge:
    Green: 4-20 m/hr (normal drilling)
    Amber: 20-40 m/hr (fast — watch for formation change)
    Red: > 40 m/hr (drilling break — potential new formation entry)
    Red: < 1 m/hr for > 10 min while drilling (indication of packed off bit or tight hole)

  Flow Delta Gauge (MFIA - MFOA):
    Green: -100 to +100 L/min (normal)
    Amber: +100 to +200 L/min (partial loss) or -50 to -100 L/min (possible influx)
    Red: > +200 L/min (total loss) or < -100 L/min (kick indicator)

  Pit Volume Trend:
    Green: Stable (+/- 0.5 m3 over 10 min)
    Amber: Changing at +/- 0.5 to 2.0 m3 per 10 min
    Red: Changing at > 2.0 m3 per 10 min

### 7.3 The Risk Corridor Chart (Center Panel)

This is the centerpiece visual of the demo. A vertical chart:
  - Y-axis: Depth (current bit at bottom, projects up to current+200 m ahead)
  - X-axis: Risk score (0-10, aggregated from offset well history)
  - Three colored bands per depth:
      Orange band = Lost Circulation risk at that depth
      Brown band  = Stuck Pipe risk at that depth
      Red band    = Gas Kick risk at that depth
  - White dashed line = current bit depth (moves DOWN as bit advances in real time)
  - The chart is like a "weather forecast for the rocks ahead"

When the white line approaches an orange band -> AMBER LC alert fires simultaneously.
The judges can SEE the correlation: the chart predicts it, the alert fires when approached.

### 7.4 The Alert Feed (Right Panel)

Alerts are shown as cards in a scrollable feed, newest at top:
  Tier 1 RED card: Full-width red background, white bold text, audio chime, action checklist.
  Tier 2 AMBER card: Amber background, action steps, 3 collapsible evidence cards with DDR links.
  Tier 3 BLUE card: Blue card, formation info, proactive checklist.

Each AMBER/BLUE card has an "Evidence" section showing:
  - Which offset wells triggered this
  - The exact DDR date and page
  - A "View in PDF" button that opens the source document

### 7.5 The PDF Proof Viewer

When "View in PDF" is clicked:
  - An overlay panel slides in from the right (or a modal opens).
  - It shows the scanned DDR page (rendered as PNG by PyMuPDF on the backend).
  - A semi-transparent yellow rectangle is drawn over the exact text that is the evidence.
  - Below the image, the extracted text is shown verbatim.
  - The page number, well name, and report date are shown in the header.

This is the "1-click bounding box proof" that SIH judges specifically look for.

---

## Demo Script (8-Minute SIH Presentation)

### Scene 0 — 30 seconds: Opening Statement

"This is NWIS — the Nearby Wells Intelligence System for OIL eRTMAC.
OIL has drilled 3,000 wells in Upper Assam over 60 years. That institutional knowledge
sits in filing cabinets and uncategorized PDFs. When a drill string gets stuck at 3,200 m
in Barail Coal-Shale, the engineer has no quick way to know that this exact zone stuck
three strings in nearby wells last decade — and that each was freed with a diesel spotting pill.
NWIS makes that knowledge available in real time, before the incident happens."

### Scene 1 — 1 minute: The OCR Ingestion Proof

"We feed the system a scanned DDR PDF — exactly like what OIL has in its archives."
[DRAG AND DROP a DDR PDF into the ingestion panel.]
"The system extracts: well name, bit depth, mud properties, NPT event type and duration,
and the mitigation text — all with bounding box coordinates tracking the source."
[SHOW: The extracted fields appear in a structured card. Click 'View Source' -> PDF opens
with yellow highlight on the extracted text.]
"Every fact we show you is provable — one click to the exact line in the original document."

### Scene 2 — 1.5 minutes: The Map and Offset Ranking

"This is the geospatial cockpit. [POINT TO MAP] 15 wells in the Nahorkatiya-Moran area.
The pulsing green marker is our active well NHK-412, currently at 2,990 m TVDSS —
that is 3,215 m measured depth, but we convert to subsea to compare apples to apples.
The five blue markers are the top-ranked offset wells — ranked not just by distance,
but by our Omega score that weights geological match, trajectory similarity, and NPT history."

[ADVANCE DEPTH by 200 m using the simulator controls.]
"Watch the ranking list as the bit drills from Barail Lower Sand into Barail Coal-Shale."
[PAUSE — list reorders. MOR-034 rises from #3 to #1.]
"MOR-034 just jumped to number one. Why? Because it has 3 documented stuck pipe events
in the Barail Coal-Shale — which we are now approaching. The system sees the geology,
not just the map. A well 8 km away with relevant history outranks a well 2 km away
with no Coal-Shale history."

### Scene 3 — 1.5 minutes: The Geological Correlation (Module 4 Demo)

"How do we know NHK-089 at 3,228 m TVDSS is the same geological level as our well
at 2,990 m TVDSS? They are 238 m apart in absolute depth!"
[SHOW the xi calculation panel.]
"Both wells are at xi = 0.44 — 44% into the Barail Lower Sand formation.
NHK-089 has a thicker Barail section due to its structural position on the flank.
The xi ratio normalizes for this. A raw MD comparison would have missed this event completely."
[CLICK on the highlighted event from NHK-089.]
"This opens the source DDR from 2015. Page 2, line 18. Yellow highlight.
45 barrels per hour lost circulation. 30-barrel nut plug cured it in 2 hours."

### Scene 4 — 1.5 minutes: Ahead-of-Bit Alert Fires

[ADVANCE DEPTH to 30 m before the Barail Coal top.]
[BLUE alert fires in the right panel.]
"BLUE alert — proactive intelligence — we are 32 m away from the Barail Coal-Shale.
This alert fired based purely on historical evidence from 3 offset wells.
No sensor anomaly yet. The telemetry is perfectly normal."
[SHOW: Alert card expanded. Three DDR links. Pre-prepared pill recommendation visible.]

[ADVANCE DEPTH 10 more meters — into the Coal-Shale.]
[Simulator introduces a torque trend anomaly.]
[AMBER alert fires: "Pre-stuck indicators — Increasing torque, recommend string reciprocation."]
"The AMBER alert fires as telemetry confirms what history predicted.
Now we have BOTH signals: 3 offset wells said this zone sticks, AND torque trend says it is starting.
The engineer had 25 minutes of lead time to prepare the diesel spotting pill."

### Scene 5 — 1 minute: Knowledge Query

"The engineer types: What mitigation worked best for stuck pipe in Barail Coal?"
[TYPE query. Hit enter. 3-second wait. Results appear.]
"Three DDR passages, ranked by relevance. Each with a confidence score.
The answer synthesized from these passages: diesel spotting pill, 25-35 bbl, spotted at bit.
Click source: [CLICK] — PDF opens, line highlighted."
"No hallucination. Every number traces to a real document."

### Scene 6 — 1 minute: Architecture and Data Provenance

"[SHOW architecture diagram]
Air-gapped FastAPI backend. PostgreSQL with PostGIS and pgvector extensions.
Local LLaMA 3.1 8B via Ollama — no external API calls.
WITSML telemetry replay via WebSocket.
Zero cloud dependency. Deployable on-premise at eRTMAC Duliajan."

"Geological formation parameters sourced from USGS Bulletin 2208-D (Wandrey, 2004) —
public domain, peer-reviewed, specifically covering the Assam Geologic Province.
Telemetry structure from Equinor Volve dataset, CC BY 4.0 licensed.
Synthetic well records generated from USGS formation distributions — clearly labelled
as synthetic in every record."

### Scene 7 — 1 minute: Closing ROI Statement

"OIL drills approximately 40-60 wells per year in Upper Assam. Industry data shows
stuck pipe and lost circulation cause 10-15% of NPT — roughly 3-5 incidents per year
that require fishing, sidetracks, or major remediation.
Each incident costs Rs 15-40 lakh in rig time alone.
Conservative estimate: NWIS prevents or reduces 4 incidents per year.
Savings: Rs 6-16 crore annually. NWIS pays for itself in the first month of deployment.
And it never forgets a lesson from a previous well."

---

## Tech Stack: Complete Production Specification

### Backend

  Language:     Python 3.11+
  Framework:    FastAPI (async, high performance, auto-docs via OpenAPI)
  Database:     PostgreSQL 15 + PostGIS 3.3 + pgvector 0.5
  ORM:          SQLAlchemy 2.0 (async)
  WebSocket:    FastAPI WebSocket (built-in)
  Task Queue:   Celery + Redis (for background OCR processing)

  Key Libraries:
    pymupdf (fitz) — PDF rendering and text extraction
    pytesseract — Tesseract OCR for scanned pages
    sentence-transformers — embedding generation
    wellborepath — minimum curvature TVDSS calculation
    numpy, scipy, pandas — numerical processing
    watchdog — file system monitoring for drop folder
    ollama — local LLM inference API client

### Frontend

  Framework:    React 18 + TypeScript
  Mapping:      Leaflet.js + react-leaflet
  Charts:       Recharts (for telemetry time-series) + D3.js (for risk corridor)
  State:        Zustand (lightweight, no Redux boilerplate)
  WebSocket:    native browser WebSocket API
  PDF Viewer:   pdf.js (Mozilla, runs in browser, no server needed for display)
  UI Library:   Radix UI primitives + custom CSS (no Tailwind dependency for air-gap compliance)

### Infrastructure

  Deployment:   Single Docker Compose file (all services)
  Services:     postgres, redis, celery_worker, fastapi, react (nginx)
  Network:      Bridge network (no external calls)
  Volumes:      /data/documents (PDF storage), /data/mbtiles (offline map tiles)

  Minimum Hardware for eRTMAC Deployment:
    CPU: Intel Xeon 8-core (2018 or newer)
    RAM: 32 GB (16 GB minimum, but Ollama needs headroom)
    Storage: 500 GB SSD (PDF corpus + database + models)
    GPU: Optional (NVIDIA RTX 3060 12GB recommended for faster Ollama inference)
    Network: Local LAN only — NO internet connection required

### API Endpoints Summary

  GET  /ws/telemetry/{well_id}        — WebSocket for 1-Hz sensor stream
  POST /api/ingest/document           — Upload PDF for OCR processing
  GET  /api/wells                     — List all wells with Omega scores at current depth
  GET  /api/wells/{id}/formation_tops — Formation tops for a specific well
  GET  /api/correlation/xi            — Xi calculation for active depth
  GET  /api/correlation/risk_corridor — Risk projection ahead of current depth
  GET  /api/offset_ranking            — Current Omega-ranked offset list
  POST /api/knowledge/query           — RAG knowledge search
  GET  /api/alerts/active             — Current active alert list
  GET  /api/docs/{doc_id}/render/{page} — PDF page renderer with bbox highlight
  GET  /api/telemetry/history/{well_id} — Historical telemetry (last 2 hours)
  GET  /health                        — System health check (all services)

---

## Jury Q&A Defense Sheet

Q: "Is this real OIL data?"
A: "Formation parameters are from USGS Bulletin 2208-D — peer-reviewed public domain source
   covering the Assam Geologic Province. Telemetry structure uses Equinor Volve, CC BY 4.0.
   Numerical values are synthetic but calibrated to USGS formation distributions. We explicitly
   label all synthetic records as such. The pipeline is designed for real OIL data — connecting
   it to the NDR or eRTMAC WITSML feed would require only configuration changes, not re-architecture."

Q: "How is your xi ratio better than just using TVDSS?"
A: "TVDSS corrects for directional survey effects, but not for structural dip. The same Barail
   Lower Sand formation is at 2,940 m TVDSS in NHK-412 and at 3,180 m TVDSS in NHK-089 —
   because NHK-089 is on the structural flank. A raw TVDSS comparison would miss their connection.
   Xi normalizes for formation thickness and position, so 0.44 in any well means the same
   geological position relative to the formation boundaries — regardless of absolute depth."

Q: "What if the formation tops are wrong or estimated?"
A: "Every formation top has a confidence flag: HIGH (from verified WCR), LOW (from OCR below 85%
   confidence), or INFERRED (statistical imputation from neighbors). Low and inferred tops trigger
   a visible warning in the UI: 'Stratigraphic correlation uncertainty HIGH.' The engineer sees
   exactly what data quality supports the recommendation."

Q: "Why not use GPT-4 or Claude? It is much more capable."
A: "OIL eRTMAC is air-gapped. DGH NDR data cannot leave the OIL network under any circumstances.
   Sending drilling data to OpenAI or Anthropic APIs would violate DGH NDR data sovereignty
   regulations. We use Ollama with a locally-hosted LLaMA 3.1 8B model — comparable capability
   for structured drilling text, zero data exfiltration risk."

Q: "How do you prevent false alarms?"
A: "Three mechanisms: First, rig-state FSM — alarms are suppressed during states where the sensor
   signal is meaningless (e.g., no LC alarm when pumps are off). Second, sustained-condition
   triggers — a 1-second spike does not fire an alarm; requires sustained anomaly for 30-90 seconds.
   Third, formation context thresholds — Lost Circulation sensitivity increases inside Tipam
   Sandstone and decreases in tight shale where natural loss is impossible."

Q: "Your 70% NPT event prediction recall — is that realistic?"
A: "In the Volve benchmark study (Volve Bench, 2024), stuck pipe early warning systems achieved
   60-75% recall at 20-60 minute lead times on well-labelled datasets. Our 70% target is
   consistent with published benchmarks. We also report Precision and False Alarm Rate explicitly —
   not just recall — because an alarm that cries wolf 10 times per shift is worse than no alarm."

Q: "What happens when there are no offset wells nearby?"
A: "The system degrades gracefully. If no offset wells are found within 50 km with the same
   formation data, the Omega rank list is empty and the risk corridor defaults to regional
   statistics (USGS formation hazard classification by formation name). The engineer sees:
   'LIMITED OFFSET DATA — risk corridor based on regional formation statistics only.
   Treat with high caution. Recommend manual DDR review before entering this zone.'"


---
---
## SECTION 8: UPDATED COCKPIT LAYOUT (Post-Geomine Analysis)

After analyzing the Geomine demo, the cockpit needs to be expanded.
The revised 5-panel layout:

+------------------+------------------------------+------------------+
|  LEFT PANEL      |     CENTER TOP               |  RIGHT PANEL     |
|  ACTIVE WELL     |     GEOSPATIAL MAP           |  ALERT FEED      |
|  STATUS +        |     (Leaflet)                |  + KNOWLEDGE     |
|  TELEMETRY       |                              |  QUERY           |
|  GAUGES          |                              |                  |
+------------------+------------------------------+------------------+
|                  |  CENTER BOTTOM (tabs):       |                  |
|                  |  [RISK CORRIDOR][MUD WINDOW] |                  |
|                  |  [WELL CORRELATION PANEL]    |                  |
|                  |  [OFFSET TRENDS][COST METER] |                  |
+------------------+------------------------------+------------------+
                   |  BOTTOM STRIP: TELEMETRY TIME SERIES (last 60 min)
                   +----------------------------------------------+

TAB DETAILS for center bottom:

TAB 1 — RISK CORRIDOR:
  Vertical depth track. Three risk bands (LC, SP, Kick). Moving bit marker.
  Evidence count labels on each band.

TAB 2 — MUD WINDOW:
  PP gradient line, FG line, current mud weight line.
  Offset well mud weight dots at xi-equivalent depths.
  Red/orange triangles for historical NPT events at those depths.

TAB 3 — WELL CORRELATION PANEL (THE KILLER FEATURE):
  Multi-well lithology stick plot with xi-normalized depth alignment.
  Orange horizontal correlation line showing current geological horizon across all wells.
  NPT event markers on each well column.
  Formation color legend.

TAB 4 — OFFSET TRENDS AND ANALYTICS:
  Aggregated statistics across top-5 Omega-ranked offset wells:
    - Average ROP by formation (bar chart)
    - NPT frequency by formation (pie/donut chart)
    - Mud weight range actually used per formation (box plot)
    - Historical stuck pipe duration distribution (histogram)
  
  This helps engineers see PATTERNS, not just individual events.
  "In Barail Coal, 4/5 offset wells had stuck pipe events. Average duration: 18 hours.
   All were freed with diesel spotting pill. None required sidetrack."

TAB 5 — COST METER:
  NPT cost calculator (see M4 Section 12).
  Running cost clock for current event.
  Session total: NPT hours, estimated cost, NWIS-attributed savings.

---
---
## SECTION 9: THE 10-MINUTE EXTENDED DEMO SCRIPT

Extended script that covers Geomine's features AND our differentiators.
Use this when given more time (SIH finals / extended Q&A).

### Scene 0 — 30 sec: Hook
"OIL loses Rs 15-25 crore per year to preventable NPT in Upper Assam.
Geomine addresses this. So do we. Here is what we do differently."

### Scene 1 — 1 min: OCR Ingestion
"[Drag DDR PDF] System extracts all fields. Watch: we stored the bounding box of every fact.
[Click 'View Source'] The original 1995 DDR page opens. Yellow highlight. Exact sentence.
Not an AI paraphrase. The ORIGINAL DOCUMENT. This matters when a Rs 50 crore mud program
is on the line."

### Scene 2 — 1 min: Map + Omega Ranking
"[Point to map] 15 wells. Omega score. Watch what happens as we drill deeper.
[Advance depth 400 m into Barail Coal]
[List reorders — MOR-034 rises to #1]
MOR-034 jumped. It has 3 Barail Coal stuck pipe events. The other systems use raw depth.
We use the xi ratio — geologically normalized depth. THAT is why MOR-034 ranked up.
It is geologically the most relevant, even though NHK-089 is physically closer."

### Scene 3 — 1 min: The Well Correlation Panel
"[Switch to TAB 3 — Well Correlation Panel]
This is how subsurface geologists actually think. Each column is an offset well.
Each formation is a color. The orange line — that is our current drilling depth,
xi-normalized across ALL wells simultaneously.
[Move the orange line DOWN] Watch every column's line move — but NOT at the same absolute depth.
MOR-034 is 238 m LOWER for the same orange line position. Because it is on the structural flank.
This is the xi ratio in visual form. Geomine's depth corridor would have compared the wrong horizon."

### Scene 4 — 1 min: Mud Window
"[Switch to TAB 2 — Mud Window]
Blue dots: actual mud weights from offset wells at this xi position in Tipam Sandstone.
Orange triangle at 1.36 g/cc: that is where NHK-089 had lost circulation in 2015.
Our current mud weight: 1.32 g/cc. We are 0.04 g/cc below that historical failure point.
[Advance depth slightly — orange triangle approaches current mud weight line]
AMBER alert: 'Approaching fracture gradient from offset well evidence.'
This fired from HISTORY — before any sensor anomaly. Geomine fires AFTER the sensor drops."

### Scene 5 — 1 min: Physics-Based Stick-Slip
"[Switch to live telemetry tab]
[Simulate a slow torque oscillation — stick-slip building]
Our physics engine: the drill string torsional model says stick-slip severity is now 0.62.
It calculates based on string length, pipe dimensions, formation friction coefficients.
In Barail Coal-Shale the static-to-dynamic friction ratio is 3.3:1 — the HIGHEST of any Assam formation.
When the bit releases, it will overspeed to approximately 2.1x surface RPM for 0.8 seconds.
[AMBER fires: 'Moderate stick-slip — reduce RPM by 12 rpm']
[Reduce RPM in simulator — physics engine shows severity dropping to 0.31]
Resolved in 15 seconds. No string fatigue. No NPT."

### Scene 6 — 1 min: Anti-Collision Monitor
"[Switch to anti-collision panel]
Three surrounding wells shown in 3D. SAFD values displayed.
NHK-410: SAFD 2.8 — SAFE.
NHK-395: SAFD 1.9 — safe but monitoring.
Watch as we drill 100 m deeper: [ADVANCE] SAFD to NHK-395 drops to 1.3 — AMBER.
System recommends azimuth correction of 8 degrees. Engineer clicks ACKNOWLEDGE — logs the action.
This is drilling safety, not just productivity."

### Scene 7 — 1 min: Engineer Decision Workflow + Cost
"[RED alert fires — simulated stuck pipe]
Three buttons: Acknowledge, Override, Escalate.
[Click ACKNOWLEDGE] System logs who, when, what action.
[NPT cost meter starts] Rs 82,000 per hour. 14 minutes elapsed: Rs 19,133 accumulated.
[Implement spotting pill recommendation from knowledge base — sourced from offset DDR]
[After 45 min simulation — flow metrics return to normal]
System logs OUTCOME: EFFECTIVE. This will weight the diesel spotting pill recommendation
MORE strongly next time a similar event occurs in this formation."

### Scene 8 — 1 min: Knowledge Query
"[Type: What LCM treatments worked in Tipam Sandstone in Nahorkatiya?]
[Results: 3 DDR passages + synthesized answer]
'30-35 bbl medium nut plug + calcium carbonate at 40 ppb. Pumped at 1200 lpm reduced rate.'
[Click 'View Source'] DDR page opens. Yellow highlight on exact paragraph.
The LLM runs locally on Ollama — no data leaves this network. Zero cloud dependency."

### Scene 9 — 30 sec: Architecture Close
"Air-gapped FastAPI. PostgreSQL + PostGIS + pgvector. Ollama local LLM.
Offline Leaflet maps. One Docker Compose file. Deploys in 20 minutes on an eRTMAC server.
No SaaS subscription. No cloud fees. No data sovereignty risk.
NWIS is the only system in this room that can be deployed on OIL's actual eRTMAC network."

---
---
## SECTION 10: WHAT MAKES NWIS STRUCTURALLY BETTER THAN GEOMINE

Summary table for jury handout or slide:

Feature                     | Geomine          | NWIS
----------------------------|------------------|-----------------------------------------------------
Depth comparison            | Raw MD buffer    | TVDSS + Xi ratio (geologically correct)
Offset search radius        | Single fixed buffer | Formation-aware (50km Tipam, 10km Kopili)
Fault block awareness       | Not mentioned    | PostGIS polygon containment (cross-fault excluded)
Ahead-of-bit prediction     | No               | Xi projection 200m ahead + risk corridor
Historical evidence depth   | Depth proximity  | Stratigraphically normalized (same xi position)
PDF bounding box proof      | Not shown        | 1-click highlight on exact sentence
Mud window data source      | Unclear          | Extracted from offset DDRs via OCR (auto-updated)
Stick-slip physics          | Physics engine   | Formation-SPECIFIC friction coefficients for Assam
Engineer decision tracking  | Approve/Reject   | Approve/Override/Escalate + outcome monitoring
Recommendation learning     | Not mentioned    | Outcome tracking improves future recommendations
Data sovereignty            | Unclear          | Provably air-gapped (no external API calls in demo)
Geological data source      | Unclear          | USGS Bulletin 2208-D (cited, public domain)
LLM                         | Unclear          | Ollama + LLaMA 3.1 8B (local, no OpenAI API)
Well correlation panel      | Radar chart      | Full lithology stick plot with xi-normalized horizon
NPT cost calculator         | Yes              | Yes + outcome tracking feeds savings counter
Anti-collision              | Yes              | Yes + SAFD with uncertainty ellipse method
Formation-aware thresholds  | Fixed thresholds | Thresholds CHANGE per formation (xi-triggered)
