# PS 26121 gap plan: what's missing and how to cover it

**Project:** DrillWise · eRTMAC-NWIS · SIH 2026 · Oil India Limited
**Date:** 23 November 2026
**Basis:** the code on `main` (commit `2078e40`), the backend audit (152 unit and contract tests passing), and checks run while deploying.

Each requirement in Problem Statement 26121 is mapped to what exists today, what's missing, the change that closes the gap, and how to do it.

**Status:** ✅ covered · 🟡 partly · ❌ missing
**Effort:** S = under a day · M = 1–3 days · L = 3+ days

## Facts checked in the code

- The event schema has 8 hazard types: kick, mud loss, lost circulation, stuck pipe, torque spike, wellbore instability, cementing failure and fishing operation. It has **no overpressure** type.
- Trained models exist for 3 of them (`real_data/real_trained_models/`: kick, stuck pipe, wellbore instability, about 2 KB each).
- The IsolationForest and XGBoost models in module 05 are trained only inside tests; no saved models exist.
- The repo has real Volve WITSML data: 63 XML files (trajectories and logs) across about 20 wells, unused as a data stream.
- There are no casing, cementing or mud-programme data files, only formation tops (`modules/02_nwis_backend/data/synthetic/formation_tops.json`).
- Module 04's health check is hardcoded to `"healthy"` (`modules/04_physics_engine/api/server.py:269`).

---

## 1. Expected outcomes (what the solution should do)

### i. Use AI, NLP, OCR and analytics to extract and structure report data: 🟡

| | |
|---|---|
| **Today** | A six-layer pipeline: PyMuPDF text, Docling OCR for scans, rule-based extraction, templates, physics validation, and JSON output with page links. It has been run on 14 Volve documents. |
| **Gap** | Extraction is rules and regex, not a trained NLP model. Docling and semantic search are optional installs and aren't on the deployed backend, so live it's text parsing only. |
| **Change 1 (M)** | Add a real NLP step: a named-entity model (spaCy, already in `requirements-optional.txt`) trained on our extracted events to tag depth, formation, event type, mud weight and mitigation. Keep the rules as a fallback and a cross-check. |
| **Change 2 (S)** | Show precision and recall from the 14 Volve documents on the Document Ingestion page, so "AI extraction" comes with numbers. |
| **Change 3 (M)** | Make OCR available live, either on a heavier Render plan or by running OCR in a background job. Otherwise, show plainly in the UI that OCR needs the full install. |
| **How** | Use the existing extracted events as labelled data, train spaCy on them, and score it on a held-out set of Volve pages. |

### ii. Interactive map of nearby wells within a user-defined radius: ✅

| | |
|---|---|
| **Today** | 2D map, 3D Cesium globe, radius filter, and a 5-factor relevance score (DORS) with every component shown. |
| **Gap** | Small. The globe only works through the sibling `nwis-spatial-visualization` project, and there are only 12 demo wells. |
| **Change (S)** | Load the 20 real Volve wells as a second field, with their real trajectories, so the map works on real geometry too. |

### iii. Searchable repository of events, lessons learned and mitigations: 🟡

| | |
|---|---|
| **Today** | Event search, an evidence-grounded Copilot, and links to the source PDF page. |
| **Gap** | About 44 events, so the search can't show scale. Semantic search is off on the deployed backend. There's no separate "lessons learned" record type; lessons sit inside event text. |
| **Change 1 (M)** | Grow the corpus. Extract every Volve drilling report and add a larger labelled synthetic set of a few hundred events across the 12 wells. |
| **Change 2 (S)** | Add a `lesson` and `mitigation_outcome` field per event (worked, partly worked, failed), searchable and filterable. |
| **Change 3 (S)** | Turn on lightweight semantic search without the heavy model: precompute embeddings at build time and ship them with the data, so the free tier can still run it. |

### iv. Correlate geological, drilling and reservoir data by depth and formation: 🟡

