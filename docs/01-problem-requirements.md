# Problem Requirements Document
## SIH 26121 - eRTMAC-NWIS

**Document Version:** 1.0  
**Last Updated:** September 27, 2026  
**Status:** Active

---

## 1. Problem Statement Summary

Oil India Limited requires an AI-powered **Nearby Wells Intelligence System (NWIS)** that transforms fragmented historical drilling knowledge into contextual, depth-aware, evidence-backed intelligence for active drilling operations.

### 1.1 Core Problem
- **Current Gap:** Historical drilling knowledge exists across 500+ well completion reports, daily drilling reports, and individual engineer memory
- **Impact:** Decision delays, missed risk mitigation opportunities, preventable NPT (Non-Productive Time)
- **Root Cause:** No unified system to contextualize historical offset-well knowledge at decision time

---

## 2. Functional Requirements

### FR-1: Intelligent Document Processing
**Priority:** Critical  
**PS Mapping:** Expected Outcome (i)

- **FR-1.1** Extract structured data from scanned PDFs (DDRs, WCRs from 1990s onwards)
- **FR-1.2** OCR processing for legacy handwritten drilling reports
- **FR-1.3** NLP extraction of:
  - Formation top depths and casing shoe seats
  - Mud properties (density, viscosity, water loss)
  - Operational remarks and incident narratives
  - NPT hours and root causes
  - Mitigation actions and outcomes
- **FR-1.4** Output WITSML-compliant structured records
- **FR-1.5** Preserve source document provenance (page number, extraction confidence)

### FR-2: Geospatial Offset Well Discovery
**Priority:** Critical  
**PS Mapping:** Expected Outcome (ii)

- **FR-2.1** Interactive dark-mode GIS map showing:
  - Active well (pulsing green marker)
  - Historical offset wells (color-coded by relevance)
- **FR-2.2** Dynamic radius filtering (5 km to 50 km slider)
- **FR-2.3** Subsurface-aware relevance scoring:
  - Geographic proximity
  - Geological fault block sharing
  - Formation continuity
  - Pressure regime similarity
- **FR-2.4** Wells separated by sealing faults grayed out automatically

### FR-3: Institutional Memory Knowledge Base
**Priority:** Critical  
**PS Mapping:** Expected Outcome (iii)

- **FR-3.1** Natural language search interface:
  - Example: "Lost circulation in Tipam Sandstone below 3,000 meters"
  - Example: "Stuck pipe during casing run in Barail Coal"
- **FR-3.2** Return structured result cards with:
  - Past analog cases
  - Root causes
  - NPT hours lost
  - Proven historical mitigation recipe
- **FR-3.3** 1-click PDF evidence viewer with highlighted relevant paragraphs

### FR-4: Cross-Well Depth Correlation
**Priority:** Critical  
**PS Mapping:** Expected Outcome (iv)

- **FR-4.1** Dual stratigraphic depth track visualization:
  - Column 1: Active well (live drilling)
  - Columns 2-4: Top 3 relevant offset wells
- **FR-4.2** Automatic horizon alignment:
  - Convert inclined wells to True Vertical Depth Subsea (TVDSS)
  - Align by geological formation (Tipam ↔ Tipam, Barail ↔ Barail)
- **FR-4.3** Real-time bit position marker on aligned tracks
- **FR-4.4** Historical incident markers plotted at exact geological horizons

### FR-5: Multi-Hazard Risk Analytics
**Priority:** Critical  
**PS Mapping:** Expected Outcome (v)

- **FR-5.1** Five specialized risk gauges (independent models):
  1. **Lost Circulation Risk:**
     - Flow-out vs flow-in delta (ΔQ)
     - Offset loss history in same formation
     - Formation fracture gradient proximity
  2. **Stuck Pipe Risk:**
     - Overpull trends
     - Mechanical Specific Energy (MSE) anomaly
     - Torque fluctuation patterns
  3. **Kick/Overpressure Risk:**
     - Sudden ROP drilling breaks
     - Pit volume gains
     - d-exponent trend deviations
  4. **Torque & Drag Dysfunction:**
     - Stick-slip torsional resonance detection
     - Hookload vs depth gradient
  5. **Cementing Integrity Risk:**
     - Offset cement bond log (CBL) failure history
     - Mud displacement efficiency predictors

