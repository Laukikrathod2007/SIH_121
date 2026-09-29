# SIH 26121 — eRTMAC-NWIS: Verified Status, Architecture, Benchmarks & Technical Reference

> **Purpose of this document:** Files `00`–`03` describe the *planned* system (problem
> decomposition, architecture, math, schemas), written before implementation. This
> document is the **as-built, as-tested** counterpart — what actually exists, what was
> actually measured, and the background knowledge needed to explain it in your own
> documentation. Where this document and `01`–`03` differ, this one reflects reality;
> the earlier docs reflect the original design intent (still valid as a spec/roadmap).
>
> Everything under **Benchmarks** was measured on this machine, in this session, against
> live code — none of it is a projection or a claim taken from documentation. Everything
> under **Known Limitations** is a real gap found by testing, not a guess.

---

> **Update, same day (2026-09-28), later session:** re-grounded in the literal PS
> text (`research/research/PROBLEM_STATEMENT.md`) and found the widest gap between
> what the PS asks for and what existed: outcome v asks for "predictive analytics
> **models**"; `compute_ml_score()` was a hand-coded heuristic standing in for one.
> This is now closed — see §3.5 and §5.9 below. The map/dashboard (outcomes ii,
> vii) and the searchable-knowledge-repository / live-streaming gaps (outcomes
> iii, vi) are still open; ML was prioritized first.

## 1. Is It Working? — Status at a Glance

| Component | Status | Evidence |
|---|---|---|
| Module 01 — Document Intelligence Pipeline | ✅ Working, production-hardened | 74-page real DDR processed end-to-end; synthetic native + scanned DDRs verified; live cloud fallback verified against real Reducto/Extend.ai keys |
| Module 02 — Backend Intelligence Core | ✅ Working, production-hardened | Full validation suite passes; 4 real bugs found by live testing and fixed; all 4 engines (including the previously-unreachable Stratigraphic Correlator) now reachable and verified |
| Module 01 ↔ Module 02 integration | ❌ **Not connected** | See §2.3 — this is the single largest honest gap; read it before writing anything that implies a live pipeline |
| Phase 4 — Frontend Cockpit | ⛔ Not started | No code exists yet |
| Phase 5 — Live Replay Simulation | ⛔ Not started | No code exists yet |
| Local OCR (Docling) accuracy on narrative text | ⚠️ Working but limited | See §5.2 — a real, measured quality gap, not a guess |

---

## 2. Architecture (As-Built)

### 2.1 Module 01 — Document Intelligence Pipeline (port 8001)

```
PDF INPUT
   │
   ├─ TIER 1: PyMuPDF — native digital text extraction (~5–25ms/page, 99%+ accuracy)
   │           Also decides per-page: is this a scanned raster image or real text?
   │
   ├─ TIER 2: Docling (IBM Research) — layout-aware OCR for scanned pages
   │           Optional dependency. Genuinely installed and working as of this
   │           session (previously it was not installed at all).
   │
   ├─ TIER 2.5: Cloud Fallback — Reducto (primary) → Extend.ai (secondary)
   │           Triggers automatically ONLY when a page's confidence falls below
   │           0.75 (configurable). Verified against live API keys — see §3.3.
   │           OFF by default (no network calls) unless an API key is configured.
   │
   ├─ TIER 3: Petroleum-domain Regex/Rules engine — entity extraction
   │           Deliberately NOT an ML/NER model. Extracts: mud properties, drilling
   │           parameters, formation tops, NPT time-ranges, narrative hazard events.
   │
   ├─ LAYER 4: Template Learner — learns DDR coordinate layouts after 3+ documents
   │           of the same operator+type, for a sub-50ms fast path on repeats.
   │
   ├─ LAYER 5: Physics Domain Validator — OISD-157 + IADC range checks
   │           Auto-repairs OCR digit-slips (e.g. "3.2 ppg" → "13.2 ppg", since
   │           8.33 ppg is the physical minimum for drilling fluid) and flags
   │           physically-impossible values no generic OCR tool would catch.
   │
   └─ OUTPUT: WITSML-mapped JSON, saved to data/output/, served via REST API
```