| | |
|---|---|
| **Today** | Minimum-curvature trajectories, TVD/TVDSS, a formation-position index, and cross-well formation alignment. |
| **Gap** | No reservoir data (porosity, permeability, pore pressure) and no drilling-parameter correlation, such as ROP or mud weight per formation across wells. The PS also lists casing programmes and cementing practices. |
| **Change 1 (M)** | Per-formation drilling statistics across offset wells: average ROP, mud weight used, events per 100 m and NPT. Show them as a table and bars on the Correlation page. |
| **Change 2 (M)** | Add a reservoir and pressure track per well (pore pressure, fracture gradient, mud-weight window), from Volve logs where they exist and labelled synthetic values otherwise. |
| **Change 3 (M)** | Overlay casing shoes and cement tops on the correlation view (see data item viii). |

### v. Predictive models for mud loss, stuck pipe, overpressure, torque spikes and cementing issues: 🟡 (the biggest gap)

| | |
|---|---|
| **Today** | Trained models for stuck pipe, kick and wellbore instability, each about 2 KB. A physics digital twin and a rule engine. IsolationForest and XGBoost exist in code but are never trained outside tests. |
| **Gap** | The PS names five risks. Mud loss, torque spike and cementing use heuristics. Overpressure has no hazard type at all, although the ahead-of-bit output scores it. |
| **Change 1 (M)** | Train models for mud loss and torque spike, using the same pipeline as the existing three (`modules/02_nwis_backend/ml/train_hazard_models.py`, `real_data/train_hazard_models_real.py`). |
| **Change 2 (M)** | Add overpressure as a hazard type, driven by the corrected d-exponent and kick precursors (the formula is already in the docs), and train or calibrate it. |
| **Change 3 (M)** | Cementing risk: a scored model built from casing depth, formation, mud-loss history and cement-job records (needs data item viii). |
| **Change 4 (S)** | Fit IsolationForest on normal drilling from Volve logs and save it, so the "sensor anomaly" pillar is real rather than a placeholder. Save the XGBoost fusion model the same way. |
| **Change 5 (S)** | A Model Card page: training data, leave-one-well-out scores and limits for each model. Judges ask about this. |
| **Honest framing** | Models trained on synthetic data prove the pipeline, not field accuracy. The UI and docs must say which data each model was trained on. |

### vi. Real-time alerts and recommendations: 🟡

| | |
|---|---|
| **Today** | Ahead-of-bit risk corridors, alerts with action, evidence and four-pillar confidence, and live telemetry from the physics simulator. |
| **Gap** | Nothing reads a real data stream. The PS wants a system that runs alongside eRTMAC, and there's no adapter. |
| **Change 1 (M, high value)** | An eRTMAC adapter interface plus a WITSML replay source. It replays a real Volve WITSML depth log as if it were live, through the same path a real eRTMAC feed would use. Alerts then fire on real data. |
| **Change 2 (S)** | Lead time worked out from the live ROP and the distance to the risk corridor, instead of the fixed "35–45 min" claim in the docs. |
| **Change 3 (S)** | Alert acknowledgement and an audit trail: who saw the alert, what they did, and when. The endpoints partly exist (`/api/v3/predictive/alerts/mitigate`, alert history). |

### vii. Dashboard for field and office staff: ✅

| | |
|---|---|
| **Today** | 15 pages, dark theme, the built-in docs and the landing story. |
| **Gap** | No user roles; field and office users see the same thing. The main JavaScript file is about 3 MB (850 KB compressed). |
| **Change 1 (M)** | Two simple roles. Field users get the Command Center first, with a large-text alert view. Office users get the analytics and reports pages. |
| **Change 2 (S)** | Split the 3 MB bundle so each page loads only its own code. |

---

## 2. Problem description (what teams can't do today)

| # | PS statement | Status | Change |
|:-:|---|:-:|---|
| i | See nearby wells on a map relative to the active well | ✅ | Real Volve field as a second dataset (outcome ii) |
| ii | Instant access to historical experience from offset wells | 🟡 | Larger corpus plus semantic search (outcome iii) |
| iii | Correlate drilling parameters, reservoir data, mud losses, kicks, stuck pipe, casing, cementing and formation risks | 🟡 | Per-formation drilling statistics, pressure track, casing and cement overlay (outcome iv), plus data item viii |
| iv | Proactive alerts when nearing depths or formations with known problems | 🟡 | WITSML replay through an eRTMAC adapter, and live lead time (outcome vi) |

