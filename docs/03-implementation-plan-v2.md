# Implementation Plan v2.0 (UPDATED)
## eRTMAC-NWIS - 7 Production Modules Architecture

**Document Version:** 2.0  
**Last Updated:** September 27, 2026  
**Status:** Active - Team Aligned Architecture  
**Previous Version:** `03-implementation-plan.md` (10 modules - deprecated)

---

## 🎯 Key Changes from v1.0

### What Changed:
- ✅ **Simplified from 10 technical modules → 7 outcome-driven production modules**
- ✅ **Direct 1:1 mapping to Problem Statement's 7 Expected Outcomes**
- ✅ **Clearer team coordination** (each module = one deliverable = one outcome)
- ✅ **Better alignment with judging criteria** (outcome-focused vs. technical-focused)

### What Stayed the Same:
- ✅ Technology stack (React, FastAPI, PostgreSQL, Ollama)
- ✅ Air-gapped on-premise deployment
- ✅ Open-source first approach
- ✅ Human-in-the-loop philosophy

---

## 1. System Architecture Overview

### 1.1 7 Production Modules = 7 Expected Outcomes

```
┌─────────────────────────────────────────────────────────────────────┐
│     Module 7: Unified Drilling Command Cockpit (Frontend)           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Left: Interactive GIS Map (Module 2 Integration)           │    │
│  │  Middle: Stratigraphic Depth Track (Module 4 Integration)   │    │
│  │  Right: Live Risk Gauges (Module 5 Integration)             │    │
│  │  Top: Real-Time Alert Banner (Module 6 Integration)         │    │
│  │  Bottom: AI Copilot + PDF Evidence (Module 3 Integration)   │    │
│  └────────────────────────────────────────────────────────────┘    │
│  PS Outcome vii: "User-friendly dashboard for field & office"      │
└─────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌─────────────────────────────────────────────────────────────────────┐
│    Module 6: Real-Time Alerts & Proactive Recommendations          │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Lookahead warning system (15-50m before hazard)          │    │
│  │  • Amber alerts with 30-60 min preparation lead time        │    │
│  │  • Actionable recommendations (e.g., "Pre-mix LCM slug")    │    │
│  │  • Alert states: Green (safe) → Amber (approaching) → Red   │    │
│  └────────────────────────────────────────────────────────────┘    │
│  PS Outcome vi: "Real-time alerts for proactive decisions"         │
└─────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌─────────────────────────────────────────────────────────────────────┐
│         Module 5: Predictive Drilling Risk Analytics                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  5 Specialized Hazard Models:                               │    │
│  │  1. Lost Circulation Risk (flow-out vs flow-in analysis)    │    │
│  │  2. Stuck Pipe Risk (overpull trends + MSE analysis)        │    │
│  │  3. Kick/Overpressure Risk (ROP breaks + pit gains)         │    │
│  │  4. Torque & Drag Dysfunction (stick-slip analysis)         │    │
│  │  5. Cementing Integrity Risk (offset CBL failure history)   │    │
│  │                                                              │    │
│  │  4-Pillar Confidence Framework:                             │    │
│  │  • Evidence Strength (N=X offset wells)                     │    │
│  │  • Live Anomaly Status (real-time deviation %)              │    │
│  │  • Data Quality Score (completeness + reliability)          │    │
│  │  • Source Grounded (100% traceable to PDF)                  │    │
│  └────────────────────────────────────────────────────────────┘    │
│  PS Outcome v: "Predictive analytics for drilling risks"           │
└─────────────────────────────────────────────────────────────────────┘
                                ▲
                ┌───────────────┴───────────────┐
                │                               │
┌───────────────▼─────────────────┐ ┌──────────▼───────────────────────┐
│ Module 4: Geological, Drilling  │ │ Module 3: Drilling Knowledge     │
│ & Reservoir Correlation         │ │ & Lessons-Learned Repository     │
├─────────────────────────────────┤ ├──────────────────────────────────┤
│ • MD → TVDSS conversion         │ │ • Natural language search engine │
│ • Horizon alignment across wells│ │ • Analog case retrieval          │
│ • Geological continuity mapping │ │ • Historical NPT + mitigations   │
│ • Dual stratigraphic view       │ │ • 1-click PDF evidence viewer    │
│ • Active well vs offset sync    │ │ • Institutional memory platform  │
│                                 │ │                                  │
│ PS Outcome iv: "Correlate data  │ │ PS Outcome iii: "Searchable      │
│ across wells by depth/formation"│ │ knowledge repository"            │
└─────────────────────────────────┘ └──────────────────────────────────┘
                ▲                               ▲
                │               ┌───────────────┘
                │               │
┌───────────────▼───────────────▼─────────────────────────────────────┐
│       Module 2: Geospatial Offset Well Intelligence                 │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Interactive GIS map (dark mode for control rooms)        │    │
│  │  • Dynamic radius slider (5-50 km user-defined)             │    │
│  │  • Active well (pulsing green marker)                       │    │
│  │  • Offset wells (color-coded by geological relevance)       │    │
│  │  • Fault-block awareness ("Nearby ≠ Relevant")              │    │
│  │  • Formation continuity highlighting                        │    │
│  └────────────────────────────────────────────────────────────┘    │
│  PS Outcome ii: "Interactive map-based visualization"               │
└─────────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│   Module 1: Historical Data Extraction & Structuring                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  • Background OCR + NLP ingestion worker                    │    │
│  │  • Extract: Formation tops, casing shoes, mud properties    │    │
│  │  • Extract: Operational incidents + NPT hours               │    │
│  │  • WITSML-compliant structured output                       │    │
│  │  • Eliminates weeks of manual data entry                    │    │
│  └────────────────────────────────────────────────────────────┘    │
│  PS Outcome i: "AI/NLP/OCR to extract and structure data"          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Breakdown (7 Production Modules)

### Module 1: Historical Data Extraction & Structuring

**PS Outcome i:** "Use AI, NLP, OCR, and data analytics to automatically extract and structure information from historical drilling reports and well documents."

**What It Does:**
- Ingests scanned DDRs, WCRs, and historical documents
- Extracts structured data: formation tops, casing, mud properties, incidents, NPT
- Outputs WITSML-compliant records to database
- Background processing (doesn't block user workflow)

**Key Features:**
- OCR with PaddleOCR (handles poor-quality scans)
- NLP entity extraction with spaCy (domain-tuned for drilling)
- Layout-aware parsing (tables, multi-column text)
- Confidence scoring for extracted data

**Technology:**
- **OCR:** PaddleOCR (multilingual, handles handwriting)
- **NLP:** spaCy + custom drilling entity recognizer
- **Parser:** pdf2image + custom layout analyzer
- **Queue:** Background worker with Celery (optional) or async tasks

**Inputs:** PDF files (DDRs, WCRs, mud reports)
**Outputs:** Structured JSON → PostgreSQL database

**Success Criteria:**
- Extract well name: >98% accuracy
- Extract depth values: >95% accuracy
- Extract incidents: >90% recall
- Overall extraction: >94% accuracy (validated against WITSML ground truth)

---

### Module 2: Geospatial Offset Well Intelligence

**PS Outcome ii:** "Provide an interactive map-based visualization of nearby wells within a user-defined radius."

**What It Does:**
- Interactive GIS map showing active well + offset wells
- User-defined radius slider (5-50 km)
- Geological relevance scoring (not just physical distance)
- Color-coded wells by geological context

**Key Features:**
- Active well: Pulsing green marker (real-time position)
- Offset wells: Color-coded by relevance (blue = relevant, gray = different fault block)
- Fault-block awareness: Wells across sealing faults are grayed out
- Formation continuity: Highlights wells along same sand strike
- Click well → Show summary popup (depth, incidents, NPT)

**Technology:**
- **Frontend:** React Leaflet (offline map tiles)
- **Backend:** PostGIS (spatial queries)
- **Relevance Engine:** Multi-factor scoring:
  - Physical distance (haversine formula)
  - Geological similarity (formation overlap %)
  - Fault-block matching (shared structural domain)
  - Directional drilling similarity (inclination/azimuth)

**Inputs:** Well locations (lat/lng), geological models
**Outputs:** Ranked list of offset wells with relevance scores

**Success Criteria:**
- Map loads in <2 seconds
- Radius filter updates in <500ms
- Top 3 offset wells align with geologist's expert ranking

---

### Module 3: Drilling Knowledge & Lessons-Learned Repository

**PS Outcome iii:** "Create a searchable knowledge repository of drilling events, lessons learned, operational challenges, and mitigation measures."

**What It Does:**
- Searchable institutional memory platform
- Natural language queries (e.g., "lost circulation in Tipam Sandstone")
- Returns analog cases with root causes, NPT, and proven mitigations
- 1-click PDF evidence viewer (highlights exact paragraph)

**Key Features:**
- Google-like search bar for drilling engineers
- Hybrid search: BM25 (keyword) + Vector (semantic)
- Result cards show: Case summary, NPT hours, mitigation recipe, success rate
- PDF viewer: Opens original document with yellow highlight on evidence
- Filter by: Formation, depth range, incident type, date range

**Technology:**
- **Search:** BM25 (rank_bm25 library) + pgvector (semantic)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384-dim)
- **Chunking:** Sliding window (500 words, 100-word overlap)
- **Reranking:** Cross-encoder for top-k refinement

**Inputs:** Extracted incident records from Module 1
**Outputs:** Ranked list of analog cases + PDF links

**Success Criteria:**
- Query response time: <2 seconds
- Top-3 precision: >85% (validated by SMEs)
- PDF highlighting: 100% accuracy (exact paragraph match)

---

### Module 4: Geological, Drilling & Reservoir Correlation

**PS Outcome iv:** "Correlate geological, drilling, and reservoir data across wells based on depth and formation."

**What It Does:**
- Converts MD (Measured Depth) → TVDSS (True Vertical Depth Subsea)
- Aligns formation horizons across active and offset wells
- Displays dual stratigraphic depth track (active vs. offset)
- Automatic geological correlation

**Key Features:**
- Side-by-side geological columns (active well + top 3 offsets)
- Horizon alignment: Auto-matches formations (Tipam ↔ Tipam)
- Handles deviated wells: Converts inclined well to TVDSS for apples-to-apples comparison
- Incident markers: Plots historical events at correct geological horizon
- Depth corridor: Shows active bit advancing toward past incident zones

**Technology:**
- **Conversion:** MD → TVDSS using survey data (inclination, azimuth)
- **Horizon Matching:** Formation name + depth-range matching
- **Visualization:** D3.js or Plotly for stratigraphic columns

**Inputs:** Survey data (MD, inc, azi), formation tops (MD, TVDSS)
**Outputs:** Aligned stratigraphic view with incident markers

**Success Criteria:**
- TVDSS conversion accuracy: <1% error
- Horizon alignment: >90% automatic match rate
- Visual rendering: <1 second update on depth change

---

### Module 5: Predictive Drilling Risk Analytics

**PS Outcome v:** "Develop predictive analytics models that can identify potential drilling risks such as mud losses, stuck pipe, overpressure zones, torque spikes, or cementing issues based on historical offset-well behaviour."

**What It Does:**
- Continuously assesses 5 core drilling hazards using live data + offset history
- Risk outputs with 4-pillar confidence framework (no black-box "85% Risk")
- Specialized model for each hazard (not generic model)

**5 Specialized Hazard Models:**

1. **Lost Circulation Risk**
   - Monitors: Flow-out vs. flow-in delta (ΔQ), SPP trends, offset loss zones
   - Triggers: ΔQ > 10% sustained, approaching offset loss depth ±15m

2. **Stuck Pipe Risk**
   - Monitors: Overpull trends, MSE (Mechanical Specific Energy), torque fluctuations
   - Triggers: Overpull >20% WOB, MSE >2x baseline, approaching offset stuck depth

3. **Kick / Overpressure Risk**
   - Monitors: ROP drilling breaks, pit volume gains, d-exponent trends
   - Triggers: ROP increases >50%, pit gain >0.5 bbl, d-exp drops

4. **Torque & Drag Dysfunction**
   - Monitors: Stick-slip torsional resonance, hookload oscillations
   - Triggers: Torque variance >30%, stick-slip frequency detected

5. **Cementing Integrity Risk**
   - Monitors: Offset CBL (cement bond log) failure history in this formation
   - Triggers: Approaching depth with >50% historical CBL failure rate

**4-Pillar Confidence Framework:**
Instead of fake "85% risk" number, display:
- **Evidence Strength:** N=3 offset wells (High/Medium/Low)
- **Live Anomaly Status:** ΔQ = -12% (Mild/Moderate/Severe)
- **Data Quality:** 96% (sensor reliability + completeness)
- **Source Grounded:** 100% (traceable to PDF page 34, line 18)

**Technology:**
- **Models:** scikit-learn (RandomForest, XGBoost) per hazard
- **Features:** Engineered from drilling parameters (ROP, WOB, RPM, SPP, etc.)
- **Training:** Supervised learning on labeled historical incidents
- **Inference:** Real-time scoring on 1-minute intervals

**Inputs:** Live drilling parameters (WITSML), offset incident history
**Outputs:** Risk scores (0-100) per hazard + confidence pillars

**Success Criteria:**
- Incident recall: >85% (detects 85% of actual incidents)
- False positive rate: <15% (avoids alert fatigue)
- Lead time: 30-60 minutes before incident occurs

---

### Module 6: Real-Time Alerts & Proactive Recommendations

**PS Outcome vi:** "Generate real-time alerts and recommendations to assist drilling engineers in proactive decision-making."

**What It Does:**
- Lookahead warning system (alerts 15-50m before hazard zone)
- Actionable recommendations (not just "high risk")
- 30-60 minute preparation lead time
- 3-state alert system: Green (safe) → Amber (approaching) → Red (imminent)

**Alert States:**

1. **Green (Safe):** >50m from hazard
   - Banner: "All Clear - Next formation in 120 meters"
   - No action required

2. **Amber (Proactive Warning):** 15-50m from hazard
   - Banner: "⚠️ PROACTIVE HAZARD WARNING: 18 meters ahead to Historical Loss Zone!"
   - Details:
     ```
     Expected Interval: 3,238 m – 3,255 m (Tipam Sandstone)
     Recommended Action: Pre-mix 25 bbl Medium LCM slug in pit #2; notify mud engineer.
     Evidence: Well Moran-B2 lost 40 bbl at 3,242 m (source: DDR pg 12)
     ```
   - Audible chime
   - Gives crew 30-60 min to prepare

3. **Red (Imminent):** <15m from hazard OR live anomaly detected
   - Banner: "🚨 CRITICAL: Entering Historical Loss Zone - Monitor Returns Closely"
   - Continuous monitoring mode

**Technology:**
- **Alert Engine:** Python background worker
- **Thresholds:** Configurable per hazard type
- **Delivery:** WebSocket → Frontend banner + optional SMS/email

**Inputs:** Current depth, risk scores from Module 5, offset incident depths
**Outputs:** Real-time alerts with recommendations

**Success Criteria:**
- Lookahead accuracy: >90% (alerts issued before hazard zone entry)
- Lead time: 30-60 minutes average
- Actionability: 100% (every alert includes specific action steps)

---

### Module 7: Unified Drilling Command Cockpit

**PS Outcome vii:** "Present information through a user-friendly dashboard for field and office-based personnel."

**What It Does:**
- Single-pane unified dashboard (no switching between 5 different programs)
- Dark mode optimized for 24/7 control rooms
- Integrates all 6 modules into one coherent interface

**5-Panel Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│                   TOP: Real-Time Alert Banner                   │
│  🚨 AMBER: 18m ahead to Loss Zone - Pre-mix LCM slug           │
└────────────────────────────────────────────────────────────────┘
┌─────────────────────┬──────────────────────┬──────────────────┐
│     LEFT PANEL      │    MIDDLE PANEL      │   RIGHT PANEL    │
│  Interactive GIS    │  Stratigraphic       │  Live Risk       │
│  Map (Module 2)     │  Depth Track         │  Gauges          │
│                     │  (Module 4)          │  (Module 5)      │
│  • Active well      │                      │                  │
│  • Offset wells     │  [Active Well]       │  ┌───────────┐  │
│  • Radius slider    │  ┌─────────┐         │  │ Lost Circ │  │
│  • Geological       │  │ ████    │         │  │   Risk    │  │
│    relevance        │  │ ████    │ ←Bit    │  │   HIGH    │  │
│    color-coding     │  │ ████ ⚠  │         │  └───────────┘  │
│                     │  └─────────┘         │  ┌───────────┐  │
│                     │  [Offset-1]          │  │ Stuck Pipe│  │
│                     │  ┌─────────┐         │  │   Risk    │  │
│                     │  │ ████    │         │  │   MEDIUM  │  │
│                     │  │ ████ ✖  │         │  └───────────┘  │
│                     │  └─────────┘         │                  │
└─────────────────────┴──────────────────────┴──────────────────┘
┌────────────────────────────────────────────────────────────────┐
│            BOTTOM: AI Copilot + PDF Evidence Viewer             │
│  Search: "lost circulation in Tipam"                           │
│  Result: Well Moran-B2, 40 bbl loss at 3,242m [View PDF] →     │
└────────────────────────────────────────────────────────────────┘
```

