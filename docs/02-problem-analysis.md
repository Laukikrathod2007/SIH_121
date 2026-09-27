# Problem Analysis & Breakdown
## SIH 26121 - eRTMAC-NWIS

**Document Version:** 1.0  
**Last Updated:** September 27, 2026  
**Status:** Active

---

## 1. Executive Problem Analysis

### 1.1 The Core Problem (What vs Why)

**WHAT Oil India Already Has:**
- ✅ Real-time drilling monitoring (eRTMAC)
- ✅ 30 years of drilling history (500+ wells)
- ✅ Technical expertise (drilling supervisors, engineers)
- ✅ Standardized data formats (WITSML)

**WHY The Problem Exists:**
```
ACTIVE WELL (Now)          HISTORICAL KNOWLEDGE (Past)
       ↓                            ↓
  3,220m depth              500 PDF reports scattered
  Formation C               Individual engineer memory
  Live telemetry            No depth-aware search
       ↓                            ↓
       └──────── GAP ─────────────┘
                  ↓
    "Which historical interval matters RIGHT NOW?"
```

**The Gap:** Historical drilling knowledge is **fragmented, unstructured, and not contextualized** to the active well's current depth/formation/trajectory.

### 1.2 Why Existing Solutions Don't Work

| Approach | Why It Fails |
|----------|--------------|
| **Manual report search** | Takes 2-4 hours; drill bit doesn't wait |
| **GIS-only map** | Shows nearby wells, but "nearby ≠ relevant" |
| **Generic chatbot** | Can't correlate depth intervals or geological horizons |
| **Simple database query** | Doesn't understand "approaching 3,240m in Tipam = approaching trouble zone from Well NHK-03" |

---

## 2. Problem Decomposition

### 2.1 Four Core Sub-Problems

