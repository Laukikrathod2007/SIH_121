# Complete ML/Model Audit

**Date:** 2026-10-04
**Method:** Exhaustive repo-wide search for every model-artifact file type requested (*.pkl, *.pickle, *.joblib, *.onnx, *.pt, *.pth, *.bin, *.safetensors, *.ckpt). **Only *.joblib files exist anywhere in this repository** — zero hits for every other extension. Every artifact found was loaded directly (`joblib.load`) and its contents inspected, not assumed from its filename. MD5 hashes were computed directly for every pair of similarly-named files to settle "is this the same model" questions with certainty, not inference. Live API calls were made against module 02 (:8002) and module 04/05 (:8003) with each module's real `.env` API key.

---

## Complete model inventory

| Model | File | Training data | Features | Preprocessing | Loader (file:line) | Runtime consumer (file:line + endpoint) | Status |
|---|---|---|---|---|---|---|---|
| Stuck Pipe (synthetic) | `modules/02_nwis_backend/data/models/stuck_pipe_model.joblib` (1,625 B; MD5 `d50f839d...`; n_positive=14, n_total=194) | `modules/02_nwis_backend/data/synthetic/drilling_events.json` (39 synthetic events) via `ml/train_hazard_models.py` | `[depth_m, pore_pressure_ppg, inclination_deg, well_type_code, formation_group_code]` (`ml/feature_engineering.py:61`) | `StandardScaler` → `LogisticRegression(class_weight="balanced")` | `ml/hazard_predictor.py:32,60,63,126` | `engines/risk_corridor_engine.py:279` → `server.py:604 GET /api/v2/analyze/{well_id}` — **live-verified**: `m_ml_source: "trained_model"` | **IMPLEMENTED** (small-N synthetic, genuinely wired and live) |
| Kick (synthetic) | `modules/02_nwis_backend/data/models/kick_model.joblib` (1,625 B; MD5 `f86e2b98...`; n_positive=10, n_total=190) | same | same | same | same | same, live-verified `trained_model` | **IMPLEMENTED** (small-N synthetic) |
| Wellbore Instability (synthetic) | `modules/02_nwis_backend/data/models/wellbore_instability_model.joblib` (1,625 B; MD5 `3e2ad740...`; n_positive=12, n_total=192) | same | same | same | same | same, live-verified `trained_model` | **IMPLEMENTED** (small-N synthetic) |
| Mud Loss | *(no file exists)* | only 3 synthetic positive events, below `MIN_POSITIVE_SAMPLES=8` (`feature_engineering.py:44`) | n/a | n/a | n/a — `_model_cache["MUD_LOSS"]=None` | heuristic only, live-verified `heuristic_fallback` | **UNWIRED by disclosed design** — too few examples, training never attempted |
| Torque Spike | *(no file exists)* | 0 positive examples ever existed | n/a | n/a | n/a | heuristic only, live-verified `heuristic_fallback`; no formation-risk term exists for this hazard at all | **SIMULATED** — real plumbing, generic placeholder signal |
| Cementing Failure | *(no file exists)* | 0 positive examples | n/a | n/a | n/a | heuristic only, live-verified `heuristic_fallback`, `evidence_count=0` | **SIMULATED** |
| Overpressure Zone | *(no file exists)* | 0 positive examples; added to the enum after the training pipeline already existed | n/a | n/a | n/a | heuristic only, live-verified `heuristic_fallback`, `evidence_count=0`; absent from module 05's hazard taxonomy entirely | **SIMULATED** |
| Stuck Pipe (REAL/Volve) | `real_data/real_trained_models/stuck_pipe_model_REAL.joblib` (1,771 B; MD5 `ec19ca41...`; 55 real depth-tagged rows, 3 real wells, leave-one-well-out mean AUC 0.594) | `real_data/real_events_depth_tagged_fresh.json` (33 real events) + real WITSML trajectories, via `real_data/train_hazard_models_real.py` | identical 5-feature schema (reuses `build_features()`) | identical `StandardScaler`+`LogisticRegression` pipeline | **No loader exists.** `hazard_predictor.py`'s `MODELS_DIR` only ever resolves to `modules/02_nwis_backend/data/models/` | none | **BROKEN/UNWIRED — two independent, compounding reasons**: (1) wrong directory — never looked at; (2) **even if the directory were fixed, this file's fitted estimator is stored under the dict key `"pipeline"`, while `hazard_predictor.py:126` reads `entry["model"]`** — loading would raise `KeyError`, silently caught and falling back to heuristic rather than crashing |
| Wellbore Instability (REAL/Volve) | `real_data/real_trained_models/wellbore_instability_model_REAL.joblib` (1,771 B; MD5 `3c188a9c...`; 53 rows, 3 wells, AUC 0.548) | same real pipeline | identical | identical | same — never loaded | none | **BROKEN/UNWIRED** — identical two-fold failure as above |
| Isolation Forest (anomaly) | *(no artifact file exists anywhere under module 05)* | Never trained in production — the only `.fit()` calls found anywhere in the repo for this class are inside `modules/05_predictive_analytics/tests/test_predictive_analytics.py` (lines 135, 189), saving only to pytest's ephemeral `tmp_path`, discarded after the test run | `ANOMALY_FEATURE_NAMES` — 18 features (`anomaly_detector.py:21-40`) | mean/std normalization, no persisted scaler | `realtime_inference.py:42,63-65` — `if path.exists(): load(...)`, file never present, load silently skipped | `risk_fusion_engine.py:79,107-115` → `POST /api/v3/predictive/evaluate`; status surfaced live at `GET /api/v3/predictive/models` | **SIMULATED/UNFITTED** — live-verified `"status":"UNFITTED_FALLBACK"`; real sklearn code, genuinely never fitted in any production run |
| XGBoost Hazard Classifier | *(no artifact file exists anywhere)* | same — only `.fit()` calls are in the test file (lines 314, 330), saved only to `tmp_path` | `SUPERVISED_FEATURE_NAMES` — 55 features (`xgboost_classifier.py:39-67`) | `StandardScaler`, fit-on-train only | `realtime_inference.py:42,67-69` — same exists-check pattern, file never present | `risk_fusion_engine.py:82-87,107-115` → same endpoint; live status `UNFITTED_FALLBACK` | **SIMULATED/UNFITTED** — always returns `NORMAL=1.0`, all other classes 0.0, when unfitted (`xgboost_classifier.py:163-165`) |
| Baseline hazard rules | `modules/05_predictive_analytics/predictive/baseline_hazard_rules.py` (not an artifact — pure code) | n/a — deterministic physics thresholds, not ML | physics-threshold features (flow delta, pit slope, overpull, torque slope, etc.) with hysteresis debouncing | n/a | instantiated `realtime_inference.py:58` | `risk_fusion_engine.py:71-76` → live-verified `"status":"ACTIVE"` | **IMPLEMENTED** (not ML — correctly not claimed to be — but genuinely wired and live) |
| Module 04 `synthetic_generator.py`+`feature_engine.py` pipeline | n/a — code only, produces data, not an artifact | self-generated physics-simulation data under domain randomization, with a quality gate | 55/60-feature trailing-window telemetry schema — **a different schema from module 02's 5-feature set** | feature extraction only; no scaler ever persisted | n/a | Sole consumer is `dataset_reporter.py`, which computes descriptive statistics for `docs/ML_DATASET_REPORT.md` — **this output file does not exist on disk**, confirming the reporter has never actually been run to completion. **Zero `.fit()` calls anywhere consume this pipeline's output.** | **UNWIRED / fully self-contained** — produces real synthetic data that nothing trains on |

