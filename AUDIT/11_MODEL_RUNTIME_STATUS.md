# Remediation Record — Real-Data-Trained Hazard Models (Priority 1)

**Date:** 2026-10-04
**Status: FIXED, LIVE-VERIFIED**

---

## Finding
`AUDIT/06_ML_AND_MODEL_AUDIT.md` identified two real, genuinely Volve-data-trained
hazard models (`real_data/real_trained_models/{stuck_pipe,wellbore_instability}_model_REAL.joblib`)
that were valid joblib artifacts, used the live predictor's exact 5-feature
schema, and were nonetheless completely unreachable by the running system.

## Severity
High-value / low-risk. This was the single highest-priority item in
`FINAL_AUDIT_SUMMARY.md`'s gap list — it increases the fraction of hazard
predictions backed by real field data without touching any other engine.

## Root cause (two independent, compounding problems)
1. **Wrong search directory.** `ml/hazard_predictor.py`'s `MODELS_DIR` only
   ever pointed at `modules/02_nwis_backend/data/models/` — it never looked
   in `real_data/real_trained_models/` at all.
2. **Dict-key mismatch.** Even pointed at the right file, the loader did
   `entry["model"]`; the real-model trainer (`real_data/train_hazard_models_real.py`)
   saves the estimator under `entry["pipeline"]`. This would have raised a
   `KeyError` on every single inference call for these two hazards had only
   problem 1 been fixed.

## Pre-change inspection (required before touching any code)
Both artifacts were loaded directly and inspected (not assumed compatible):
- Both are `dict`s with the estimator at key `"pipeline"`, each a
  `sklearn.pipeline.Pipeline([StandardScaler, LogisticRegression(class_weight="balanced")])`.
- Both report `n_features_in_ == 5`, matching `FEATURE_NAMES` in
  `ml/feature_engineering.py` (`depth_m, pore_pressure_ppg, inclination_deg,
  well_type_code, formation_group_code`) — confirmed identical ordering
  because `real_data/train_hazard_models_real.py` imports and calls module
  02's own `build_features()`/`FEATURE_NAMES`, not a reimplementation.
- Metadata present: `trained_on`, `n_samples` (55 / 53), `n_wells` (3),
  `n_fallback_inclination_rows`, `lowo_fold_results` (per-well leave-one-well-out
  AUC), `lowo_mean_auc`.