**Technology:**
- **Frontend:** React 18 + TypeScript
- **Styling:** Tailwind CSS (dark mode default)
- **Charts:** Recharts or Plotly
- **Map:** React Leaflet (offline tiles)
- **Real-time:** WebSocket for live updates

**Responsive Design:**
- Desktop (1920x1080): Full 5-panel layout
- Tablet (1024x768): Collapsible side panels
- Mobile (768x1024): Tabbed interface

**Inputs:** APIs from Modules 1-6
**Outputs:** Unified dashboard interface

**Success Criteria:**
- Page load: <3 seconds
- Real-time updates: <500ms latency
- Usability: 100% of test users can find all features within 2 minutes

---

## 3. Technology Stack (Unchanged from v1.0)

### 3.1 Core Technologies

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React 18 + TypeScript | Modern UI, type safety, large community |
| **Backend** | FastAPI (Python 3.11+) | Async support, auto API docs, fast dev |
| **Database** | PostgreSQL 16 + PostGIS + pgvector | Spatial queries, vector search, proven at scale |
| **LLM** | Ollama + Llama 3.2 (local) | Air-gapped, no API costs, open-source |
| **OCR** | PaddleOCR | Multilingual, handles handwriting, open-source |
| **NLP** | spaCy + domain model | Entity extraction, fast inference |
| **Maps** | React Leaflet | Offline support, lightweight |
| **Deployment** | Docker + docker-compose | On-premise, air-gapped, repeatable |