- **FR-5.2** 4-Pillar Confidence Framework (NOT single "85% risk"):
  - **Evidence Strength:** (High: N≥3 wells | Medium: N=2 | Low: N=1 | None: N=0)
  - **Live Anomaly:** Current telemetry deviation severity
  - **Data Quality:** % of required parameters available
  - **Source Grounded:** % of claims traceable to documents

### FR-6: Proactive Early Warning System
**Priority:** Critical  
**PS Mapping:** Expected Outcome (vi)

- **FR-6.1** Three-state alert banner:
  - **Green (Safe):** >50m from known hazard zone
  - **Amber (Proactive Warning):** 15-50m from hazard zone
  - **Red (Immediate):** <15m or event detected
  
- **FR-6.2** Amber alert must include:
  - Distance to hazard zone
  - Expected interval (depth range)
  - Recommended preparation actions
  - Lead time estimate (30-60 minutes)

- **FR-6.3** Auto-trigger audible chime in control room
- **FR-6.4** Simultaneous display on:
  - Central eRTMAC video wall (Duliajan HQ)
  - Rig-site touch-PC (Company Man cabin)

### FR-7: Unified Command Cockpit
**Priority:** High  
**PS Mapping:** Expected Outcome (vii)

- **FR-7.1** Single-pane glass architecture (no app switching)
- **FR-7.2** Screen layout:
  - **Left:** Interactive GIS map
  - **Middle:** Stratigraphic depth track & risk corridor
  - **Right:** Live sensor gauges & anomaly strips
  - **Top:** Real-time alert banner
  - **Bottom/Modal:** AI copilot & 1-click evidence viewer
  
- **FR-7.3** Dark mode optimized for 24/7 control room viewing
- **FR-7.4** High-contrast ergonomics for field cabin touch-PCs
- **FR-7.5** Responsive design: 4K video wall + rugged 15" touch-PC

---

## 3. Non-Functional Requirements

### NFR-1: Security & Compliance
**Priority:** Critical

- **NFR-1.1** 100% on-premise deployment (no cloud leakage)
- **NFR-1.2** Air-gapped architecture compliant with:
  - Ministry of Petroleum & Natural Gas (MoPNG) mandates
  - DGH National Data Repository (NDR) security policies
- **NFR-1.3** Role-based access control (RBAC):
  - Drilling Supervisor (Full Access)
  - Drilling Engineer (Analytical Access)
  - eRTMAC Analyst (Monitoring Access)
  - Geologist/Reservoir Engineer (Context Access)

### NFR-2: Performance
**Priority:** Critical

- **NFR-2.1** Alert generation latency: <3 seconds from telemetry update
- **NFR-2.2** Map interaction responsiveness: <200ms pan/zoom
- **NFR-2.3** Search query response: <2 seconds for natural language queries
- **NFR-2.4** Document ingestion throughput: 50 PDFs/hour with OCR
- **NFR-2.5** System uptime: 99.5% availability (24/7 operations)

### NFR-3: Scalability
**Priority:** High

- **NFR-3.1** Support 35+ simultaneous active wells
- **NFR-3.2** Historical database: 500+ wells × 30 years of records
- **NFR-3.3** Concurrent users: 50+ engineers across HQ + rig sites

### NFR-4: Reliability
**Priority:** Critical

- **NFR-4.4** Graceful degradation if AI services fail (fallback to rule-based alerts)
- **NFR-4.2** Offline-capable rig-site deployment (VSAT/4G loss resilience)
- **NFR-4.3** Data consistency between HQ and rig-site mirrors

### NFR-5: Maintainability
**Priority:** High

- **NFR-5.1** Modular architecture allowing independent module updates
- **NFR-5.2** Comprehensive logging (audit trail for every alert)
- **NFR-5.3** Extraction confidence scoring for quality monitoring
- **NFR-5.4** A/B testing framework for model improvements

---

## 4. Data Requirements