---

## 3. Data availability (sources the PS lists)

| # | Source | What we have | Change |
|:-:|---|---|---|
| i | Well completion reports | Real Volve completion reports (in `real_data/volve`) | Extract them all into the knowledge base (S) |
| ii | Daily drilling reports | 39 synthetic DDRs, plus real Volve drilling reports | Extract the Volve DDRs as well; keep the synthetic ones labelled (S) |
| iii | Drilling and mud-logging databases | Volve WITSML logs on disk, not used as a stream | WITSML replay source (outcome vi, M) |
| iv | Historical well parameters | Synthetic | Pull per-well parameters from Volve logs (S) |
| v | Reservoir and geological data | Formation tops only | Pressure and reservoir track (outcome iv, M) |
| vi | eRTMAC data streams | None | Adapter interface and replay source; document the real eRTMAC hook-up (M) |
| vii | Trajectory and survey data | Real Volve WITSML trajectories, and minimum curvature implemented | Use them on the map, globe and correlation views (S) |
| viii | Casing, cementing and mud-programme records | ❌ **Missing**: a casing endpoint exists, but no casing, cement or mud data files | Add a casing, cement-job and mud-programme dataset per well: real from Volve reports where possible, labelled synthetic otherwise (M) |
| ix | Event records: mud losses, kicks, stuck pipe, **fishing**, **NPT** | Fishing is in the schema with no events; NPT is extracted | Add fishing events and NPT summaries per well and per formation (S) |

---

## 4. Engineering and demo risks (not in the PS, but judges notice)

| Change | Why | Effort |
|---|---|:-:|
| Keep the Render backend awake (uptime ping, or a paid tier for demo day) | A sleeping free-tier backend takes 30–60 s for the first request | S |
| Set `NWIS_DATABASE_URL` on Render | Otherwise uploads and alerts are lost when the server restarts | S |
| Make module 04's health check real | System Status can say "healthy" while the service is broken | S |
| Pin the scikit-learn version | A version change can stop the saved models from loading | S |
| Fix `frontend/.env` variable names (`VITE_M01_*` → `VITE_API_BASE`, `VITE_API_KEY`) | Local app pages stay empty until this is fixed | S |
| Remove "35–45 min lead time" claims from the docs | A judge can challenge them | S |
| Add a LICENSE file; set `main` as the default branch; clean up `old/` and the temp folders | The repo looks unfinished | S |
| Watch the full story on a typical laptop | The new shots were only checked by measurement | S |
| Treat the frontend API key as public | `VITE_API_KEY` ships in the browser bundle; real protection needs user login | M |

---

## 5. Recommended order

### Phase 1: credibility and demo safety (1–2 days)
- All S items in section 4.
- The Model Card page (outcome v, change 5).
- Precision and recall on the ingestion page (outcome i, change 2).

These carry little risk and remove the easiest criticisms.

### Phase 2: "real AI on real data" (4–6 days)
These answer the hardest judge questions:
1. The eRTMAC adapter with WITSML replay, so alerts fire on real Volve data (outcome vi).
2. Mud-loss, torque-spike and overpressure models, and the anomaly model fitted and saved (outcome v).
3. Casing, cement and mud-programme data, plus fishing and NPT events (data viii and ix). This also unlocks the cementing model and the casing overlay.

### Phase 3: depth (3–5 days)
- Per-formation drilling statistics and the pressure track (outcome iv).
- A larger corpus with semantic search (outcome iii).
- The spaCy NLP extractor (outcome i).
- Roles and bundle splitting (outcome vii).

### Rule throughout
Anything we generate is labelled synthetic in the data and the UI, and every model states what data it was trained on.

---

## 6. Open decisions

1. Start with Phase 1 and Phase 2 as listed, or a different order?
2. For casing, cementing and mud programmes: extract what we can from the Volve reports, or build a labelled synthetic set for the Assam demo wells? Extracting is more credible; synthetic is faster.
3. Upgrade the Render plan for demo day, or set up a free uptime ping instead?