**API surface:** `POST /api/v1/ingest` (upload, returns job_id) → `GET /api/v1/jobs/{id}`
(poll) → `GET /api/v1/results/{doc_id}` (full JSON) + narrower views (`/events`,
`/formations`, `/npt`, `/benchmark`). All protected by `X-API-Key` except `/`, `/docs`,
`/api/v1/health`.

**Job persistence:** SQLite (`data/jobs.db`) — job status survives restarts. Not a
distributed queue; fine for the single-instance deployment this targets.

### 2.2 Module 02 — Backend Intelligence Core (port 8002)

```
ACTIVE BIT POSITION (depth d_t)
         │
         ├─ ENGINE 1: DORS — Dynamic Offset Relevance Score
         │   DORS = 0.20·S_spatial + 0.30·S_formation + 0.20·S_depth
         │         + 0.15·S_trajectory + 0.15·S_hazard
         │   → Ranks all offset wells; "nearby" ≠ "relevant" (see §5.4)
         │
         ├─ ENGINE 2: Stratigraphic Depth Correlator
         │   d_strat = TVD(d) − Top_TVD(Formation_k)
         │   Aligns offset wells at the SAME geological horizon, not the same
         │   raw depth — eliminates the "Trajectory Trap" (MD ≠ TVD for
         │   directional wells). Exposed via GET /api/v2/stratigraphic_depth_track
         │   — added this session; the engine existed but had no caller before.
         │
         ├─ ENGINE 3: Historical Risk Corridor Engine
         │   R_H(t) = 0.45·P_history + 0.35·A_sensor + 0.20·M_ML
         │   M_ML is now a REAL trained model (LogisticRegression) for hazard
         │   types with ≥8 historical examples (STUCK_PIPE, KICK,
         │   WELLBORE_INSTABILITY) — physics heuristic elsewhere. See §3.5.
         │   Clusters offset events into depth corridors; issues a 15–50m
         │   lookahead early warning. See §5.5 for why this has TWO different
         │   "risk level" numbers and why that's intentional, not a bug.
         │
         └─ ENGINE 4: 4-Pillar Confidence Evaluator
             Evidence Strength (N analog wells) + Sensor Anomaly (Z-score) +
             Data Quality (completeness %) + Audit Status (source-grounded) —
             a transparent, decoupled confidence breakdown (no single opaque
             "AI score").
```

**API surface:** `GET /api/v2/wells`, `/analyze/{well_id}`, `/offset_rank/{well_id}`,
`/corridors/{well_id}`, `/formations/{well_id}`, `/stratigraphic_depth_track/{well_id}`,
`/events`, `/telemetry/{well_id}`, `/map/wells`. All protected by `X-API-Key` except `/`,
`/docs`, `/api/v2/health`.

**Data source:** a static synthetic testbed (`data/synthetic/*.json` — 12 wells, 97
formation tops, 39 events, 3,600 telemetry records for the Assam-Arakan basin),
generated once by `generate_testbed.py`. Not live data.

### 2.3 ⚠️ The Two Modules Are Not Connected

This is worth stating plainly because it's easy to imply otherwise in a slide or a
diagram: **Module 01's extracted drilling events do not feed Module 02's analysis.**
Module 01 writes its output to `data/output/*.json`. Module 02 reads from its own,
separately-generated `data/synthetic/*.json`. There is no code anywhere in either
module that reads one and writes the other. Verified by searching both codebases for
cross-references — none exist beyond comments added this session for style
consistency.