```
┌─────────────────────────────────────────────────────────────────┐
│ PROBLEM 1: FIND RELEVANT OFFSET WELLS                          │
│ ├─ Geographic proximity (radius search)                         │
│ ├─ Geological similarity (formation, fault blocks)              │
│ ├─ Trajectory similarity (vertical vs deviated)                 │
│ └─ Dynamic relevance (changes as active well progresses)        │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PROBLEM 2: EXTRACT HISTORICAL KNOWLEDGE                        │
│ ├─ OCR scanned PDFs (1990s handwritten reports)                │
│ ├─ NLP extraction (events, depths, formations, NPT)            │
│ ├─ Structure unstructured narratives                            │
│ └─ Preserve document provenance (page numbers)                  │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PROBLEM 3: CORRELATE ACROSS DEPTH/FORMATION                    │
│ ├─ Align wells by geological horizon (not just MD)             │
│ ├─ Convert inclined wells to TVDSS                             │
│ ├─ Match current depth to historical incident intervals         │
│ └─ Account for stratigraphic variation                          │
└─────────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PROBLEM 4: PREDICT & WARN PROACTIVELY                          │
│ ├─ Detect current telemetry anomalies (live signals)           │
│ ├─ Match anomalies to historical precursor patterns            │
│ ├─ Calculate lead time (how far ahead is trouble zone?)        │
│ └─ Recommend actionable mitigation (not generic advice)         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Problem Complexity Matrix

| Sub-Problem | Technical Difficulty | Business Impact | MVP Priority |
|-------------|---------------------|-----------------|--------------|
| **Offset Well Discovery** | Medium | High | ⭐⭐⭐ Critical |
| **Document Extraction** | High (OCR + NLP) | Medium | ⭐⭐ High |
| **Depth Correlation** | High (geological alignment) | Critical | ⭐⭐⭐ Critical |
| **Risk Prediction** | Very High (ML models) | Critical | ⭐⭐⭐ Critical |

---

## 3. Root Cause Analysis (5 Whys)

**Problem:** Engineers cannot proactively mitigate drilling risks using historical knowledge.

**Why 1:** Historical information is not available at decision time.  
↓  
**Why 2:** Reports are unstructured PDFs scattered across file servers.  
↓  
**Why 3:** No system extracts and structures the information automatically.  
↓  
**Why 4:** Even if structured, no system correlates it to the active well's current geological context.  
↓  
**Why 5:** Traditional databases don't understand "3,220m in Formation C approaching historical loss zone at 3,242m."

**Root Cause:** **Lack of context-aware, depth-aligned, evidence-backed institutional memory system.**

---

## 4. Stakeholder Pain Point Analysis

### 4.1 Drilling Supervisor (Primary User)
**Current Pain:**
- Drill bit at 3,220m, uncertain if trouble ahead
- Must call experienced engineer to ask: "Did we have problems in this formation before?"
- Engineer searches manually for 2 hours → Bit already passed trouble zone

**Desired Outcome:**
- System alerts 45 minutes BEFORE entering known trouble zone
- Shows exactly what happened in offset well NHK-03 at 3,242m
- Recommends proven mitigation (e.g., "Prepare 25 bbl LCM pill")

**Success Metric:** "Saved ₹40 lakh ($50,000) by preventing 3-day NPT event"

### 4.2 eRTMAC Engineer (HQ Surveillance)
**Current Pain:**
- Monitoring 35 rigs simultaneously on video wall
- Cannot track which wells are approaching historically problematic intervals
- Reactive firefighting instead of proactive guidance

**Desired Outcome:**
- Dashboard shows all 35 wells with color-coded risk corridors
- Automatically highlights wells entering amber/red zones
- Can drill down into specific well to see evidence

**Success Metric:** "Prevented 2 NPT events this month by early warning"

### 4.3 Drilling Engineer (Technical Analyst)
**Current Pain:**
- Post-incident analysis takes 1 week
- Manual correlation of offset well data
- Recommendations based on incomplete historical data

**Desired Outcome:**
- Natural language search: "Lost circulation in Tipam Sandstone"
- Instant results with depth intervals, NPT hours, mitigation actions
- 1-click access to source documents

**Success Metric:** "Reduced post-incident analysis time from 1 week to 2 hours"

---

## 5. Technical Challenge Breakdown

### Challenge 1: The "Nearby ≠ Relevant" Problem

**Scenario:**
```
Active Well: NHK-25 at 3,220m in Tipam Sandstone
Candidate Offset Wells:
├─ NHK-22: 5 km away, SAME fault block, SAME formation → HIGHLY RELEVANT
├─ NHK-18: 3 km away, DIFFERENT fault block (sealed by thrust fault) → LOW RELEVANCE
└─ NHK-09: 12 km away, SAME formation, directional well → MEDIUM RELEVANCE
```

**Solution Requirements:**
- Geospatial distance calculation
- Geological fault block mapping
- Formation continuity analysis
- Trajectory similarity scoring
- Multi-factor relevance ranking

### Challenge 2: The OCR & Extraction Problem

**Input:** Scanned handwritten DDR from 1995
```
[Scanned image]
"At 3242m experienced total fluid loss. Pumped 30 bbl nut-plug pill.
Circulation restored after 4 hours. NPT = 8 hrs."
```

**Required Outputs:**
```json
{
  "event_type": "LOST_CIRCULATION",
  "depth_start_m": 3242,
  "formation": "Tipam Sandstone",
  "severity": "TOTAL",
  "mitigation": "30 bbl nut-plug LCM pill",
  "outcome": "circulation restored",
  "npt_hours": 8,
  "source_doc": "DDR_NHK03_1995_p47.pdf",
  "extraction_confidence": 0.89
}
```

**Technical Stack Needed:**
- OCR engine (Tesseract/PaddleOCR/Google Vision)
- Layout-aware parser (unstructured.io)
- Domain-specific NER (Named Entity Recognition)
- Validation rules (depth ranges, unit conversions)

### Challenge 3: The Depth Alignment Problem

**Geological Reality:**
```
Well A (Vertical)        Well B (35° deviated)      Active Well (40° deviated)
   |                         /                           /
   | 3,200m MD             / 3,350m MD                 / 3,420m MD
   | Formation C          / Formation C                / Formation C
   |                     /                            /
   | 2,800m TVDSS ─────────── SAME HORIZON ───────────── 2,800m TVDSS
   |                     /                            /