### 3.2 Why Open-Source + On-Premise?

**MoPNG Security Requirements:**
- ❌ No cloud APIs (OpenAI, Pinecone, etc.)
- ❌ No external data egress
- ✅ Air-gapped deployment (rig site + HQ)
- ✅ All processing on local hardware

---

## 4. Development Sequence (4 Sprints × 5 Days)

### Sprint 1: Foundation (Days 1-5)

**Week 1 Goals:** Data + Core Intelligence

| Days | Module | Deliverable |
|------|--------|-------------|
| **Day 1-2** | Module 1 (Part 1) | OCR pipeline functional (3 PDFs → JSON) |
| **Day 3-4** | Module 1 (Part 2) | Database schema + data population (20 wells) |
| **Day 5** | Module 2 (Skeleton) | Basic GIS map with well markers |

**End of Sprint 1:**
- ✅ 20 wells in database (synthetic OIL India data)
- ✅ OCR extraction working (>90% accuracy)
- ✅ Map displays active well + 5 offset wells

---

### Sprint 2: Intelligence Layer (Days 6-10)

**Week 2 Goals:** Search + Correlation + Risk Models

| Days | Module | Deliverable |
|------|--------|-------------|
| **Day 6-7** | Module 3 | Search engine working (BM25 + vector) |
| **Day 8** | Module 4 | Depth correlation (MD → TVDSS) |
| **Day 9-10** | Module 5 (Part 1) | 2 risk models trained (loss + stuck pipe) |