### Available Data Sources (from PS)
1. Well Completion Reports (WCRs) - 500+ PDFs, some handwritten
2. Daily Drilling Reports (DDRs) - 30 years of records
3. Drilling and mud logging databases - WITSML format
4. eRTMAC real-time data streams - Current implementation
5. Well trajectory and survey data - Directional drilling records
6. Casing, cementing, and mud program records
7. Historical operational event records (NPT database)
8. Reservoir and geological data (formation tops, pressure tests)

### Data Quality Requirements
- **Minimum viable dataset for MVP:** 10-20 wells with complete records
- **Production dataset:** 500+ wells across Upper Assam fields
- **Real-time telemetry frequency:** 1-5 second updates from eRTMAC

---

## 5. User Personas

### Primary Users
1. **Drilling Supervisor (Rig Site)**
   - Role: Real-time operational decision maker
   - Need: Proactive alerts with actionable recommendations
   - Context: Rig cabin, touch-PC, 24/7 operations

2. **eRTMAC Engineer (HQ Control Room)**
   - Role: Multi-well surveillance analyst
   - Need: Simultaneous monitoring of 35+ wells
   - Context: Video wall dashboard, HQ Duliajan

3. **Drilling Engineer (Technical Support)**
   - Role: Analytical investigation and planning
   - Need: Deep-dive into historical analogues
   - Context: Office desktop, detailed analysis mode

### Secondary Users
4. **Geologist/G&R Engineer**
   - Role: Formation context validation
   - Need: Verify geological correlation accuracy

5. **Reservoir Engineer**
   - Role: Pressure/subsurface behavior analysis
   - Need: Cross-well pressure regime patterns

---

## 6. Success Metrics (Prototype Phase)

### Quantitative Metrics
- **Alert Lead Time:** Achieve 30-60 minute proactive warnings
- **False Alarm Rate:** <15% (better than acceptable 20% industry threshold)
- **Evidence Traceability:** 100% of alerts linked to source documents
- **Search Precision@5:** >80% relevant results in top 5
- **Document Extraction Accuracy:** >85% for critical fields

### Qualitative Metrics
- **Engineer Trust Score:** Survey-based confidence rating
- **Decision Time Reduction:** Time saved vs manual report search
- **NPT Prevention Cases:** Documented incidents avoided

---

## 7. Constraints & Assumptions

### Technical Constraints
- Must integrate with existing eRTMAC infrastructure (non-disruptive)
- WITSML 2.1 compatibility required
- PostgreSQL + PostGIS database mandate (OIL IT policy)
- No external API calls (air-gapped deployment)

### Operational Constraints
- Cannot replace human decision authority (human-in-the-loop mandatory)
- Recommendations must be explainable (no black-box ML)
- System must degrade gracefully (no sudden failures)

### Assumptions
- OIL will provide representative sample dataset for MVP
- eRTMAC data stream API is accessible
- Rig-site network connectivity via VSAT/4G exists (with interruptions)

---

## 8. Out of Scope (Explicitly NOT Required for MVP)

1. **Full Digital Twin:** Physics-based simulation (future extension)
2. **Graph Neural Networks (GNN):** Research direction, not MVP requirement
3. **Autonomous Rig Control:** System remains decision-support only
4. **Decorative 3D Visualization:** Focus on functional intelligence
5. **Generic Chatbot:** Structured search over conversational AI
6. **Federated Learning:** Single-organization deployment

---

## 9. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient historical data quality | High | Implement extraction confidence scoring + manual validation workflow |
| False alarm fatigue | High | Multi-pillar evidence framework + tunable thresholds |
| eRTMAC integration complexity | Medium | Build standalone with optional eRTMAC connector |
| OCR accuracy on handwritten reports | Medium | Hybrid OCR + manual correction UI |
| Network latency at rig sites | Medium | Edge caching + offline mode |

---

## 10. Approval & Sign-off

**Document Prepared By:** SIH 2026 Team  
**Reviewed By:** [Pending - Team Lead]  
**Approved By:** [Pending - SIH Mentor]  

**Next Steps:**
1. Review and approve requirements ✓
2. Create detailed problem analysis document
3. Design modular implementation plan
4. Begin MVP development

---

**Document Control:**
- This is a living document
- Changes require team consensus
- Version history maintained in Git