```

**Challenge:** Match events by **geological horizon**, not just measured depth (MD).

**Solution:** Convert all depths to True Vertical Depth Subsea (TVDSS) using well trajectories.

### Challenge 4: The Multi-Risk Prediction Problem

**Five Different Hazard Families:**
1. **Lost Circulation:** Fracture gradient, flow delta (ΔQ), pit levels
2. **Stuck Pipe:** Overpull, MSE, torque patterns, connection time
3. **Kick/Overpressure:** ROP breaks, pit gains, gas shows, d-exponent
4. **Torque Spikes:** Stick-slip, torsional oscillations, rotary torque
5. **Cementing Issues:** CBL history, mud displacement, density variation

**Problem:** Each requires DIFFERENT models and DIFFERENT telemetry signals.

**Anti-Pattern:** ❌ Single "XGBoost model predicting all risks"  
**Correct Approach:** ✅ Five specialized risk engines with unified interface

---

## 6. Data Flow Analysis

### 6.1 Historical Data Pipeline
```
Legacy PDFs (1990-2020)
    ↓
OCR + Layout Parser
    ↓
NLP Event Extraction
    ↓
Structured JSON Events
    ↓
PostgreSQL Database (WITSML schema)
    ↓
Vector Embeddings (for semantic search)
    ↓
Hybrid Search Index (BM25 + Vector)
```

### 6.2 Real-Time Analytics Pipeline
```
eRTMAC Live Stream (1-5 sec updates)
    ↓
Current Well State
    ↓
Offset Relevance Engine → Find relevant wells
    ↓
Historical Event Query → Fetch past incidents
    ↓
Depth Correlation → Align MD → TVDSS
    ↓
Risk Assessment → 5 parallel risk models
    ↓
Alert Decision → Proactive warning logic
    ↓