If your documentation describes an end-to-end "upload a DDR → it becomes offset-well
intelligence" flow, that flow does not exist yet in code. What exists is two
independently-working, independently-tested systems that *could* be connected (Module
01's `DrillingEvent`/`FormationTop` schemas are structurally close to Module 02's — see
`models/schemas.py` in each) but currently are not.

---

## 3. Real Benchmarks (Measured, Not Projected)

### 3.1 Module 01 — Real Document (Utah FORGE DDR, 74 pages, native digital PDF)

| Metric | Value |
|---|---|
| Pages processed | 74 / 74 |
| Scanned (OCR) pages | 0 |
| Drilling events extracted | 17 |
| Formation tops / NPT records | 0 / 0 *(correct — this US geothermal report has neither section; verified by grepping its raw text)* |
| Overall confidence | 99.0% |
| Physics validation accuracy | 100% (0 violations) |
| Processing time | **~9.4s → ~0.3–0.7s** after fixing a real performance regression (see §4.2) |

### 3.2 Module 01 — Synthetic Indian-DDR-style document (native text, not scanned)

Built specifically because the real document above has no formation-tops/NPT/mud-table
content to test against. Exercises the exact regex patterns in
`tier3_entity_extractor.py`.

| Feature | Result |
|---|---|
| Mud weight auto-repair | OCR value 3.2 ppg (physically impossible — below 8.33 ppg freshwater floor) → auto-corrected to **13.2 ppg** |
| Formation tops | 2/2 correct (Tipam Sandstone @2980m, Girujan Clay @2200m), no duplicates |
| NPT hours | **7.0h** (5.5 + 1.5), correctly summed from structured time-range records |
| Plastic viscosity field | Extracted without crashing (this exact field previously crashed Layer 5 for the whole document — see §4.1) |

### 3.3 Module 01 — Same document, rendered as a genuinely scanned image (no text layer)

Run twice: once with cloud fallback (Reducto, live API key), once with local Docling
OCR — same input, to compare quality directly.

| | Via Reducto (cloud fallback) | Via local Docling OCR |
|---|---|---|
| Time | ~8.1s (one-time per-document upload+parse) | ~92s (first run; downloads model weights) |
| Mud weight | 4.1 ppg → auto-repaired to 14.1 ppg ✅ | 4.1 ppg → auto-repaired to 14.1 ppg ✅ |
| Formation tops | 2/2 correct ✅ | 2/2 correct ✅ |
| Drilling events | **3/3 recovered** (Kick, 2× Stuck Pipe) ✅ | **0/3 recovered** ❌ — narrative section OCR'd as gibberish |
| NPT hours | **8.25h correct** ✅ | **0.0h** ❌ |
| Self-reported confidence | 100% | "excellent" (~0.93) — **despite the failure above** |

This is the most important single benchmark in this document — see §5.2 for what it
means.

### 3.4 Module 02 — Example DORS ranking and full analysis

At `WELL-NHK-001`, depth 2500m (formation: Barail Coal-Shale):

| Hazard | Composite R_H(t) | Risk Level |
|---|---|---|
| MUD_LOSS | 0.322 | MODERATE |
| STUCK_PIPE | 0.361 | MODERATE |
| KICK | 0.145 | LOW |
| WELLBORE_INSTABILITY | 0.246 | LOW |
| TORQUE_SPIKE | 0.202 | LOW |

Top offset well: NHK-002, DORS score 0.673, distance 12.3km — ranked #1 despite not
being the closest well, because formation/trajectory/hazard match outweighed raw
distance (the whole point of DORS — see §5.4).

At depth 420m, a real early-warning case: a STUCK_PIPE corridor 38m ahead, built from
5 analog wells with CRITICAL historical severity, correctly produces:
`"38m to historical STUCK PIPE zone (HGJ-011 +4 more analog) — Condition mud prior to
entering shale..."` — this exact alert did NOT fire before a fix made this session (see
§4.3).

### 3.5 Module 02 — Hazard prediction: real trained model vs. heuristic, honestly scored