**End of Sprint 2:**
- ✅ Search returns relevant analog cases
- ✅ Stratigraphic depth track aligned
- ✅ 2/5 risk models operational

---

### Sprint 3: Integration (Days 11-15)

**Week 3 Goals:** Alerts + Frontend Integration

| Days | Module | Deliverable |
|------|--------|-------------|
| **Day 11-12** | Module 5 (Part 2) | 3 more risk models (kick, torque, cement) |
| **Day 13-14** | Module 6 | Alert engine with lookahead warnings |
| **Day 15** | Module 7 (Part 1) | Frontend dashboard (3/5 panels functional) |

**End of Sprint 3:**
- ✅ 5/5 risk models operational
- ✅ Amber alerts triggering at correct thresholds
- ✅ Dashboard shows map + depth track + risk gauges

---

### Sprint 4: Polish + Demo Prep (Days 16-20)

**Week 4 Goals:** Final Integration + Demo Script

| Days | Focus | Deliverable |
|------|-------|-------------|
| **Day 16-17** | Module 7 (Part 2) | Complete dashboard (5/5 panels functional) |
| **Day 18** | Testing | End-to-end validation with synthetic data |
| **Day 19** | Demo Script | Live demo flow + presentation slides |
| **Day 20** | Rehearsal | Team run-through, bug fixes |

