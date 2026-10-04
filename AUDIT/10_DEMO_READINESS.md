# Demo-Readiness Audit

**Date:** 2026-10-04
**Labels used:** DEMO READY, DEMO READY WITH SIMULATION, DEMO READY WITH LIMITATION, NOT DEMO READY.

---

### Feature: Nearby wells — 2D map
**Route:** `/app/offset-map` or `/app/wells`
**User action:** Select active well, drag radius slider, click an offset well
**Backend:** Module 02 `GET /api/v2/map/wells`, `/api/v2/offset_rank/{id}`
**Data:** 12 synthetic + 2 real Volve wells
**Expected result:** Map centers on active well, offset wells ranked and shown within the visually-filtered radius
**Evidence:** Verified live, screenshots in `AUDIT/evidence/`
**Limitation:** The backend's own `radius_km` API parameter is a scoring weight, not a hard filter (frontend correctly compensates) — explain this if a judge inspects the raw API
**Status: DEMO READY**

### Feature: Nearby wells — 3D globe
**Route:** `/app/globe`
**User action:** Select active well, rotate/zoom, click a marker
**Backend:** Same as above
**Data:** Same catalog
**Expected result:** Real Earth geography, correctly-placed markers, active-well sync with the rest of the app
**Evidence:** Verified live and geographically correct after a real bug was found and fixed this project
**Limitation:** No "fly to active well" camera assist — a judge unfamiliar with the globe may need guidance to find a specific well; no terrain/underground scenes (explicitly out of scope, not attempted)
**Status: DEMO READY WITH LIMITATION**

### Feature: Document ingestion
**Route:** `/app/documents`
**User action:** Upload a real PDF
**Backend:** Module 01, full 6-layer pipeline
**Data:** Real uploaded PDF; real Volve sample PDFs available in `real_data/volve/`
**Expected result:** Real extraction result with formations, events, confidence score, possible physics auto-repair
**Evidence:** Live end-to-end test performed this audit — real, internally consistent JSON result
**Limitation:** Entity extraction is regex-based, not NLP/ML — be precise about this if asked; cloud fallback is live-armed on this checkout (will make a real outbound API call below 0.75 confidence)
**Status: DEMO READY**

### Feature: Knowledge/historical search
**Route:** `/app/knowledge` or `/app/copilot`
**User action:** Type a natural-language query
**Backend:** Module 02 semantic search
**Data:** 44 events (39 synthetic + 5 real)
**Expected result:** Relevance-ranked results mixing real and synthetic events, real evidence citations
**Evidence:** Live-tested, `search_mode: "semantic"` confirmed
**Limitation:** Vector search is a brute-force in-process scan, not a production index — entirely adequate at this scale, but say so if asked about scaling
**Status: DEMO READY**

### Feature: Geological correlation
**Route:** `/app/correlation`
**User action:** View stratigraphic alignment / risk corridors for the active well
**Backend:** Module 02 engines
**Data:** Real + synthetic formation/trajectory data
**Expected result:** Real depth-aligned correlation across offset wells
**Evidence:** Live-verified
**Limitation:** None significant
**Status: DEMO READY**

### Feature: Risk prediction — hazard scores
**Route:** `/app/risk`, Command Center
**User action:** Select a well, view the 7 hazard cards
**Backend:** Module 02 `analyzeWell`
**Data:** 3 of 7 hazards trained-model-backed (synthetic), 4 heuristic
**Expected result:** Each hazard card honestly shows a "TRAINED MODEL" or "HEURISTIC" badge
**Evidence:** Live-verified exactly matching the per-hazard audit in `06_ML_AND_MODEL_AUDIT.md`
**Limitation:** Be ready to explain precisely which 3 hazards are ML-backed and why the other 4 aren't (insufficient labeled examples) — this is a strength if explained honestly, a liability if glossed over
**Status: DEMO READY WITH LIMITATION**

### Feature: Predictive analytics (module 05) — alerts/advisory
**Route:** `/app/alerts`
**User action:** Start the simulator, watch for alerts
**Backend:** Module 04/05
**Data:** Live physics simulation (not real rig data)
**Expected result:** Real-time alert generation as simulated telemetry crosses thresholds
**Evidence:** Simulation advancement confirmed live; actual alert firing under a real threshold breach was not observed in this audit's short test window
**Limitation:** Two of three ML pillars (Isolation Forest, XGBoost) are honestly UNFITTED_FALLBACK — only the deterministic rules pillar is active. The simulator must be manually started; it is not running by default.
**Status: DEMO READY WITH SIMULATION**

### Feature: Physics digital twin
**Route:** `/app/drilling`, `/app/simulator`
**User action:** Start/pause/inject a scenario
**Backend:** Module 04
**Data:** Real coupled physics equations, live-advancing
**Expected result:** Real-time telemetry stream, visible 3D rig scene
**Evidence:** Live before/after advancement test confirmed real progression
**Limitation:** This is a simulated digital twin, not real OIL India rig/eRTMAC data — no such feed exists or was obtainable; say this plainly rather than letting a judge assume otherwise
**Status: DEMO READY WITH SIMULATION**

### Feature: System status / backend health
**Route:** `/app/status`
**User action:** View live health of all three backends
**Backend:** All three
**Data:** Real live health checks
**Expected result:** All three show HEALTHY with real sub-status detail
**Evidence:** Live-verified, including the honest UNFITTED_FALLBACK model statuses
**Limitation:** Module 04's own `/health` has one static field (`status`) not derived from a real check — minor, not user-facing in a way that would mislead a judge watching the dashboard
**Status: DEMO READY**

### Feature: Evidence/citation viewer
**Route:** Any page with a source-document citation
**User action:** Click a citation
**Backend:** evidence-server (Node) or module 01
**Data:** 42 real/synthetic mixed PDFs
**Expected result:** Real PDF opens; for the rare case where no real PDF exists for a historical-testbed-only event, an honest "not found" message appears instead of fabricating a viewer
**Evidence:** Live-tested both paths
**Limitation:** None — this honest-failure behavior is a strength to highlight, not hide
**Status: DEMO READY**

---

## Features NOT ready to demo as claimed

**"AI/NLP document extraction"** — if phrased exactly this way, this is **NOT DEMO READY as literally described**. The OCR is real AI (Docling); the entity extraction is real but is regex/rules, not AI/NLP. Recommend describing this precisely ("AI-powered OCR + deterministic rules-based structuring") rather than claiming NLP/NER that isn't present.

**"Real-time eRTMAC integration"** — **NOT APPLICABLE / NOT DEMO READY as a real integration**, because no real eRTMAC feed exists or was ever available to integrate against. The physics digital twin is a legitimate, honestly-labeled substitute and should be presented as exactly that.

**Fishing-operations event tracking** — **NOT DEMO READY**, because the data model has no slot for it at all. Do not claim this PS-named event type is supported.