Leave-one-well-out cross-validated ROC-AUC (0.5 = random guessing, 1.0 = perfect):

| Hazard type | Historical examples | Model | Leave-one-well-out AUC |
|---|---|---|---|
| KICK | 10 | **Trained** (LogisticRegression) | **0.817** — genuine signal |
| STUCK_PIPE | 14 | **Trained** | 0.622 — barely better than random |
| WELLBORE_INSTABILITY | 12 | **Trained** | 0.606 — barely better than random |
| MUD_LOSS | 3 | Heuristic (below the 8-example training threshold) | n/a |
| TORQUE_SPIKE | 0 | Heuristic | n/a |
| CEMENTING_FAILURE | 0 | Heuristic | n/a |

Verified live via `GET /api/v2/analyze/{well_id}` that each hazard assessment
correctly reports which path produced its score
(`hazard_assessments[].m_ml_source`): MUD_LOSS/TORQUE_SPIKE show
`"heuristic_fallback"`, the other three show `"trained_model"` — never silently
one or the other. Retrain any time with `python run_server.py --train-ml`.

---

## 4. Real Bugs Found and Fixed This Session (the ones that matter for a documentation)

Full blow-by-blow is in `04_STEP_BY_STEP_IMPLEMENTATION_LOG.md` (Steps 3–7). The
headline ones, if you're summarizing:

1. **Physics auto-repair never ran on any real document** — the orchestrator never
   aggregated per-page mud properties into the document-level list the validator
   checks. Found by testing a full document, not a unit test.
2. **A silent crash disabled ALL physics validation on any document reporting Plastic
   Viscosity** (a near-universal DDR field) — an `ExtractedField` object was compared
   directly against a float, and the orchestrator's error handling swallowed it as a
   warning.
3. **Total NPT hours was silently wrong** — summed from narrative-parsed events whose
   "X hrs NPT" figure is usually in a different sentence than the event description
   once real DDR text is split on punctuation.
4. **A corridor with 5 analog wells and CRITICAL severity, 38m ahead, produced no
   alert** — the alert gate checked the diluted composite score instead of the
   corridor's own proximity assessment.
5. **Auth silently didn't activate on the very first server boot** after auto-generating
   a key — a module-import-ordering bug, reproduced identically in both modules.

None of these were visible from reading the code or from the original unit tests — all
five were found by actually running the system against realistic input and checking the
output against what it should have been.

---

## 5. Background Knowledge (for writing your documentation)

### 5.1 What WITSML is, and why it's mentioned everywhere

**WITSML** (Wellsite Information Transfer Standard Markup Language) is the oil & gas
industry's standard XML/JSON schema for exchanging drilling data (well trajectories,
mud logs, drilling reports) between operators, service companies, and software
vendors. Mapping this system's output to WITSML field names (e.g. `mudLog.mudWeight`,
`opsReport.activity`) means the extracted data could, in principle, be imported into
any WITSML-compliant system OIL already uses — it's an interoperability claim, not a
performance one. See `03_DATA_MODELS_AND_WITSML_SCHEMAS.md` for the full field mapping.

### 5.2 Why OCR confidence scores don't mean "the text is correct"

This is the most important nuance for explaining the cloud-fallback design (§3.3
above). An OCR/document-parsing engine's confidence score typically reflects how
*legible the image was* — sharp edges, consistent spacing, recognizable character
shapes — not whether the *recognized characters form correct words in context*. A
page can be scanned cleanly (high image quality → high confidence) while the OCR
engine still mis-reads a cluster of small, awkwardly-kerned words as different
characters that happen to also look plausible. That's what happened in §3.3: Docling
scored the page "excellent" while one whole section came out as gibberish. This is why
the system treats confidence as "was this scan clean," not "is this text correct" —
and why a real deployment should not assume any confidence-based automation catches
100% of OCR errors. It should still have a human-review step for anything
safety-critical, exactly as `00_PROJECT_OVERVIEW`'s "Human-in-the-Loop" section says.