**End of Sprint 4:**
- ✅ Full system operational
- ✅ Demo script polished
- ✅ Presentation ready for judges

---

## 5. Critical Path & Dependencies

### Module Dependencies (Build Order)

```
Module 1 (Data Extraction)
    ↓
Module 2 (GIS Map) + Module 3 (Search) + Module 4 (Correlation)
    ↓
Module 5 (Risk Models)
    ↓
Module 6 (Alerts)
    ↓
Module 7 (Dashboard)
```

**Critical Path:** Module 1 → Module 5 → Module 6 → Module 7

**Parallel Work Streams:**
- Modules 2, 3, 4 can be developed in parallel after Module 1 completes
- Frontend (Module 7) can be mocked early, integrated later

---

## 6. Team Roles & Responsibilities

### Recommended Team Structure (5-7 members)

| Role | Primary Modules | Skills Required |
|------|----------------|-----------------|
| **Data Engineer** | Module 1 | Python, OCR, NLP, data wrangling |
| **Backend Engineer** | Modules 3, 5, 6 | Python, FastAPI, ML, algorithms |
| **GIS/Geo Specialist** | Modules 2, 4 | PostGIS, spatial algorithms, geology knowledge |
| **Frontend Engineer** | Module 7 | React, TypeScript, Tailwind, UI/UX |
| **ML Engineer** | Module 5 | scikit-learn, feature engineering, model training |
| **DevOps/Integration** | Docker, deployment | Docker, Linux, networking |
| **Product/Demo Lead** | Overall coordination | Presentation, demo scripting, judging criteria |

