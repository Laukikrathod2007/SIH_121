# 15 — Production Readiness Roadmap

**Date:** 2026-10-05. This is a standalone engineering handover document:
read it without needing to re-run the forensic audit process this project
has already been through (`AUDIT/01`–`14`). It separates **verified
facts** (checked against running code/tests this pass), **known gaps**
(confirmed absent, not assumed), **inferred risks** (reasoned from the
architecture, not directly measured), and **external dependencies**
(genuinely outside this project's authority to resolve) — and it never
marks something complete without evidence.

**The core distinction this document exists to make explicit: a working
SIH hackathon demonstration is not the same claim as operational
readiness for real drilling decisions.** Everything in `AUDIT/14` about
demo readiness stands; nothing below should be read as walking that back.
This document is about the different, larger question of what it would
take to run this safely in a real drilling operations context.

---

## A. Current implementation status

### Fully implemented and verified (this pass + prior passes)
- All seven SIH expected outcomes have working, browser-verified
  end-to-end journeys (see `AUDIT/14` for the full matrix).
- PostgreSQL/PostGIS/pgvector/TimescaleDB as the shared source of truth
  for wells, trajectories, formations, casing, events, alerts, and
  documents, with an honest three-state contract (configured+reachable /
  not configured / configured+unreachable) verified across 287 passing
  tests this pass.
- **Fixed this pass**: `NWISOrchestrator.analyze()`'s telemetry
  correlation was well-id-blind (could silently score a hazard using a
  *different* well's sensor data). Now strictly scoped to the requested
  well end-to-end — in-memory, DB-backed, and at the API layer — verified
  live (curl + browser) and with 10 new regression tests
  (`modules/02_nwis_backend/tests/test_telemetry_scoping_regression.py`).
- Document ingestion → OCR/regex extraction → human review → PostgreSQL
  handoff → knowledge-search retrieval, with idempotent retry and no raw
  database exceptions ever reaching a user-facing field.
- Alert history read path (added Pass 6), with restart-persistence
  directly demonstrated (41 real persisted alerts survived both a backend
  process restart and, this pass, a full Docker container restart).
- UI terminology sweep: no internal module numbers, raw API paths, or
  database jargon remains on an ordinary product screen (confirmed by a
  repo-wide grep this pass found and fixed several additional instances
  beyond Pass 6's own sweep).
- **Fixed this pass, prompted by direct user observation**: a document
  that auto-passed validation (the common case) never reached the
  searchable knowledge base — `handoff_events()` was only ever wired to
  the manual-review approval route, with no path for documents that
  skipped review entirely. Fixed by auto-approving PASS documents in the
  orchestrator, running the same migration logic a human approval would.
  Verified live through the actual browser upload flow with two real
  documents. See `AUDIT/14` §4 for the full detail.
- **Fixed this pass, found while verifying the above**: `report_date`
  extracted from a source document ("15/03/2025", DD/MM/YYYY) was passed
  unparsed to a Postgres `DATE` column, silently failing the sync for
  this project's own reference sample document and any document whose
  report date has a day-of-month above 12 — and would have silently
  misparsed other dates as the wrong day/month under Postgres's default
  MDY date style, a correctness bug worse than the crash. Fixed with a
  dedicated parser trying DD/MM first (these documents' real convention),
  MM/DD as fallback, NULL (never a guess) if genuinely ambiguous. 8 new
  tests, including a live-DB regression reproducing the original failure.
- **Fixed this pass, found via a user screenshot**: the app's default
  active well on first load was a real Volve well located in the North
  Sea, so every map view opened centered on open ocean with no useful
  basemap detail. Changed to a real Upper Assam well (also this
  project's own designated live-simulation well), and changed both map
  components' default basemap style to Satellite per explicit user
  request. Verified live with screenshots showing real, recognizable
  terrain on first load.

### Partially implemented (real, working, with a known honest limitation)
- **Document extraction** is genuinely regex/rule-based for structured
  fields (Tier 3), not an NLP/NER model — the code's own docstring is
  explicit about this (`tier3_entity_extractor.py`), and this project has
  never claimed otherwise in its user-facing copy. Tier 2 layout-aware
  OCR (Docling) is a real, already-integrated capability that is simply
  **not installed** in this environment — confirmed this pass:
  `pip show docling` found it in an unrelated Python environment on this
  machine, but the backend's own interpreter does not have it
  (`python -c "import docling"` fails). `/health` already reports this
  truthfully. See §B.1 for what installing it would take.
- **Semantic knowledge search** uses a real sentence-transformers model
  (all-MiniLM-L6-v2) with a documented, tested keyword-fallback
  degradation path — but the pgvector-backed `event_embeddings` table
  (45 seeded rows, HNSW index, schema-correct) is **not yet the live
  search backend** — confirmed this pass: no application code reads from
  or writes to it outside one schema-existence test. The actual live
  search computes and caches embeddings in-process at runtime instead.
  This is schema-provisioned infrastructure for a capability that hasn't
  been wired up yet, not a broken feature.
- **Predictive ML (module 05)**: `isolation_forest_anomaly` and
  `xgboost_hazard_classifier` are `UNFITTED_FALLBACK` — confirmed this
  pass by tracing `realtime_inference.py`'s expected model directory
  (`modules/05_predictive_analytics/predictive/data/models/`), which does
  not exist. The `.joblib` files that DO exist on disk
  (`modules/02_nwis_backend/data/models/kick_model.joblib`, etc.) belong
  to a **different** ML subsystem — module 02's DORS-adjacent hazard
  models, trained on real Volve event data by
  `real_data/train_hazard_models_real.py` — not module 05's
  telemetry-feature models. The fallback path itself
  (`DrillingAnomalyDetector.score()` when unfitted) is a real, reasoned
  heuristic, not a fabricated number, and the UI discloses the unfitted
  status honestly. See §C.2 for what fitting these models would actually
  require.

### Missing / not started
- No backup or disaster-recovery tooling of any kind — confirmed this
  pass by direct search (no script, no documented procedure, no tested
  restore path).
- No load/performance testing has been run against this application at
  any point in its history that this audit trail documents.
- No centralized logging/observability (metrics, tracing, alerting) — the
  app has rotating file-based logs (`Backend/data/logs/`) and nothing
  else. See §D.3.
- No field trial, pilot deployment, or domain-expert sign-off of any
  kind — this is, and has only ever been, a hackathon prototype.

### Depends on external access
- A genuine connection to OIL's eRTMAC real-time data stream, or any of
  OIL's private operational databases/credentials — this project has
  never had, and does not claim to have, this access. Every telemetry
  value in this system is either real-but-public (Equinor Volve) or
  clearly labeled SIMULATED (the physics digital-twin). See `AUDIT/14`
  §3 for the full provenance accounting.
- Real OIL-specific training data for any model that would need to be
  fit on actual OIL field operations to be meaningfully validated for
  that context (vs. the Volve/synthetic data this project can legally and
  practically use today).

---

## B. Remaining product and SIH requirements

Mapped against the seven outcomes in `research/research/PROBLEM_STATEMENT.md`.
Only outcomes with a genuine remaining gap are listed — the rest are
"Implemented and verified" per `AUDIT/14`.

### B.1 AI/NLP/OCR-based document extraction and structuring
**Today**: deterministic regex/keyword extraction (Tier 3) is real and
tested; Tier 2 layout-aware OCR (Docling) exists in code but is not
installed in this environment.
**What's missing**: Docling itself, and — more importantly — a genuine
evaluation of whether regex-based Tier 3 extraction reaches acceptable
accuracy on documents meaningfully different from the ones it was built
against (scanned, low-quality, non-DDR/WCR formats).
**What needs to change**: `pip install -r Backend/requirements-optional.txt`
in an environment with the memory/disk headroom to do it safely (not
attempted this pass — see `AUDIT/16` §5.1 for why), then re-run
extraction against a held-out set of real documents and measure field-
level precision/recall, not just "did it not crash."
**Verification**: a documented benchmark (this project already has the
scaffolding for this — `GET /api/v1/results/{doc_id}/benchmark` exists)
run against a labeled holdout set, with numbers, not an assertion.

### B.3 Searchable historical knowledge and mitigations
**Today**: keyword + in-process semantic search, both real and tested.
**What's missing**: the pgvector-backed path is schema-ready but unused;
at today's data volume (dozens of events) this genuinely does not matter
for correctness or speed, but it will matter once real document ingestion
at scale produces thousands of events (the in-process embedding cache's
own docstring already flags this honestly: "premature engineering at
today's data volume").
**What needs to change**: wire `knowledge_search.py` to write embeddings
into `event_embeddings` on event creation and query via pgvector's HNSW
index instead of (or alongside, for the degraded-DB case) the in-process
cache, once data volume actually justifies it.
**Verification**: a load test at a realistic future data volume (hundreds
to thousands of events) comparing in-process-cache latency against
pgvector query latency.

### B.5 Predictive analytics for principal drilling hazards
**Today**: the deterministic rule engine (module 02's DORS/4-pillar, and
module 05's `BaselineHazardRules`) is real, tested, and always active
regardless of ML-model-fitting status. The ML pillars are honestly
unfitted. Module 02's own separate hazard models (`kick_model.joblib`
etc.) ARE fitted, on real Volve event data — confirmed this pass.
**What's missing**: module 05's isolation-forest/XGBoost pillars have
never been fitted in this environment.
**What needs to change**: see §C.2 — this needs a real telemetry training
set assembled by running the physics simulator through
`FeatureEngine`-shaped envelopes (not static JSON), which is a nontrivial,
properly-tested undertaking correctly out of scope for an emergency demo
pass.
**Verification**: leave-one-scenario-out cross-validation (matching the
existing leave-one-well-out pattern module 02's own training script
already uses), with precision/recall/false-positive-rate reported
honestly, not just an "it's fitted now" claim.

### B.6 Proactive alerts and recommendations
**Today**: fully implemented and verified this pass, including the read
path and restart-persistence.
**What's missing for a production (not demo) context**: configurable
proximity/lead-time thresholds are currently fixed in code, not
operator-tunable; no alert-fatigue/deduplication tuning has been
validated against anything resembling real operational alert volume.
**What needs to change**: expose threshold configuration (likely via the
existing `NWIS_*` env-var pattern, or a small settings table once that's
worth building), and test deduplication behavior under sustained
high-frequency alert conditions, not just the single labelled-scenario
tests this project has run so far.

---

## C. Data, integration, and model readiness

### C.1 OIL/eRTMAC integration boundary
**Verified fact**: the integration boundary is concrete and already
exists in a testable form — `sync_evaluation()`
(`modules/04_physics_engine/db/service.py`) validates incoming telemetry
by shape (well_id must exist in `wells`, hazard_type must resolve or is
stored as NULL rather than coerced) and writes through the same schema
regardless of whether the data originated from the physics simulator or
would originate from a real feed. **This means connecting a real eRTMAC
feed, if that access were ever granted, would not require new ingestion
code** — only a new producer calling the same `sync_evaluation()`
contract with real data shaped the same way. This is deliberately
designed this way, confirmed by reading the code, not inferred.
**External dependency**: the actual eRTMAC connection, its authentication
model, its real data contract (field names, units, update frequency) are
all unknown to this project and cannot be assumed. The `TelemetryEnvelope`
shape this system expects is this project's own invention, modeled on
what a drilling telemetry stream plausibly looks like — it has not been
validated against OIL's actual eRTMAC schema, because this project has
never seen it.

### C.2 ML training data and validation readiness
**Verified gap** (see §A): module 05's two ML pillars are unfitted.
Fitting them for real use would require:
1. A real or realistic telemetry training set — running the physics
   simulator through enough scenario variety (normal drilling + each
   labelled hazard type) to build a feature matrix via
   `modules/04_physics_engine/data_pipeline/feature_engine.py`'s
   `FeatureEngine`, not the static 3600-row JSON fixture (which is one
   well, one scenario run, and was never intended as an ML training set).
2. **False-positive/false-negative measurement**: no detector in this
   system has ever been evaluated on this metric using held-out data;
   the one existing evaluation path
   (`DrillingAnomalyDetector.evaluate_robustness()`) exists in code but
   has not been run against a real labeled dataset in this project's
   history (confirmed: no test or script in the repo calls it against
   anything but synthetic smoke-test inputs).
3. **Calibration and drift monitoring**: this system has no mechanism to
   detect when a fitted model's predictions start drifting from reality
   over time (a well-known real-world ML operations requirement with
   zero scaffolding here today).
4. **Model versioning**: `model_registry` exists in `database/schema.sql`
   but, like `event_embeddings`, is schema-provisioned and not yet
   written to by any application code — confirmed this pass.
5. **Explainability**: the rule-based pillar is inherently explainable
   (it's literally threshold logic, visible in `baseline_hazard_rules.py`);
   the ML pillars, once fitted, would need their own explainability
   story (SHAP values or similar) before a drilling engineer should trust
   a "KICK: 78% confidence" number enough to act on it in a real
   operation — this does not exist today.
**Honest framing**: none of the above is "an engineering defect that can
be fixed locally" in the way the telemetry-scoping bug was. It is a
genuine, multi-week undertaking requiring real data, careful validation
methodology, and domain-expert review of what "acceptable" false-negative
rates even mean for each hazard type — a judgment call this project has
no authority to make unilaterally.

### C.3 Data quality, provenance, and synchronization
**Verified working**: REAL/SYNTHETIC/SIMULATED/DERIVED provenance is
threaded through events (this pass added the previously-dropped
`source_type` field to the API response), wells, and alerts, and is
visible in the UI via badges. Document sync status is a closed,
honestly-labeled enum, never a raw exception.
**Known gap**: there is no automated data-quality validation pipeline —
e.g., a check that a newly-approved document's extracted depth values
are physically plausible for the well's actual total depth, or that two
documents don't silently contradict each other about the same well. The
one existing guard in this vein
(`modules/01_document_intelligence/pipeline/layer5_physics_validator.py`)
validates individual extraction internal consistency, not cross-document
or cross-source consistency.

---

## D. Production engineering and operational readiness

### D.1 Authentication, authorization, security
**Verified fact**: single shared API key (`NWIS_API_KEY`), checked via a
header, with per-route-class rate limiting. No user accounts, no
role-based access control, no audit trail of *who* took an action (the
existing `audit_log` table records *that* an action happened, with
`actor` hardcoded to `"system"` — confirmed by reading
`db/service.py::_write_audit_log()`).
**Required for production**: real user authentication (not a shared
key), role-based permissions (a field engineer approving a document vs.
an admin changing system configuration are not the same trust level),
and a genuine security review/penetration test — none of which has
happened. A shared API key is an acceptable boundary for a demo behind a
URL only judges know; it is not an acceptable boundary for a multi-user
operational tool.

### D.2 Secrets and configuration management
**Fixed this pass**: consolidated to exactly two `.env` files (was six),
with every real value documented in a matching `.env.example`, nothing
committed to git (confirmed: no `.env` file is tracked).
**Still required for production**: a real secrets manager (not a `.env`
file on disk) once this runs on infrastructure with more than one
operator who needs access, and secret rotation procedures (today,
rotating `NWIS_API_KEY` means editing one file and restarting — fine for
one deployment, not for a fleet).

### D.3 Logging, observability, monitoring, alerting
**Verified fact**: Loguru-based rotating file logs exist
(`Backend/data/logs/`), per-module log files from the pre-unification
era still get written alongside the unified process's own log (confirmed
intentional, not a bug — see `Backend/app/core/logging.py`'s own
docstring).
**Missing entirely**: structured/centralized logging (today's logs are
human-readable text, not machine-queryable), metrics (no request-latency,
error-rate, or resource-usage tracking beyond what Render's own dashboard
incidentally provides), distributed tracing, and any alerting on the
operational health of the system itself (as opposed to the drilling
alerts the system generates, which are a different thing entirely).

### D.4 Backups, disaster recovery, database restoration
**Verified gap**: no backup script, no documented restore procedure, no
disaster-recovery plan exists anywhere in this repository — confirmed by
direct search this pass. The local dev database is a Docker named volume
with no automated backup. On a real managed Postgres (once one is
actually in use — see `AUDIT/16` §3), most providers offer automated
backups, but this project has not configured, tested, or documented using
them.

### D.5 Concurrency, load testing, performance, availability
**Verified gap**: no load test has ever been run against this system
(confirmed: no load-testing tool, script, or recorded result exists in
the repo). The physics simulation loop runs at a fixed 25 Hz tick rate
per the architecture's own design intent, but how the system behaves
under concurrent multi-well simulation, concurrent document ingestion,
and concurrent API load simultaneously has never been measured.
**Risk**: this project's own measured single-process memory footprint
(~605 MB, this pass) combined with an unknown concurrency ceiling means
the actual safe operating envelope for a real multi-user deployment is
unknown, not just "needs tuning."

### D.6 Deployment and recovery procedures
**Fixed this pass**: a real, verified deployment path exists now
(`AUDIT/16_DEPLOYMENT_GUIDE.md`) for Render + Vercel, including the
honest database-hosting constraint and its real options.
**Missing**: no staging environment, no blue-green or canary deployment
strategy, no automated rollback procedure beyond "redeploy the previous
commit by hand."

### D.7 Audit trails, evidence traceability, data retention
**Verified partial**: `audit_log` exists and is written to for well-read
operations (`_write_audit_log()` in module 02's db service), but
`actor` is always `"system"` (no real user identity exists to record —
see D.1), and not every mutating operation writes an audit row (confirmed
by reading each service module's write paths — document sync, alert
sync, and event handoff do not call `_write_audit_log()` at all; only the
well-read path does). Evidence traceability for documents (source
file + page reference) is genuinely solid and tested.
**Required for production**: a consistent audit-trail policy applied to
every state-changing operation, not just reads, tied to real user
identity once D.1 is addressed, and a stated data-retention policy (how
long are uploaded documents, telemetry records, and alert history kept —
currently: indefinitely, by default, with no code path that ever deletes
anything).

### D.8 Domain-expert validation, human oversight, safe failure behavior
**Verified fact**: this system has never been reviewed by a drilling
engineer, geologist, or petroleum domain expert for correctness of its
underlying formulas, thresholds, or recommendations — confirmed by the
absence of any such review in this project's own audit history. The DORS
formula, the 4-pillar risk fusion weights, and the hazard-specific
mitigation text are all this project's own synthesis from public
drilling-engineering literature (per `research/research/`'s own
materials), not expert-validated for operational use.
**Required before any real operational use**: formal review by qualified
petroleum/drilling engineers of every formula, threshold, and
recommended-action text in the system, and an explicit human-in-the-loop
requirement (a recommendation this system produces should require a
qualified engineer's sign-off before being acted on, not be presented as
an autonomous directive) — this is partially already true in the UI
framing (recommendations, not commands) but has no enforced workflow
behind it.

### D.9 Field trials and stakeholder acceptance
**Verified fact**: zero field trials, zero pilot deployments, zero
engagement with actual OIL personnel or any other real drilling
operation, at any point in this project's history. This is, in its
entirety, a hackathon-built prototype that has been engineered carefully
and tested thoroughly against the data and constraints available in this
environment — that is a genuinely different thing from field-validated
software.

---

## E. Prioritized implementation plan

### P0 — Release blockers (must fix before ANY real operational use)
1. **Real authentication and authorization** (D.1). *Evidence*: single
   shared API key confirmed via code read. *Work*: user accounts, RBAC,
   session management. *Acceptance*: no two users share credentials; an
   action is traceable to a real identity.
2. **Domain-expert formula/threshold review** (D.8). *Evidence*: no
   review in project history. *Work*: engage qualified petroleum
   engineers to review DORS, risk-fusion weights, and every
   recommended-mitigation text. *Acceptance*: signed-off review document
   per formula/threshold, with any required corrections implemented and
   regression-tested.
3. **Backup and disaster recovery** (D.4). *Evidence*: no tooling exists.
   *Work*: automated backup schedule + a tested, timed restore drill.
   *Acceptance*: a documented restore completed from a backup within a
   defined RTO, not just "the provider probably backs it up."
4. **ML pillar fitting + validation, OR explicit UI/documentation that
   these pillars remain advisory-only indefinitely** (C.2). *Evidence*:
   confirmed unfitted this pass. *Work*: either the full training/
   validation program in §C.2, or a permanent, explicit product decision
   (not a silent gap) that these two pillars never drive an autonomous
   action without human review. *Acceptance*: either real,
   cross-validated precision/recall numbers exist and are disclosed, or
   the product explicitly, permanently frames these two signals as
   unvalidated and advisory.

### P1 — Critical capabilities (needed for a dependable operational product)
1. **Database hosting with persistence** (`AUDIT/16` §3). *Evidence*:
   Render free tier has no persistent disk; managed Postgres lacks the
   required extensions. *Work*: choose and provision a real option (self-
   hosted paid instance, or a schema adaptation for a managed provider).
   *Acceptance*: data survives a real restart in the deployed
   environment, verified live.
2. **Install and benchmark Docling (Tier 2 OCR)** (B.1). *Evidence*:
   confirmed not installed; real capability gap for scanned documents.
   *Work*: install in an environment with headroom, benchmark against a
   held-out document set. *Acceptance*: measured extraction accuracy
   improvement on scanned pages, with a before/after number.
3. **Backend memory footprint reduction** (`AUDIT/16` §5.1). *Evidence*:
   605 MB measured RSS, confirmed over Render free-tier's 512 MB.
   *Work*: make `sentence-transformers`/torch genuinely optional at
   deploy/runtime, or otherwise reduce footprint. *Acceptance*: backend
   runs stably within the target host's memory budget under realistic
   load.
4. **Centralized logging/observability** (D.3). *Evidence*: file-only
   logs today. *Work*: structured logging + a real metrics/alerting
   stack. *Acceptance*: an operator can see system health without SSHing
   into a log file.
5. **Load testing** (D.5). *Evidence*: none has ever been run.
   *Work*: realistic concurrent-user load test against the deployed
   stack. *Acceptance*: a documented safe concurrency ceiling, not a
   guess.
6. **Audit trail completeness** (D.7). *Evidence*: only well-reads are
   audited today. *Work*: extend `_write_audit_log()`-equivalent calls to
   every mutating operation. *Acceptance*: every state change is
   traceable in the audit log.

### P2 — Production hardening (security, reliability, scalability, maintainability)
1. Secrets manager instead of `.env` files (D.2).
2. Alert-threshold operator configurability (B.6).
3. pgvector wired into the live search path at real data volume (B.3).
4. Data-quality cross-document/cross-source validation (C.3).
5. Staging environment + automated rollback (D.6).
6. Data-retention policy, implemented and enforced (D.7).
7. Model versioning actually populating `model_registry` (C.2.4), model
   drift monitoring (C.2.3).

### P3 — Future enhancements (do not block core readiness)
1. Explainability tooling for the ML pillars once fitted (C.2.5).
2. Multi-basin formation-profile support beyond the existing
   `NWIS_FORMATION_PROFILE` switch (confirmed this pass: already a real,
   working env-var-driven feature for a *different* basin's vocabulary —
   extending it to more basins is additive polish, not a gap).
3. Blue-green/canary deployment strategy.
4. A genuine real-time eRTMAC integration, contingent entirely on OIL
   granting access this project does not have and cannot obtain on its
   own.

No estimates are given for P0–P3 items beyond relative ordering: several
(domain-expert review, a real eRTMAC integration) depend on access or
decisions outside this project's control, and inventing a delivery date
for them would not be a defensible estimate.

---

## F. Production-grade acceptance gates

The system may be described as **SIH-demo-ready** (already true, per
`AUDIT/14`) when: every outcome in the official problem statement has a
working, browser-verified journey; the test suite passes; the application
runs end-to-end live; and provenance/data honesty is maintained
throughout. **All of this is independently true today and does not
require anything in this document.**

The system may be described as **production-ready for real drilling
decision support** only when, additionally:

1. Every P0 item in §E is complete, with documented evidence, not a
   checklist tick.
2. A qualified petroleum/drilling engineering review has explicitly
   signed off on every formula, risk weight, and recommended-action text
   the system can surface to a user.
3. Authentication identifies real individual users, and every
   state-changing action is attributable to one of them in the audit
   trail.
4. A tested backup has been successfully restored at least once, with a
   documented recovery time.
5. Either the ML pillars have real, cross-validated, honestly-reported
   accuracy numbers appropriate to drilling-hazard-detection stakes, or
   the product permanently and explicitly frames them as advisory-only,
   never autonomous.
6. The system has been exercised under a realistic concurrent load test
   and the results are documented, not assumed.
7. At least one real field trial or pilot with actual drilling operations
   personnel has validated that the system's outputs are useful and not
   misleading in a live operational context — this is the one gate nothing
   in an engineering pass alone can satisfy; it requires OIL's or an
   equivalent operator's direct participation.

Until all seven of these are true, this system should be presented,
discussed, and used strictly as what it verifiably is: a thoroughly
engineered, honestly instrumented, and extensively tested **prototype**
— not a validated operational tool for real drilling decisions. Treating
SIH acceptance (§ above, already achieved) as equivalent to this list is
the single most important distinction this document exists to prevent.