Dashboard Update (WebSocket push)
```

---

## 7. Architectural Constraints

### 7.1 Security Constraints (Hard Requirements)
- **Air-Gapped Deployment:** No cloud APIs (MoPNG/DGH mandate)
- **On-Premise Only:** Must run on OIL's servers in Duliajan HQ
- **Data Sovereignty:** No data leaves India; no external model APIs

**Impact on Design:**
- ❌ Cannot use OpenAI/Anthropic APIs
- ❌ Cannot use cloud-hosted vector databases (Pinecone)
- ✅ Must use local LLMs (Ollama, Llama 3.2)
- ✅ Must use self-hosted vector store (pgvector, Qdrant)

### 7.2 Integration Constraints
- **Cannot Replace eRTMAC:** Must act as sidecar/companion system
- **Read-Only Access:** Cannot write back to eRTMAC databases
- **WITSML Compatibility:** Must parse WITSML 2.1 XML formats

### 7.3 Operational Constraints
- **24/7 Availability:** Drilling operations never stop
- **Low Latency:** Alerts must appear within 3 seconds
- **Offline Resilience:** Rig-site deployment must work during network outages

---

## 8. Success Criteria Breakdown

### 8.1 Technical Success Metrics
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Alert Lead Time | 30-60 minutes | Time between alert and actual event |
| False Alarm Rate | <15% | Alerts that did NOT lead to incidents |
| Search Precision@5 | >80% | Top 5 results contain relevant answer |
| OCR Accuracy (critical fields) | >85% | Depth, formation, event type extraction |
| System Latency | <3 seconds | Alert generation after telemetry update |

### 8.2 Business Success Metrics
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| NPT Events Prevented | 2+ per month | Documented cases of avoided incidents |
| Decision Time Reduction | 50% faster | Time to retrieve historical analogue |
| Engineer Trust Score | >4.0/5.0 | Post-deployment user survey |
| ROI (Cost Savings) | ₹40L+ per saved NPT event | ₹1L/hr rig cost × hours saved |

---

## 9. Risk-Adjusted Implementation Strategy

### 9.1 High-Risk Areas (Require Mitigation)
1. **OCR Accuracy on Handwritten Reports**
   - **Risk:** Low extraction accuracy → False alerts
   - **Mitigation:** Human-in-the-loop validation UI + confidence scoring

2. **False Alarm Fatigue**
   - **Risk:** Too many warnings → Engineers ignore system
   - **Mitigation:** Multi-pillar evidence framework + tunable thresholds

3. **Geological Misalignment**
   - **Risk:** Incorrect depth correlation → Wrong historical analogue
   - **Mitigation:** Geologist validation step in MVP + formation top QC

### 9.2 Dependency Risks
| Dependency | Risk | Mitigation |
|------------|------|------------|
| eRTMAC API access | May not be granted in time | Build standalone simulator |
| Historical data quality | Incomplete/corrupted PDFs | Start with best 20 wells |
| Rig-site network | VSAT outages | Edge caching + offline mode |

---

## 10. Competitive Differentiation Analysis

### 10.1 How NWIS Differs from Existing Solutions

| Solution | Limitation | NWIS Advantage |
|----------|-----------|---------------|
| **SLB Tela Offset Wells Insights** | Cloud-only, generic chatbot | On-premise, depth-aware correlation |
| **Halliburton OpenWells** | Focus on NPT analysis, not proactive alerts | Proactive 45-min early warnings |
| **Cognite Know Your Well** | Document search, no risk prediction | Combines search + ML risk models |
| **Generic GIS Map** | Shows location, not geological relevance | Subsurface-aware relevance scoring |

### 10.2 Key Differentiators (What Makes NWIS Unique)
1. **Dynamic Offset Relevance:** Relevance score changes as drill bit advances
2. **Interval-Aware Correlation:** Matches geological horizons, not just well names
3. **4-Pillar Evidence Framework:** Separates historical evidence, live anomaly, data quality, and source grounding
4. **Proactive Lead Time:** Warns 30-60 minutes BEFORE entering trouble zone
5. **100% Air-Gapped:** Complies with India's data sovereignty requirements

---

## 11. Problem-Solution Mapping (PS Expected Outcomes)

| PS Outcome | Core Problem | Proposed Solution Module |
|------------|--------------|-------------------------|
| (i) Extract & structure historical data | Fragmented PDFs | **Document Ingestion Pipeline** |
| (ii) Interactive map of nearby wells | Geographic discovery | **Geospatial Offset Engine** |
| (iii) Searchable knowledge repository | Information retrieval | **Hybrid Search & RAG** |
| (iv) Correlate across wells by depth | Geological misalignment | **Depth Correlation Engine** |
| (v) Predictive risk analytics | Reactive decision-making | **Multi-Hazard Risk Models** |
| (vi) Real-time alerts & recommendations | Late warnings | **Proactive Alert System** |
| (vii) User-friendly dashboard | Context switching | **Unified Command Cockpit** |

---

## 12. Validation Strategy

### 12.1 How We Will Validate the Solution
1. **Historical Backtesting:**
   - Take 10 known NPT events from 2020-2025
   - Replay telemetry data through NWIS
   - Measure: Would NWIS have alerted 30+ minutes early?

2. **Geologist Review:**
   - Show depth correlation results to OIL geologists
   - Validate formation alignment accuracy

3. **User Acceptance Testing:**
   - 2-week pilot with 3 drilling engineers
   - Collect feedback on usability and trust

4. **False Alarm Analysis:**
   - Track all alerts for 1 month
   - Calculate precision/recall for each risk type

---

## 13. Next Steps

Based on this analysis, we proceed to:
1. ✅ Finalize modular architecture design
2. ✅ Create detailed implementation plan
3. ✅ Define MVP scope (20-well dataset)
4. → Begin parallel module development

---

**Document Control:**
- Living document (updated as new insights emerge)
- Changes tracked in Git
- Team consensus required for major changes