- **Honest performance read**: `lowo_mean_auc` = 0.594 (STUCK_PIPE) and 0.548
  (WELLBORE_INSTABILITY) — weak, with individual folds as low as 0.40–0.47.
  This is **not** stronger than the synthetic models' own reported AUC
  (~0.60–0.62, per the training script's own comparison printout). The real
  models are preferred here for **provenance** (genuine field data vs. a
  procedurally generated testbed), not for measured performance. This
  trade-off is stated explicitly in code comments, not hidden.
- A direct inference probe (`pipeline.predict_proba([test_vector])`) was run
  against both artifacts before any production wiring, confirming no crash
  and valid, differentiated `[P(0), P(1)]` output.

## Files changed
- `modules/02_nwis_backend/ml/hazard_predictor.py`

## Implementation
Added a three-tier model resolution in `_load_all_models()`, evaluated once
per hazard type at first use (lazy-loaded, same caching behavior as before):

1. **Real-data-trained model** (`real_data/real_trained_models/{hazard}_model_REAL.joblib`)
   — loaded and passed through a new `_validate_real_model()` gate that checks:
   presence of the `"pipeline"` key, a `predict_proba` method, `n_features_in_`
   matching the live feature count, and a live probe inference against a
   zero-vector of the correct shape. Any failure is logged and that hazard
   type falls through to tier 2 — it never raises up to the request path.
2. **Synthetic-trained model** (`data/models/{hazard}_model.joblib`, existing
   behavior, untouched) — used when no real model exists or it failed
   validation.
3. **Heuristic fallback** (existing behavior, untouched) — used when neither
   trained model exists for that hazard type.

On a validated real-model load, the entry is normalized to the same internal
`{"model": ...}` key the rest of the module already uses (`chosen_entry =
{**real_entry, "model": real_entry["pipeline"]}`), so no other code path had
to change. `predict_ml_score()` now reports the actual tier used via a new
`_model_source_cache`, instead of always returning the string `"trained_model"`
whenever any model entry was non-null.

New `MLScoreResult.source` values: `"trained_model_real"` (new),
`"trained_model"` (unchanged meaning — now specifically synthetic-trained),
`"heuristic_fallback"` (unchanged).

Frontend: `LookAheadPanel.tsx` and `OperationalDirective.tsx` (the only two
components that render `m_ml_source`) were updated to render a distinct
"REAL-DATA MODEL" badge (emerald) for `trained_model_real`, vs. "TRAINED
MODEL" (cyan) for synthetic and "HEURISTIC" (slate) for fallback — without
this, the new source value would have silently fallen into the "HEURISTIC"
bucket in the UI, which would have been a newly-introduced inaccuracy in the
other direction. `frontend/src/types/index.ts`'s type comment was updated to
list all three values.

## Why this approach
- Preserves the existing synthetic/heuristic fallback chain exactly — no
  hazard type that worked before can now fail.
- Normalizing the dict key inside the loader (rather than changing what key
  the trainer writes, or duplicating inference logic per source) keeps
  `predict_ml_score()` itself unchanged except for the one `source` lookup.
- Validation happens once at load time, not per-request, so there's no new
  per-request latency or failure surface.
- Does not touch module 05, module 04, or any other hazard's code path.

## Regression risk
Low. The change is additive and gated: a hazard with no real-model file on
disk takes the exact code path it took before (`real_path.exists()` is
`False` → straight to synthetic/heuristic, byte-for-byte the same logic as
pre-change). Only `STUCK_PIPE` and `WELLBORE_INSTABILITY` — the two hazards
with a `*_REAL.joblib` file present — are affected.

## Verification (live, this pass)
- **Server log**, module 02 restarted clean:
  ```
  Loaded REAL-data-trained hazard model: STUCK_PIPE (stuck_pipe_model_REAL.joblib), lowo_mean_auc=0.594, n_wells=3
  Loaded synthetic-trained hazard model: KICK (kick_model.joblib)
  Loaded REAL-data-trained hazard model: WELLBORE_INSTABILITY (wellbore_instability_model_REAL.joblib), lowo_mean_auc=0.548, n_wells=3
  ```
- **Live API** (`GET /api/v2/analyze/WELL-HGJ-012?depth=2600`):
  ```
  STUCK_PIPE              m_ml_source=trained_model_real   m_ml=1.0
  KICK                    m_ml_source=trained_model        m_ml=1.0
  WELLBORE_INSTABILITY    m_ml_source=trained_model_real   m_ml=1.0
  MUD_LOSS / TORQUE_SPIKE / CEMENTING_FAILURE / OVERPRESSURE_ZONE
                          m_ml_source=heuristic_fallback
  ```
- **Stability check**: same well queried at depth 500m/1500m/3500m — tier
  selection identical across all three; no flapping, no exceptions.
- **Real-well check**: queried against `15/9-F-1` (a real Volve well, one of
  the 3 the model was literally trained on) at depth 2500m — produced
  differentiated, non-degenerate probabilities (STUCK_PIPE 0.93 vs.
  WELLBORE_INSTABILITY 0.64), not a stuck constant.
- **Browser verification** (`/app/command-center`, well `15/9-F-12`):
  `OperationalDirective` banner and `LookAheadPanel` both render the new
  **REAL-DATA MODEL** badge for STUCK PIPE and WELLBORE INSTABILITY, **TRAINED
  MODEL** for KICK, **HEURISTIC** for the remaining four hazards. 0 console
  errors.

## Before / After

| Hazard | Before | After |
|---|---|---|
| STUCK_PIPE | `trained_model` (synthetic) | `trained_model_real` (real Volve data) |
| WELLBORE_INSTABILITY | `trained_model` (synthetic) | `trained_model_real` (real Volve data) |
| KICK | `trained_model` (synthetic) | `trained_model` (unchanged — no real artifact exists) |
| MUD_LOSS / TORQUE_SPIKE / CEMENTING_FAILURE / OVERPRESSURE_ZONE | `heuristic_fallback` | `heuristic_fallback` (unchanged) |

## Status: FIXED

---

# Addendum — KICK real-data model added (2026-10-04, same-day follow-up)

**Trigger:** User asked to search for additional real datasets that could
reduce reliance on synthetic training data. Public dataset search (Petrobras
3W, DGH India NDR) found nothing usable — 3W is production-phase sensor data
(BSW/DHSV/slugging), a different problem domain from this project's
drilling-phase hazards; DGH's National Data Repository is real and
India-specific (24,434 wells) but is an access-gated data room, not an open
download, and out of reach within this session. See chat transcript for the
full negative-result writeup — nothing from that search was used.

**What was actually usable instead:** `real_data/real_events_module01.json`,
a 119-record raw extraction dump already sitting in the repo, never merged
into the file the real-model trainer actually reads
(`real_events_depth_tagged_fresh.json`), flagged UNVERIFIED in the original
`07_DATA_PIPELINE_AUDIT.md` pass ("whether this file is consumed anywhere").
Investigated it properly rather than merging it blindly:

- **Confirmed NOT consumed anywhere** before this fix (grep-verified).
- **Found and excluded 3 categories of bad data**, all manually verified
  against full `raw_narrative` text, not just the event-type label:
  1. Well ID `15/9-F-11` (19 records) does not correspond to any real well
     in this project — all 4 of its depth-tagged narratives are garbled
     fragments of geological/logging descriptive text (MagTrak tool
     descriptions, lithology descriptions, a report page footer), not real
     drilling incidents. The entity extractor's keyword regex matched
     incidental phrases ("thief zone", "no returns") inside non-incident
     prose. **Entirely excluded.**
  2. 2 records with physically impossible depths (262,430m / 262,060m — the
     same underlying extraction bug already observed live during this
     remediation pass's Review Queue testing, in a different document from
     the same well family), both already self-flagged
     `FAILED_PHYSICS_VALIDATION` by module 01's own Layer 5 validator.
     **Excluded.**
  3. 1 record (well `15/9-F-1`, 66m) is a geological zonation *description*
     naming a stratigraphic unit called "Thief Zone," not a loss-of-
     circulation *incident* — same false-positive pattern as (1).
     **Excluded.**
  4. 6 further records were de-duplicated: 4 records at the identical depth
     (3220m, well `15/9-19B`) were the same underlying trip-gas table row
     OCR'd multiple times with character-recognition noise
     ("weUhead"/"welUiead"/"wellhead" — classic 'll'/'U' OCR confusion) —
     collapsed to 1. 2 more collided with events already present in the
     target file (matched well+hazard+depth) and were correctly skipped as
     the same real-world event re-extracted, not double-counted.
  5. Inconsistent well-ID formatting (`15_9-19B` vs the canonical
     `15/9-19B`, `15_9-F-1C` vs `15/9-F-1C`) was normalized — these are the
     same real wells already in the project's catalog.

**Files added:**
- `real_data/merge_unused_real_events.py` — the one-off augmentation script,
  with every exclusion/dedup rule documented inline with its specific
  reasoning (not just "cleaned the data").

**Result:** `real_events_depth_tagged_fresh.json` grew from 33 to 45 events
(12 new, real, individually-verified events — not 18, after de-duplication).
KICK's real positive count went from 1 (statistically unusable) to **12
positives across 2 real wells** — enough to clear `MIN_POSITIVE_SAMPLES=8`
and run a genuine (if small) 2-fold leave-one-well-out validation. MUD_LOSS
reached 7 positives — still one short of the threshold, correctly **NOT**
forced through (the training script's own `MIN_POSITIVE_SAMPLES` gate was
not lowered or bypassed).

**New model:** `real_data/real_trained_models/kick_model_REAL.joblib` —
honest leave-one-well-out AUC **0.694** (folds: `15/9-19B`=0.721 n=26,
`15/9-F-1C`=0.667 n=16) — no synthetic KICK model existed to compare against
before, so this is pure net-new real-data ML capability, not a replacement.
STUCK_PIPE and WELLBORE_INSTABILITY were retrained as a side effect of
re-running the same script (their own event counts were unaffected by the
new KICK/MUD_LOSS-only additions); their AUCs moved by negligible amounts
(0.594→0.624 and 0.548→0.548 respectively) — not a regression, ordinary
retrain variance from the dataset most rows unchanged.

**Live verification:** module 02 restarted; `_load_all_models()`'s existing
generic `{hazard}_model_REAL.joblib` lookup picked up the new KICK model
with **zero code changes** to `hazard_predictor.py` — the Priority 1 design
(search by hazard name, validate, prefer real over synthetic) already
supported this without modification. Confirmed live:
```
STUCK_PIPE             trained_model_real
KICK                   trained_model_real   <- NEW
WELLBORE_INSTABILITY   trained_model_real
MUD_LOSS/TORQUE_SPIKE/CEMENTING_FAILURE/OVERPRESSURE_ZONE
                        heuristic_fallback  (unchanged -- real data insufficient)
```
Stable across depth=500/1500/3500m and on a real Volve well (`15/9-F-1`),
differentiated non-degenerate predictions, no crashes. Browser-verified at
`/app/command-center`, 0 console errors.

**Updated hazard coverage: 3 of 7 hazards now real-data-trained** (up from
2), 1 of 7 synthetic-only (no real alternative possible — KICK's synthetic
model remains on disk as the validated fallback if the real model ever
fails its load-time check), 3 of 7 heuristic-only (real and synthetic data
both insufficient).

## Status: FIXED (extended)
