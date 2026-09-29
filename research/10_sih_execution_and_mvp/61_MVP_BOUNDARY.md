# SIH 26121 — MVP Boundary & Scope Enforcement

## 1. Executive Summary
In rapid hackathon prototyping, project failure is almost invariably caused by scope creep—attempting to build an entire enterprise ERP or complex physical CFD simulator in 36 hours. This document establishes the strict three-tier boundary for NWIS: defining what is mandatory for the prototype, what is secondary, and what is strictly prohibited.

---

## 2. The Three-Tier Architectural Scope Boundary

```
                                  MVP BOUNDARY HIERARCHY
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: CORE MUST-HAVE MVP (The Winning Core — 100% Implemented)                       │
│ • Real-time 1-Hz WebSocket telemetry stream replay.                                    │
│ • PostGIS geospatial offset map with dynamic stratigraphic ratio normalization (ξ).   │
│ • Ahead-of-the-bit Historical Risk Corridor calculation (target depth ±30 m).          │
│ • Decoupled Mud Loss & Stuck Pipe predictive inference engines (<20 ms latency).       │
│ • TreeSHAP physical feature attribution cards on live alerts.                          │
│ • PDF Document Viewer with exact bounding-box highlighting on historical DDRs.         │
│ • Tool-Augmented Orchestrator Agent for natural-language operational queries.          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: GOOD-TO-HAVE (Demonstrated if Time Permits)                                    │
│ • 3D WebGL Minimum Curvature borehole trajectory viewer (Three.js).                   │
│ • Secondary hazard engines: Kick overpressure & Torsional stick-slip detection.        │
│ • Dynamic calibration parameter sliders on the rig console UI.                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: STRICTLY EXCLUDED SCOPE CREEP (Disqualifying Engineering Traps)                │
│ ❌ Closed-Loop Autonomous Control (Modulating physical drawworks/pumps).               │
│ ❌ 3D Pre-Stack Seismic Inversion & Reservoir Geocellular Modeling.                   │
│ ❌ Multi-Agent Swarm Debate Loops (Unsupervised LLM debates).                         │
│ ❌ Proprietary Cloud Dependencies (AWS/GCP/OpenAI public API lock-in).                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Granular Deliverable Specifications

### Tier 1: Core Must-Have Deliverables
1. **Streaming Rig Telemetry Engine:** Replays 1-Hz WITS data (ROP, WOB, RPM, Torque, SPP, Flow In/Out, Pit Volume) via local WebSocket connections to the frontend.
2. **Dynamic Offset Ranker:** Executes PostGIS spatial query, computes dynamic depth relevance $\Omega(w, z)$, and returns top 3 ranked offsets in $< 50$ ms.
3. **Historical Risk Corridor:** Projects active target interval and searches offset database for historical loss or sticking events at that stratigraphic horizon.
4. **Predictive Corroboration Engine:** LightGBM classifier evaluates rolling telemetry features against historical risk profiles to confirm early warning.
5. **Explainability & Bounding Box:** Renders top 3 TreeSHAP driving features and provides an interactive modal displaying the exact audited DDR PDF page with bounding box highlight.
6. **Tool-Augmented Chat:** Single LLM with 5 deterministic function calls answering natural-language drilling queries.

---

## 4. Architectural Verdict for SIH 26121

**Verdict:** `[DEFEND TIER 1 AT ALL COSTS]`.
- Delivering a **rock-solid, visually stunning, bug-free Tier 1 prototype** will easily outperform competitors who build half-functional, broken mega-systems.
- Tier 3 features are explicitly defended before the judges as intentional engineering exclusions that preserve rig safety and operational feasibility.