### 5.3 IADC NPT Taxonomy & OISD-157

- **NPT (Non-Productive Time):** any drilling time that doesn't advance the well
  (stuck pipe, waiting on weather, equipment failure, etc.) — the single biggest
  controllable cost lever in drilling operations, which is why extracting it
  accurately from historical reports (§4, bug #3) matters operationally, not just
  as a data-quality nicety.
- **IADC NPT codes:** the International Association of Drilling Contractors' standard
  numeric classification for NPT causes (e.g. code 201 = "Lost Circulation — Total").
  Used so NPT events are comparable across operators/wells/years instead of being
  free-text narratives someone has to re-read every time.
- **OISD-157:** an Indian oil & gas safety standard (Oil Industry Safety Directorate)
  covering drilling operational practices. This system's Layer 5 physics validator
  uses OISD-adjacent physical bounds (e.g. minimum mud weight = freshwater density,
  8.33 ppg) as its "is this value even physically possible" check.

### 5.4 DORS — why "nearby" and "relevant" are different questions

A well 12km away that penetrated the exact same formation at the exact same
inclination and hit the exact same hazard is a better analog than a well 2km away
drilled through completely different rock. DORS blends five factors (spatial
proximity, formation match, depth-window overlap, trajectory/inclination similarity,
historical hazard density near this depth) specifically so a naive "wells within N km"
radius search doesn't crowd out the offset well that actually matters. See §3.4 for a
concrete example where the #1-ranked well wasn't the closest one.

### 5.5 Why the Risk Corridor Engine has two different "risk level" fields

`RiskCorridor.proximity_risk_level` answers "how physically close is the bit to
entering this specific historical hazard cluster" (a Safe / Early-Warning / Critical
state machine based purely on distance and the worst historical severity in that
corridor). `HazardRiskAssessment.risk_level` answers a different question: "blending
history, live sensor data, and a physics-based ML proxy, how risky is this hazard
*right now*." These can legitimately disagree — a corridor can be proximity-CRITICAL
while the live composite is only MODERATE if real-time sensors are quiet. Bug #4 in §4
was about making sure a proximity-CRITICAL corridor still generates an alert even when
the composite dilutes it — but the two numbers are intentionally different measures,
not one "fixed" into the other.

### 5.6 The 4-Pillar Confidence model — why it's "decoupled"

Instead of one opaque 0–100 "AI confidence" number, the system reports four
independently-computed pillars: how much historical evidence exists (N analog wells),
whether live sensors currently agree, how complete the underlying data is, and whether
the evidence traces back to an actual source document. The point is that a drilling
supervisor can see *which* pillar is weak (e.g. "only 1 analog well, but sensors are
screaming") rather than trusting or distrusting a single fused score with no way to
interrogate it.

### 5.7 Cloud document-parsing APIs (Reducto, Extend.ai) — what they are and the tradeoff

Reducto and Extend.ai are commercial document-understanding APIs: upload a file, get
back structured text/tables/layout, generally at higher accuracy than a fully local
open-source OCR stack (confirmed directly in §3.3). Using them contradicts this
project's own "100% air-gapped, DGH-sovereignty-compliant" pitch (see
`benchmarks/run_benchmark.py`'s comparison table in Module 01) — which is why the
fallback is opt-in-by-configuration, per-page (not per-document, to minimize
exposure), and fully audited (`extraction_source` tagged per page, a document-level
count of how many pages left the local boundary). This is a deliberate, documented
tradeoff between air-gapped purity and real-world accuracy, not an accidental
compromise — make that tradeoff explicit if you're presenting this to evaluators who
care about DGH data sovereignty.

### 5.8 Security posture, for a "how is this production-ready" slide

Both modules: a single shared `X-API-Key` header (auto-generated on first run,
persisted locally, never committed to git), enforced on every data/mutating endpoint
while health checks stay open for monitoring; per-key/per-IP rate limiting; CORS
restricted to a configurable allowlist (was previously wide-open in Module 02); a
global exception handler so internal errors don't leak stack traces; rotating file
logs. This is single-operator-tool-grade security (a shared secret, not per-user
auth/OAuth) — appropriate for what this actually is, not a multi-tenant SaaS product.

### 5.9 Why the hazard-prediction model is a hybrid, not "replace heuristic with ML"

The naive version of "add a real ML model" would be one model trained on all
historical events, or a flat 50/50 blend of model-and-heuristic everywhere. Neither
is honest given this data:
- **Per-hazard-type, not one model for everything** — each hazard type has a
  different number of examples (3 to 14) and, more importantly, no reason to
  share a decision boundary (what predicts a kick is not what predicts stuck
  pipe). Training one shared model would blur that.
- **A hard eligibility threshold (≥8 positive examples), not "always use the
  model"** — MUD_LOSS has 3 examples; training a model on 3 positives isn't a
  worse model, it's statistically meaningless (a model can achieve arbitrary
  training accuracy memorizing 3 points and tell you nothing about the 4th).
  Below the threshold, the original physics heuristic stays authoritative —
  and the API says so via `m_ml_source`, rather than quietly serving an
  unreliable prediction as if it were equally trustworthy.