**Flexible Roles:** Team members can work on multiple modules

---

## 7. Testing & Validation Strategy

### 7.1 Module-Level Testing

Each module must pass acceptance criteria:

**Module 1:** OCR extraction accuracy >94% (validated against WITSML)
**Module 2:** Top-3 offset wells match geologist ranking
**Module 3:** Search top-3 precision >85%
**Module 4:** TVDSS conversion error <1%
**Module 5:** Incident recall >85%, FP rate <15%
**Module 6:** Alert lead time 30-60 min average
**Module 7:** Page load <3s, usability test pass

### 7.2 Integration Testing

**End-to-End Scenario:**
1. Upload 3 DDR PDFs → Module 1 extracts incidents
2. Search "lost circulation" → Module 3 returns analog cases
3. Open active well "Nahorkatiya-A1" → Module 2 shows map, Module 4 shows depth track
4. Bit advances to 3,230m → Module 5 calculates loss risk = HIGH
5. Module 6 triggers amber alert: "18m ahead to loss zone"
6. Module 7 dashboard displays all info in unified view
7. Engineer clicks PDF evidence → Opens DDR with highlighted paragraph

**Success Criteria:** Entire flow completes in <5 seconds

### 7.3 Demo Validation

**Test with 3 personas:**
1. Drilling Engineer (field): Can they act on amber alert in <2 minutes?
2. Operations Manager (office): Can they monitor 3 wells simultaneously?
3. Geologist: Can they verify geological relevance of offset wells?

---

## 8. Deployment Architecture

### 8.1 Two-Tier Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                  OIL INDIA HQ (Duliajan)                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  NWIS HQ Server (24/7 Operations Center)           │     │
│  │  - PostgreSQL (master database)                    │     │
│  │  - All 7 modules running                           │     │
│  │  - Monitors all active rigs                        │     │
│  │  - Archive storage (historical PDFs)               │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Sync when connectivity available
                            │ (not real-time requirement)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   RIG SITE (Remote, Air-Gapped)              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  NWIS Rig Server (Portable Deployment)             │     │
│  │  - PostgreSQL (local copy of relevant wells)       │     │
│  │  - Modules 1-7 (full system for this rig only)     │     │
│  │  - Offline operation (no HQ dependency)            │     │
│  │  - eRTMAC feed → Module 5 risk models              │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Hardware Requirements

**HQ Server:**
- CPU: 16 cores (Xeon or Ryzen)
- RAM: 64 GB
- Storage: 2 TB SSD (database + PDF archive)
- GPU: Optional (speeds up OCR, not required)

**Rig Server (Portable):**
- CPU: 8 cores
- RAM: 32 GB
- Storage: 500 GB SSD
- Form factor: Ruggedized rack-mount or NUC

### 8.3 Docker Deployment

**Single Command Deployment:**
```bash
docker-compose up -d
```

