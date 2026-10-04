# Risk Architecture Decision — Module 02 vs Module 05 (Priority 3)

**Date:** 2026-10-04
**Status: DECIDED (Option A) — DOCUMENTED, LABELED IN UI. No engine code changed.**

---

## Finding (from `09_ARCHITECTURE_AND_DEAD_CODE.md`)
Two independent, real, working risk-scoring systems exist in this codebase
for overlapping drilling hazards:

```
Module 02                          Module 04/05
→ ml/hazard_predictor.py           → predictive/risk_fusion_engine.py
→ engines/risk_corridor_engine.py  → predictive/baseline_hazard_rules.py
→ DORS / 4-Pillar Confidence       → anomaly_detector.py + xgboost_classifier.py
→ Command Center, Dashboard,       → Risk & Prediction page (/app/risk)
  Geological Correlation
```

They use genuinely different taxonomies, formulas, and weighting:

| | Module 02 (`risk_corridor_engine.py`) | Module 04/05 (`risk_fusion_engine.py`) |
|---|---|---|
| Formula | `R_H = 0.45·P_history + 0.35·A_sensor + 0.20·M_ML` | `w_rules·R + w_anomaly·A + w_ml·M + w_hist·H` (0.35/0.20/0.30/0.15) |
| Risk levels | LOW (<0.25) / MODERATE (<0.50) / HIGH (<0.75) / CRITICAL | LOW (<0.35) / MEDIUM (<0.70) / HIGH |
| ML source | Per-hazard LogisticRegression (now incl. real-data-trained, see `11_MODEL_RUNTIME_STATUS.md`) or heuristic | Isolation Forest + 6-class XGBoost (both honestly `UNFITTED_FALLBACK` — see `06_ML_AND_MODEL_AUDIT.md`) |
| Historical evidence | Offset-well event corridors (DORS-ranked) | Module 4 geology/stratigraphic coordinate ξ |
| Hazard taxonomy | `HazardType` enum (7 types, incl. MUD_LOSS, CEMENTING_FAILURE) | 5 hazard keys (incl. WASHOUT, TORQUE_DRAG — not identical names) |

## Investigation performed before deciding

1. **Traced every frontend consumer of both engines.** Module 02's
   `hazard_assessments` is consumed exclusively by `LookAheadPanel.tsx`,
   `OperationalDirective.tsx`, `KPIStrip.tsx` (all on Command Center) and
   `DashboardPage.tsx`. Module 05's `activeRisk` (from `AppContext`) is
   consumed exclusively by `RiskPredictionPage.tsx` (`/app/risk`) and
   `WellCutawayCockpit.tsx`.
2. **Confirmed no code path combines them.** A repo-wide search for any
   expression mixing `hazard_assessments` and `fused_hazard_scores` /
   `activeRisk` / `m_ml` found nothing — the two numbers are never summed,
   averaged, or displayed as if they were one score anywhere in the current
   codebase. This is better than the audit's "unreconciled" framing implied
   at first glance: they are not silently colliding today, they are simply
   rendered on two different pages with no cross-reference between them.
3. **Checked whether this separation looks intentional.** Module 02's
   engine is wired into the historical-offset-evidence workflow (DORS
   ranking, stratigraphic correlation, 4-Pillar Confidence) — it answers
   "what do nearby wells' history say about this depth." Module 05's engine
   is wired into the physics-simulation/live-telemetry workflow
   (`risk_fusion_engine.py` imports `anomaly_detector`, `xgboost_classifier`
   — both consume simulated real-time sensor streams, not offset-well
   history). These genuinely are two different *kinds* of risk assessment
   answering two different questions, built against two different data
   sources, not an accidental duplicate of the same thing.

## Decision: OPTION A — keep independent, explicitly define responsibilities

**Module 02 (`/app/command-center`, Dashboard, `/app/correlation`) answers:**
*"Given this well's depth and position, what do historical offset wells and
geology suggest about hazard likelihood?"* — a spatial/historical-evidence
engine.

**Module 05 (`/app/risk`) answers:** *"Given the live (simulated) sensor
telemetry right now, what does real-time anomaly detection and physics
coupling suggest?"* — a live-signal-fusion engine.

Neither was merged into the other. Neither's formula, weights, or thresholds
were changed. No "unified risk score" was created.

### Why not Option B (reconciliation layer)
A translation layer would require either (a) inventing a mapping between two
taxonomies that don't fully overlap (e.g. module 05 has no
CEMENTING_FAILURE/OVERPRESSURE_ZONE equivalent, module 02 has no
WASHOUT/TORQUE_DRAG equivalent) or (b) averaging two scores built from
incompatible inputs (one historical/spatial, one live-telemetry), which the
spec explicitly prohibits ("do not create a fake 'unified risk score'").
Neither is honest engineering within this pass's scope.

### Why not Option C (literal side-by-side view)
The two engines already serve genuinely different user questions at
different points in the workflow (pre-spud offset analysis vs. live
monitoring) — forcing them onto one screen would conflate two different
analyses rather than clarify them, and was not requested by any verified
user journey in the E2E audit.

## What changed (UI labeling only, no engine logic)
1. `RiskPredictionPage.tsx` header now states (visible, not just a tooltip):
   *"Independent engine from Command Center's hazard cards (module 02's
   DORS/4-Pillar scoring) — different formula, different taxonomy,
   deliberately not reconciled (hover for details)."*
2. `LookAheadPanel.tsx`'s header now carries a small `module 02` tag with a
   tooltip pointing to this document, so a user moving from Command Center
   to Risk & Prediction (or vice versa) has an explicit signal that they are
   looking at two different engines, not a discrepancy or bug.

## Files changed
- `frontend/src/pages/RiskPredictionPage.tsx`
- `frontend/src/components/commandcenter/LookAheadPanel.tsx`

## Regression risk
None — text/label-only change, no data flow, no formula, no API contract
touched.

## Verification
Both components render without new console errors (browser-verified at
`/app/risk` and `/app/command-center`, see `11_FINAL_RUNTIME_VERIFICATION.md`).

## Status: DECIDED AND DOCUMENTED (Option A). Carried forward as a known,
intentional architectural property, not a defect — a future phase could
revisit Option B if the two hazard taxonomies are ever unified by product
decision, but that is explicitly out of scope here.