- **The overbalance term is never learned, by design** — no historical event
  record carries the mud weight at the time it happened (only live telemetry
  does, and only for one well). A model trained on a constant "mud weight"
  column cannot discover that overbalance matters — so that physics
  relationship is applied as an explicit additive on top of *both* paths
  (model and heuristic) at inference time, where the real mud weight the
  caller supplies is actually available. This is the same "combine what data
  can teach with what physics already tells you" principle Module 01's Layer 5
  validator uses (auto-repairing OCR digit-slips using physical bounds no
  amount of training data would be needed to know).
- **Leave-one-*well*-out cross-validation, not ordinary k-fold** — rows from
  the same well share the same formations and trajectory. Ordinary k-fold
  would likely put some rows from a well in the training fold and other rows
  from the *same* well in the test fold, silently leaking information and
  inflating the reported accuracy. Holding out an entire well per fold is the
  only honest way to estimate how this generalizes to a well the model has
  never seen — which is exactly the real use case (predicting risk in the
  *active* well being drilled right now, using only *offset* wells' history).

---

## 6. Configuration Reference

| Env var | Module | Purpose | Default |
|---|---|---|---|
| `NWIS_API_KEY` | Both | Shared API key; auto-generated into `.env` if unset | *(auto-generated)* |
| `NWIS_ENV` | Both | `dev` (auto-reload) or `production` | `dev` |
| `NWIS_HOST` / `NWIS_PORT` | Both | Bind address | `0.0.0.0` / `8001` or `8002` |
| `NWIS_CORS_ORIGINS` | Both | Extra allowed origins, comma-separated | *(localhost dev ports only)* |
| `NWIS_RATE_LIMIT_MAX_REQUESTS` / `_WINDOW_SECONDS` | Both | Rate limit tuning | 20/60s (Mod 01 ingest), 60/60s (Mod 02) |
| `NWIS_REDUCTO_API_KEY` / `NWIS_EXTEND_API_KEY` | Module 01 | Cloud fallback providers | unset (fallback inert) |
| `NWIS_CLOUD_FALLBACK_CONFIDENCE_THRESHOLD` | Module 01 | Page confidence below this triggers fallback | `0.75` |
| `NWIS_CLOUD_FALLBACK_ENABLED` | Module 01 | Master kill-switch | `true` |

---

*This document reflects the system state as of 2026-09-28. If code changes after this
date, re-verify before citing specific numbers — everything here was true when
measured, not guaranteed true forever.*