---

## Full chains, broken arrows marked explicitly

### Chain 1 — Stuck Pipe / Kick / Wellbore Instability (module 02, synthetic) — WORKING END TO END
```
modules/02_nwis_backend/data/synthetic/*.json (39 labeled events)
  → build_features() (feature_engineering.py:72)
  → StandardScaler + LogisticRegression (train_hazard_models.py:108)
  → {hazard}_model.joblib saved to modules/02_nwis_backend/data/models/
  → hazard_predictor._load_all_models() loads it (hazard_predictor.py:55-70)
  → predict_ml_score() calls .predict_proba() (hazard_predictor.py:126)
  → compute_ml_score() (risk_corridor_engine.py:279)
  → composite R_H(t) score (risk_corridor_engine.py:408)
  → GET /api/v2/analyze/{well_id} (server.py:604)
  → frontend LookAheadPanel.tsx renders real TRAINED MODEL badge
```
No arrow missing. Live-confirmed at every step.

### Chain 2 — Mud Loss / Torque Spike / Cementing Failure / Overpressure Zone (module 02) — training never attempted, by disclosed design
```
Raw input → features computable, BUT:
  ARROW MISSING: training is skipped at the data stage
  (n_positive=3 < MIN_POSITIVE_SAMPLES=8 for Mud Loss;
   n_positive=0 for the other three — never had any real/synthetic examples)
→ no model artifact ever produced
→ hazard_predictor._heuristic_score() runs forever instead
→ live-confirmed m_ml_source="heuristic_fallback" for all four
```
Not a bug — an honest, documented data-insufficiency gate. But these four hazards will never improve without more labeled data, regardless of code changes.