**Containers:**
1. `nwis-postgres` (PostgreSQL + PostGIS + pgvector)
2. `nwis-ollama` (Llama 3.2 LLM)
3. `nwis-backend` (FastAPI)
4. `nwis-frontend` (React)
5. `nwis-worker` (Background OCR jobs - optional)

**Auto-restart on failure:** Docker restart policy = `always`

---

## 9. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **OCR accuracy <90%** | Module 1 fails | Use pre-digitized CSVs as fallback; manual correction for 20 demo wells |
| **LLM too slow** | Module 3 search lag | Use BM25 only (skip vector search); pre-compute embeddings |
| **No GPU available** | Slower inference | Use CPU-only models; reduce batch size |
| **Team member drops out** | Delayed module | Cross-train team; simplify scope (5 modules instead of 7) |
| **Data download fails** | No training data | Use 3 FORGE PDFs + synthetic data (already sufficient) |
| **Judges want live eRTMAC feed** | No real data source | Mock eRTMAC feed with synthetic streaming data |

---

## 10. Success Metrics (Judging Criteria Alignment)

### Technical Feasibility (30%)
- ✅ All 7 modules functional
- ✅ Docker deployment works
- ✅ Air-gapped operation demonstrated

### Innovation & Uniqueness (25%)
- ✅ 4-pillar confidence framework (not black-box AI)
- ✅ Geological relevance (not just distance)
- ✅ 30-60 min lookahead (actionable lead time)

### Scalability & Practicality (20%)
- ✅ Works on commodity hardware (no GPU requirement)
- ✅ Handles 100+ offset wells
- ✅ Offline rig-site deployment

### User Experience & Impact (15%)
- ✅ Single-pane dashboard (no app switching)
- ✅ 1-click PDF evidence
- ✅ Usability tested with 3 personas

### Presentation & Demo (10%)
- ✅ Live demo (not just slides)
- ✅ Clear narrative (problem → solution → impact)
- ✅ 10-minute demo script polished

---

## 11. Next Steps (Immediate Actions)

### This Week:
1. ✅ Finalize team role assignments
2. ✅ Set up Git repository with `harshal` branch
3. ✅ Download remaining FORGE PDFs (aim for 10 total)
4. ✅ Start Module 1: OCR pipeline (use 3 existing PDFs)

### Next Week:
1. ⏳ Complete Module 1 (data extraction + database population)
2. ⏳ Start Module 2 (GIS map) in parallel
3. ⏳ Generate 20 synthetic OIL India wells

### Checkpoint (End of Week 2):
- Module 1: 100% complete
- Module 2: 50% complete (map displays wells)
- Module 3: 50% complete (search working)
- Module 4: 25% complete (depth conversion logic)

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-09-27 | Initial 10-module architecture | Team |
| 2.0 | 2026-09-27 | **Updated to 7 production modules** (teammate feedback) | Team |

---

## Appendix: Mapping to Original 10 Modules

**How v1.0 modules map to v2.0:**

| v1.0 (10 Modules) | v2.0 (7 Modules) |
|-------------------|------------------|
| M1: Database Schema | **Module 1** (Historical Data Extraction) |
| M2: Document Ingestion | **Module 1** (Historical Data Extraction) |
| M3: Synthetic Data Generator | **Module 1** (part of data preparation) |
| M4: Offset Relevance Engine | **Module 2** (Geospatial Intelligence) |
| M5: Depth Correlation Engine | **Module 4** (Geological Correlation) |
| M6: Hybrid Search System | **Module 3** (Knowledge Repository) |
| M7: Risk Prediction Engine | **Module 5** (Predictive Analytics) |
| M8: Alert Generation System | **Module 6** (Real-Time Alerts) |
| M9: Backend API Layer | Embedded in all modules (not separate) |
| M10: Frontend Command Cockpit | **Module 7** (Unified Dashboard) |

**Why consolidation works:**
- Clearer team coordination (7 deliverables vs. 10)
- Better alignment with PS expected outcomes (1:1 mapping)
- Simpler integration (fewer interfaces)
- Same technical depth, better organization

---

**For detailed module implementation**, see individual module docs (to be created):
- `Module-1-Data-Extraction.md`
- `Module-2-GIS-Intelligence.md`
- `Module-3-Knowledge-Repository.md`
- `Module-4-Geological-Correlation.md`
- `Module-5-Risk-Analytics.md`
- `Module-6-Alert-System.md`
- `Module-7-Dashboard.md`

**This document is the master architecture reference.** All module docs should align with this structure.