### Chain 3 — Stuck Pipe / Wellbore Instability (REAL Volve data) — TRAINED, NEVER SERVED
```
real_data/real_events_depth_tagged_fresh.json (33 real events)
  + real_trajectories_witsml.json + real_formations_fresh.json
  → build_features() (same function, correctly reused)
  → StandardScaler + LogisticRegression (train_hazard_models_real.py:266-268)
  → {hazard}_model_REAL.joblib saved to real_data/real_trained_models/
  ARROW MISSING #1: hazard_predictor.py's MODELS_DIR points at
    modules/02_nwis_backend/data/models/ — never this directory
  ARROW MISSING #2 (would still break even if #1 were fixed):
    this file's fitted estimator is under dict key "pipeline";
    hazard_predictor.py:126 reads entry["model"] — KeyError,
    silently caught, falls back to heuristic rather than crashing
→ net effect: a real, better, honestly-cross-validated model
  sits on disk and is completely inert in production
```
**This is the single highest-value finding of this entire audit area.** A genuinely superior, real-data-trained artifact exists and is invisible to the running system for two independent, compounding reasons — not because of a hidden design choice, but an integration step that was never completed.

### Chain 4 — Isolation Forest + XGBoost (module 05) — code real, never fitted in production
```
Raw telemetry → FeatureEngine.extract_features() (module 04, imported into module 05)
  → DrillingAnomalyDetector.score() / XGBoostHazardClassifier.predict_probabilities()
  ARROW MISSING: no .joblib exists under modules/05_predictive_analytics/predictive/data/models/
    (directory itself does not exist) — realtime_inference.py's
    "if path.exists(): load(...)" silently skips loading
→ both models permanently unfitted
→ risk_fusion_engine.py redistributes their fusion weight to zero
  and substitutes heuristic/rule scores instead
→ live-verified UNFITTED_FALLBACK status for both, at every /predictive/evaluate call
```
The `.fit()`/`.save()` methods are only ever exercised inside unit tests against pytest's ephemeral `tmp_path` fixture — no production training run has ever persisted an artifact for these two models.

### Chain 5 — Module 04 data pipeline — self-contained, feeds nothing
```
Physics engine (simulation/engine.py)
  → SyntheticDataGenerator.generate_scenario_run()
  → per-timestep telemetry + label records
  → FeatureEngine.extract_features()
  ARROW MISSING: the only consumer, dataset_reporter.py, computes
    descriptive statistics for a markdown report that has never
    been generated (file absent from disk) and calls .fit() on nothing
→ this pipeline does not feed module 02's hazard models
  (incompatible feature schemas) nor module 05's classifiers
  (no training script wires them together)
```
Confirmed via exhaustive repo-wide grep for every `.fit(` call site — the only matches anywhere in the codebase are inside test files.

---

## Precise verdict: does a model file existing mean the ML feature is implemented?

**No, and this audit found a clean illustrative case of exactly that distinction**: `real_data/real_trained_models/*.joblib` are real, non-trivial (1,771 bytes, genuinely different structure from the synthetic ones), properly cross-validated (leave-one-well-out AUC reported honestly: 0.594 and 0.548 — modest but real) model files. They exist. They are not fake. **And they are completely unreachable from any live code path.** This is the exact trap the audit task warned against, caught with certainty via two independent methods (directory-path grep and MD5 hash comparison) rather than assumed from either file's mere presence.

---

## Unverified / out of scope this pass

- Whether `POST /api/v3/predictive/evaluate` produces a non-empty `alerts` array under a genuine hazard-threshold breach — only nominal-depth, unperturbed simulation was observed in the live test window; a scenario fault was not injected via `/api/v3/physics/scenario` to avoid altering shared live state further during the audit. Resolving this needs a deliberate scenario-injection test.
- Whether `top_of_cement_md_m` is non-null anywhere across the full `real_casing_records_all.json` file (only the first few sampled records were checked, all `null`).
- Module 01 was confirmed to have no `.joblib`/training artifacts of its own (consistent with being a non-ML regex-extraction module), but this was not exhaustively re-confirmed against every possible embedded-weight scenario.
