# SIH 26121 — eRTMAC-NWIS: Step-by-Step Implementation Log

This document tracks all implementation steps, architecture setups, file creations, algorithmic validations, and frontend/backend milestones.

---

## Milestone Tracking Dashboard

| Step / Phase | Description | Status | Key Deliverables |
|---|---|---|---|
| **Phase 0** | **Domain Research & PS Deconstruction** | Completed | Full deconstruction of PS 26121, OIL eRTMAC alignment, WITSML compliance, 5 risk families defined. |
| **Phase 1** | **Documentation & Presentation Logger Suite** | Completed | Generated complete logger documentation suite (`00` to `07`) in `logger/` folder. |
| **Phase 1.5** | **Research Convergence & Evaluator Roadmap** | Completed | Cross-audited 69-file domain corpus vs logger suite vs live internet validation; created `08_EVALUATOR_ROADMAP_AND_FINAL_CONVERGENCE.md` & `EVALUATOR_ROADMAP_AND_FINAL_CONCLUSION.md`. |
| **Module 01** | **Document Intelligence Pipeline (6-Layer OCR + NER)** | ✅ COMPLETE + HARDENED | `modules/01_document_intelligence/` — PyMuPDF + Docling (optional) + regex/rules NER + Template Learner + Physics Validator + WITSML JSON. FastAPI server at port 8001. Production-hardening pass (Step 3 below) fixed several correctness bugs and replaced the in-memory job store with a persistent one. |
| **Phase 2** | **Data Synthesis — Assam-Arakan Basin Testbed** | ✅ COMPLETE | `modules/02_nwis_backend/data/synthetic/` — 12 wells, 97 formation tops, 39 drilling events, 3,600 1-Hz telemetry records. |
| **Phase 3** | **Backend Intelligence Core (DORS + Risk Corridors + 4-Pillar)** | ✅ COMPLETE | `modules/02_nwis_backend/` — DORS Engine, Stratigraphic Correlator, Risk Corridor Engine, FastAPI server at port 8002. |
| **Phase 4** | **Operational Cockpit Frontend (React + TS + Tailwind)** | 🔲 NEXT | Interactive GIS Map, Stratigraphic Depth Track, Telemetry Strips, Evidence Modal, AI Copilot. |
| **Phase 5** | **Live Replay Simulation & Validation Suite** | 🔲 Pending | Interactive depth scrubber, anomaly triggers, end-to-end testing and benchmarking. |

---

## Detailed Implementation Log

### Step 1: Initialization & Context Structuring
* **Date & Time:** 2026-09-25
* **Action:** Created structured `logger/` directory with core reference documents (`00` to `07`).

### Step 2: Cross-Audit, Internet Verification & Evaluator Convergence
* **Date & Time:** 2026-09-27
* **Action:** 
  - Analyzed line-by-line all files across `research/research/` (11 tracks, 69 files) and `logger/` (8 files).
  - Validated claims via internet searches on Oil India's eRTMAC 2.0 tender, WITSML 2.0 Risk Objects, DGH NDR data sovereignty, and international drilling benchmarks.
  - Authored comprehensive comparative evaluation guide: [08_EVALUATOR_ROADMAP_AND_FINAL_CONVERGENCE.md](file:///c:/Users/LAUKIK/Desktop/SIH121/logger/08_EVALUATOR_ROADMAP_AND_FINAL_CONVERGENCE.md) and [EVALUATOR_ROADMAP_AND_FINAL_CONCLUSION.md](file:///c:/Users/LAUKIK/Desktop/SIH121/EVALUATOR_ROADMAP_AND_FINAL_CONCLUSION.md).
  - Defined the "Bring Your Own Data" (BYOD) Adapter Architecture and the 7 Game-Changing Innovations to outshine competing teams.

### Step 3: Module 01 Production-Hardening Pass (Document Intelligence)
* **Date & Time:** 2026-09-27
* **Action:** Module 01 was functionally complete but had never been run end-to-end
  outside its own author's environment. Audited it file-by-file, ran it against
  real PDFs (the Utah FORGE DDR, a non-drilling research PDF, and a synthetic
  scanned-image PDF), and fixed what broke or gave silently wrong answers:
  - **Crash on Windows:** `run_server.py --test/--demo` and `benchmarks/run_benchmark.py`
    crashed with `UnicodeEncodeError` printing `✓`/`✗` to a legacy cp1252 console.
    Fixed by reconfiguring stdout/stderr to UTF-8 at each CLI entry point.
  - **Schema footgun → masked validator bug:** `MudProperties`, `FormationTop`,
    `DrillingEvent`, and `DocumentExtractionResult` each exposed convenience
    properties (`density_ppg`, `top_depth_m`, `formation_tops`, …) that shadow
    their real Pydantic field names. Because Pydantic silently drops unknown
    constructor kwargs by default, `validate_module01.py`'s own physics-validator
    test was passing vacuously — none of its `density_ppg=...`/`formation_tops=...`
    constructor kwargs were actually being stored. Added `extra="forbid"` to all
    four models (loud failure instead of silent data loss) and fixed the test to
    construct correctly. **Layer 5's OCR-slip auto-repair and fuzzy formation-name
    normalization are now genuinely verified, not just reported as passing.**
  - **Corrupt/unreadable PDFs silently reported as "COMPLETED":** `process_document`
    returned an empty-but-valid result for a missing/corrupt/encrypted/zero-page
    PDF instead of raising. The background ingestion task then marked the job
    `COMPLETED` with 0 events instead of `FAILED`. Now raises explicitly; verified
    via a live `POST /ingest` with a non-PDF file → job correctly reports `FAILED`
    with a clear error message.
  - **In-memory-only job store → SQLite-backed `api/job_store.py`:** job status
    previously lived in a plain dict and evaporated on every restart (the code
    even said so in its own docstring). Verified via a real restart: job history
    and status now survive a full process kill/restart, and 5 concurrent uploads
    complete correctly with independent status tracking.
  - **Misleading health check:** `/api/v1/health` reported `"degraded"` whenever
    spaCy or Docling weren't installed — but Tier 3 entity extraction is pure
    regex and never uses spaCy, and Docling's absence is a documented graceful-
    degradation path (native digital PDFs are unaffected). Rewrote the check to
    only fail on PyMuPDF (the actual hard dependency) and label the rest as
    optional/informational.
  - **Scanned-page detection only sampled page 0:** a document with a text cover
    page followed by scanned body pages would never trigger OCR for the rest of
    the document. Now checks every page (cheap heuristic, not real OCR).
  - **Scanned-page content duplication / silent data loss:** every scanned page
    in a multi-page document was reusing the *same* whole-document Docling
    markdown (or, if Docling wasn't installed, silently empty text with no
    indication anything was missed). `tier2_ocr_engine.py` now splits Docling's
    output per page where the installed version supports it, and — critically —
    a page with genuinely zero extractable text and no OCR engine available now
    gets an explicit "no OCR engine" marker and 0.0 confidence instead of an
    empty string. This surfaced a second bug: the confidence aggregator used
    `page_confidence or 0.90`, and in Python `0.0 or 0.90 == 0.90` — a
    legitimately unreadable page was silently reported as 90% confident.
    Verified with a synthetic image-only PDF: `overall_confidence` now correctly
    reports `0.0%` instead of a false `99.0%`.
  - Added a global FastAPI exception handler (no internal stack traces leaked to
    clients), rotating file logging (`data/logs/`), a `NWIS_ENV=production` flag
    to disable dev auto-reload, and a `.gitignore` for the module's generated
    data (job DB, uploads, output, templates, logs).
  - Re-ran `validate_module01.py` end-to-end after every change — all 6 layers
    plus the real-document test pass genuinely, not just nominally.
* **Not done in this pass (flagged, not silent):** no OCR engine is installed in
  this environment, so scanned/raster PDFs still can't be read without running
  `pip install docling` (~400MB model download) — the pipeline now says so
  explicitly instead of pretending otherwise. Phase 4 (frontend cockpit) is
  still not started; this pass was scoped to Module 01 only.

### Step 4: Benchmark Verification + Generalization Test (Second Real-World Document)
* **Date & Time:** 2026-09-28
* **Action:** Ran `benchmarks/run_benchmark.py` against the real Utah FORGE DDR to get
  final verified numbers, then specifically tested whether the pipeline "works the
  same for other such documents" — the real PDF on hand is a US DOE geothermal well
  report with no formation-tops or NPT sections at all (confirmed by grepping its
  raw text: zero hits for "Formation", "NPT", "Sandstone", etc.), so it never
  exercises three of the system's headline features. Built a second, realistic
  Indian-Oil-DDR-style synthetic PDF (`data/sample_docs/synthetic_oil_india_ddr.pdf`)
  with a mud-properties table (including an OCR-slip-style "3.2 ppg" instead of
  "13.2 ppg"), a formation-tops section, and an operations-remarks narrative with
  NPT time ranges, and ran it through the full pipeline. This surfaced three more
  real, previously-hidden bugs — none visible from the Utah FORGE document alone:
  - **Physics auto-repair never ran on any real document.** `run_physics_validation`
    validates `result.mud_properties` (the document-level list field), but the
    orchestrator only ever populated `all_drilling_events`/`all_formation_tops`/
    `all_npt_records` — nothing aggregated per-page mud properties into that list.
    The flagship "corrects OCR digit-slips" feature was dead code in production.
    Fixed: orchestrator now aggregates `all_mud_properties` the same way as the
    other entity types.
  - **A silent crash on a near-universal DDR field.** `plastic_viscosity_cp` has no
    float-unwrapping convenience property (unlike `density_ppg`/`viscosity_sec`), so
    `validate_field()` received a raw `ExtractedField` and raised
    `'<' not supported between instances of 'ExtractedField' and 'float'` — caught
    by the orchestrator's broad exception handler and logged as a warning only.
    Net effect: Layer 5 silently no-op'd for the **entire document** whenever
    Plastic Viscosity (a standard field in virtually every real DDR mud table) was
    present. Fixed at the root cause: `validate_field()` in `models/domain_rules.py`
    now defensively unwraps any `ExtractedField` passed to it, protecting every
    current and future call site, not just this one.
  - **`total_npt_hours` was silently wrong.** It summed `DrillingEvent.npt_hours`,
    which is populated by per-sentence narrative parsing — but a DDR narrative's
    event description ("Stuck Pipe — worked to free string") and its "5.5 hrs NPT"
    figure routinely land in different sentences once split on periods/semicolons,
    so `npt_hours` on narrative events is `None` far more often than not. The
    structured `NPTRecord` list (built from explicit HH:MM–HH:MM time ranges) had
    the correct figures the whole time. Switched the document-level total to sum
    from `all_npt_records` instead; kept the narrative-event check as a secondary,
    best-effort validation only.
  - **Duplicate formation tops.** `ASSAM_ARAKAN_FORMATIONS` lists both full names
    and abbreviations ("Tipam Sandstone" and "TIPAM"); a single mention matched
    both list entries and produced two records for the same physical top. Fixed by
    processing longer names first and skipping a match whose depth-figure span was
    already attributed to a fuller name.
  - Re-verified end-to-end after all four fixes: the synthetic DDR now correctly
    shows the mud-weight auto-repair (3.2 → 13.2 ppg), exactly 2 deduplicated
    formation tops, `total_npt_hours = 7.0` (5.5 + 1.5), zero crashes. Re-ran
    `validate_module01.py` (updated its NPT test case to match the corrected
    source-of-truth) and `run_server.py --test` against the real Utah FORGE PDF —
    both still pass.
  - Fixed a factual inaccuracy in the benchmark tool's "Evaluator Statement" that
    claimed spaCy was used for NER (Tier 3 is pure regex/rules; spaCy has never
    been part of the extraction path — see Step 3).
* **Verified benchmark — Utah FORGE DDR (`Drilling Summary Well 16A(78)-32.pdf`),**
  via `benchmarks/run_benchmark.py`:

  | Metric | Value |
  |---|---|
  | Pages processed | 74 / 74 |
  | Scanned (OCR) pages | 0 |
  | Drilling events extracted | 17 |
  | Formation tops | 0 *(correct — this document has none, see above)* |
  | NPT records | 0 *(correct — same reason)* |
  | Overall confidence | 99.0% |
  | Physics validation accuracy | 100% |
  | Physics violations caught | 0 |
  | Processing speed | ~30–40 ms/page |

  Formation-tops/NPT/mud-repair are verified working on the synthetic Indian-DDR-
  style document instead (above), since the real document on hand doesn't contain
  that kind of content.
* **Still open:** only one real-world document has been tested end-to-end; the
  synthetic document, while built to match the actual regex patterns in
  `tier3_entity_extractor.py`, is not a substitute for a second *real* DDR/WCR. No
  OCR engine (Docling) is installed in this environment, so scanned-PDF accuracy is
  still unverified beyond the honest-degradation path added in Step 3.

### Step 5: Cloud Parser Fallback (Reducto / Extend.ai) + Performance Regression Fix
* **Date & Time:** 2026-09-28
* **Action:** User requested a fallback to commercial cloud parsers (Reducto, Extend.ai)
  for pages the local pipeline can't confidently read, triggered automatically
  whenever a page's local confidence drops below threshold (user's explicit choice,
  made aware this trades against the project's own "air-gapped/DGH-sovereignty"
  pitch). No API keys are available yet, so this was built fully wired but
  necessarily unverified against a live account:
  - Looked up Reducto's and Extend.ai's published REST API docs (base URLs, auth,
    upload-then-parse flow, request/response shapes) since guessing at API
    contracts would be exactly the kind of thing that "breaks in real time."
  - New `pipeline/cloud_fallback.py`: uploads + parses the whole document ONCE
    per document (not once per low-confidence page — avoids redundant
    upload/billing), tries Reducto first then Extend.ai, groups Reducto's
    response by each block's source page (`bbox.page`) and Extend's by its
    page-chunking mode, and returns per-page text. Every network call is
    wrapped, timed out (30s default), and never raises — any failure (no key,
    network down, bad response) just leaves the page on its local result.
  - **Fully inert with no keys configured** (the actual current state):
    `should_use_cloud_fallback()` returns `False` immediately, zero network
    calls, byte-for-byte same behavior as before this feature existed —
    verified by re-running `validate_module01.py` and the real-document test.
  - Added `PageExtractionResult.extraction_source` ("local"/"reducto"/
    "extend_ai") and `DocumentExtractionResult.cloud_fallback_pages_count` /
    `.cloud_fallback_providers_used` so any document that left the air-gapped
    boundary is auditable per-page, not just a silent aggregate. Surfaced in
    `GET /api/v1/health` too (key-presence status, threshold, master switch).
  - Configuration is entirely env-var driven (`NWIS_REDUCTO_API_KEY`,
    `NWIS_EXTEND_API_KEY`, `NWIS_EXTEND_WORKSPACE_ID`,
    `NWIS_CLOUD_FALLBACK_CONFIDENCE_THRESHOLD`, `NWIS_CLOUD_FALLBACK_ENABLED`)
    — no code change needed to activate once a key exists. Manual smoke-test
    entry point: `python -m pipeline.cloud_fallback path/to/test.pdf`.
  - **Still needed from the user:** an actual Reducto and/or Extend.ai API key
    to verify the request/response shapes above against the live API — they
    were built from documentation, not exercised against a real account.
  - **Found and fixed a real performance regression while testing this,
    unrelated to the cloud fallback itself:** Step 3's fix (checking every
    page for scan-status, not just page 0) had accidentally doubled calls to
    `is_page_scanned()`, which renders and MD5-hashes every image on a page
    (PyMuPDF's `get_image_rects`) — on the 74-page real-world test document,
    this was costing ~4.5 of ~9.4 seconds of total pipeline time. Fixed two
    ways: (1) stopped computing it twice per page (the pre-pass result is now
    passed into `extract_page_native` instead of being silently recomputed
    inside it), and (2) short-circuited the expensive image-hash entirely
    whenever a page already has ≥50 characters of text, since the scan
    verdict is `chars<50 AND image_coverage>0.6` — image coverage can never
    change the outcome once chars≥50. Net effect: the same 74-page document
    that was taking ~9.4s now takes ~0.5–0.7s end to end (verified by direct
    before/after timing, plus a synthetic all-image PDF re-test confirming
    genuinely scanned pages are still correctly detected).

### Step 6: Cloud Fallback Verified Against Live Reducto & Extend.ai Keys
* **Date & Time:** 2026-09-28
* **Action:** User provided real Reducto and Extend.ai API keys. Wired `.env` file
  support into `pipeline/cloud_fallback.py` (via `python-dotenv`, already a listed
  dependency but previously unused) so keys live in a git-ignored
  `modules/01_document_intelligence/.env` file — added `.env.example` as a
  template and confirmed `.env` is git-ignored. Then ran the manual smoke test
  (`python -m pipeline.cloud_fallback`) against both providers, which — as
  flagged as a risk in Step 5 — surfaced real drift between their published docs
  and live behavior:
  - **Reducto: worked on the first try**, no drift. Also upgraded its confidence
    scoring to use the live-observed `granular_confidence.parse_confidence`
    numeric field (more precise than the high/low label alone documented).
  - **Extend.ai needed three real fixes**, each diagnosed from the live error
    response, not guessed:
    1. `x-extend-api-version` header is mandatory for any key created after
       2025-04-21 (confirmed live: 400 `INVALID_REQUEST`, "Missing x-extend-api-
       version version header"). Added, defaulting to `2026-02-09`.
    2. The upload response's file ID is at the top level (`id`), not nested
       under `file.id` as the fetched docs showed — the live API has moved to
       what Extend's own docs call a "new resource-based API."
    3. The parse request's file reference field is `{"id": ...}`, not
       `{"fileId": ...}` — and its chunks live under `output.chunks`, not
       top-level `chunks`. Also upgraded to use the live `chunk.metadata.
       avgOcrConfidence` field (a real per-chunk OCR confidence the fetched
       docs didn't mention) instead of a fixed 0.80 estimate.
  - After all three fixes, both providers independently confirmed working
    against live keys.
  - **Full end-to-end pipeline verification** (not just the raw API calls):
    built a second synthetic document — the same realistic Indian-Oil-DDR
    content as Step 4, but genuinely rasterized into an image with no text
    layer (simulating a real scanned document) — and ran it through
    `process_document()` unmodified. Confirmed the complete chain: local
    Tier 1/2 correctly found 0% confidence (no Docling installed) → cloud
    fallback triggered automatically → Reducto OCR'd the page → text was
    substituted and Tier 3 re-ran entity extraction on the real OCR output →
    Layer 5 physics validation correctly auto-repaired an out-of-range mud
    weight (4.1 ppg, below the 8.33 ppg freshwater floor → 14.1 ppg) *found in
    live-OCR'd text*, not a hand-constructed test object → formation tops (2),
    NPT records (2, totaling 8.25h), and drilling events (3) all extracted
    correctly → `extraction_source="reducto"` and `cloud_fallback_pages_count=1`
    correctly tagged on the result.
  - **Verified the trigger stays selective**: re-ran the real 74-page Utah
    FORGE document (all pages natively digital, high confidence) — confirms
    `cloud_fallback_pages_count=0`, i.e. no unnecessary cloud calls/cost/
    sovereignty exposure for documents the local pipeline already handles well.
* **Real benchmark numbers (this environment, this session):**

  | Scenario | Pages | Cloud pages used | Time | Confidence | Notes |
  |---|---|---|---|---|---|
  | Utah FORGE DDR (real, native digital) | 74/74 | 0 | 0.34s | 99.0% | Unaffected by cloud fallback — stays fully local as designed |
  | Synthetic scanned Oil India DDR (rasterized, forces fallback) | 1/1 | 1 (reducto) | ~8.1s | 100% | Dominated by the Reducto network round-trip (~7.8s upload+parse for one page); mud-weight auto-repair (4.1→14.1 ppg), 2 formation tops, 2 NPT records (8.25h total), 3 events all recovered correctly from live-OCR'd text |

  The ~8s figure is a per-DOCUMENT cost (one upload+parse call for the whole
  file, cached and reused for every low-confidence page in it), not per-page —
  a large multi-page scanned document needing fallback would pay this cost
  roughly once, not once per page.
* **Cleaned up:** removed accumulated test-run JSON output and uploaded PDFs
  from `data/output/`/`data/uploads/` (all git-ignored, just session cruft).
  Kept both synthetic PDFs in `data/sample_docs/` as ongoing regression fixtures
  — one exercises formation-tops/NPT/mud-repair on native text, the other
  exercises the full cloud-fallback path on a genuinely scanned page.

### Step 7: "Do It All" — Docling Install, Auth, Module 02 Audit
* **Date & Time:** 2026-09-28
* **Action:** User asked to address every open item from Steps 5/6 (Docling install,
  auth, Module 02 audit) and declare the system complete, flagging anything that
  needed their input. Worked through each:
  - **Docling installed for real** (`pip install docling docling-core`, unpinned —
    pulled 2.130.0, far ahead of requirements.txt's untested 2.5.0 pin). This
    immediately surfaced a real dependency conflict: docling 2.130.0's Pydantic
    model definitions raised `AttributeError: force_full_page_ocr` against the
    pinned `pydantic==2.8.2`. Upgraded to `pydantic==2.13.5` (verified compatible),
    updated requirements.txt's pins to what's actually installed and tested rather
    than the untested 2.5.0/2.8.2 guess.
  - **Local OCR end-to-end test surfaced a genuine, important limitation:** ran the
    scanned synthetic DDR through local Docling OCR (first run: ~92s on CPU,
    downloading model weights). It correctly recovered mud properties and both
    formation tops, but **silently garbled the entire narrative "OPERATIONS
    REMARKS" section** — losing all 3 drilling events and 8.25 NPT hours that
    Reducto (cloud fallback) had correctly extracted from the exact same page in
    Step 6. Worse: Docling's own self-reported confidence for that page was
    "excellent" (~0.93) — its confidence scoring reflects OCR/layout quality, not
    whether the resulting text is semantically correct, so this failure mode
    would not have triggered cloud fallback even with a real (not hardcoded)
    confidence value. Fixed the hardcoded-0.95 confidence (a real, separate bug —
    it was a constant, not derived from anything) to use Docling's genuine
    per-page score, which is a real improvement but explicitly does NOT claim to
    solve the underlying limitation — documented plainly in code and here rather
    than silently working around it.
  - **API authentication + rate limiting added to both modules** (`api/auth.py` /
    `auth.py`): shared `X-API-Key` header, auto-generated and persisted to `.env`
    on first run if absent (secure by default, zero setup burden), enforced on
    every data/mutating route while health/root/docs stay open for monitoring.
    Module 02's CORS also tightened from a wide-open `allow_origins=["*"]` to a
    configurable allowlist, matching Module 01.
  - **Found and fixed a real bug in the auth auto-provisioning code itself,
    reproduced identically in both modules:** `_ensure_api_key()` imported
    `generate_api_key` from the `auth` module before setting `os.environ`, which
    triggered `auth.py`'s module-level `API_KEY = os.environ.get(...)` to
    evaluate too early and freeze empty for the rest of that process's life —
    verified by testing (not just reasoning about it): the server's very first
    boot after generating a fresh key ran with auth silently disabled, only
    correct after a second restart. Fixed by generating the key with stdlib
    `secrets` directly, avoiding the premature import, and reverified a genuinely
    fresh single-launch now enables auth immediately in both modules.
  - **Module 02 (NWIS Backend) got the same scrutiny Module 01 already had** —
    it had never been tested this session before now:
    - The Stratigraphic Correlator (`align_horizons_across_wells`/
      `stratigraphic_depth`) — Engine 2 of the README's own 4-engine
      architecture — had no caller anywhere in the codebase; it was fully
      implemented and completely unreachable. Added
      `GET /api/v2/stratigraphic_depth_track/{well_id}` to expose it; verified
      it correctly aligns offset wells at equivalent geological horizons.
    - `depth` query parameters accepted negative values with no validation
      (`depth=-100` returned HTTP 200 with a nonsensical analysis). Added `ge=0`
      across all depth-accepting endpoints.
    - The alert message cited `rankings[0]` (the single overall top DORS-ranked
      well) as the evidence source regardless of which well(s) actually
      contributed to the specific corridor being alerted on — a real
      evidence-misattribution bug for a system whose selling point is an
      auditable, non-black-box confidence trail. Fixed to cite the corridor's
      actual `contributing_wells`.
    - `RiskCorridor.risk_level` and `HazardRiskAssessment.risk_level` are
      legitimately different measures by design (corridor proximity vs. the
      full R_H(t) composite per the math spec) but shared the same field name,
      so they could — and did, in testing — disagree under the same field name
      with no explanation (a corridor at HIGH proximity risk under a hazard
      assessment reporting MODERATE overall). Renamed the corridor's field to
      `proximity_risk_level` with a docstring explaining the distinction.
    - That same disagreement was also a real product gap, not just a naming
      one: the alert-message trigger gated on the composite's `risk_level`, so
      a corridor with 5 analog wells, CRITICAL historical severity, and the
      bit only 38m away never generated an alert once the blended composite
      (which also folds in quiet real-time sensor/ML terms) diluted it to
      MODERATE — precisely the scenario this early-warning mechanism exists
      to catch. Fixed the alert gate to check the corridor's own
      `proximity_risk_level` instead; reverified live that the alert now fires
      with correct well attribution ("HGJ-011 +4 more analog").
    - A silent `pass` on malformed telemetry records (zero logging) replaced
      with a warning + count, so a bad telemetry file can't silently lose data
      with no visible signal.
    - Added the same production-hardening as Module 01: `NWIS_ENV` dev/prod
      split (auto-reload was unconditionally on), rotating file logging,
      global exception handler, host/port via env vars.
  - Re-ran both modules' full validation suites and live server smoke tests
    (auth enforcement, negative-depth rejection, the new endpoint, the
    corrected alert message) after every fix — all green.
* **What "do it all" did NOT include, and why:** Phase 4 (React/TS/Tailwind
  frontend cockpit — GIS map, stratigraphic depth track UI, telemetry strips,
  evidence modal, AI copilot) and Phase 5 (live replay simulation suite) are
  net-new, large-scope builds with real design decisions (map library, hosting,
  visual design) that weren't attempted without direction — flagged back to the
  user rather than guessed at.

### Step 8: Real Trained ML Model for Hazard Prediction (Module 02)
* **Date & Time:** 2026-09-28
* **Action:** Re-grounded in the literal PS 26121 text (`research/research/
  PROBLEM_STATEMENT.md`, not the summarized version in `00_PROJECT_OVERVIEW`) and
  mapped its 7 expected outcomes against what's actually built. Found the widest
  gap: outcome v asks for "predictive analytics **models**," but
  `compute_ml_score()` was — by its own docstring — a hand-coded physics
  heuristic explicitly standing in for a model, "for demonstration without
  training data." User chose this as the priority to close first (over the
  searchable-knowledge-repository gap in outcome iii, and the live-streaming
  gap in outcome vi).
  - **Data reality check before building anything:** the synthetic testbed has
    39 events across only 4 hazard types — STUCK_PIPE (14), WELLBORE_INSTABILITY
    (12), KICK (10), MUD_LOSS (3) — with TORQUE_SPIKE and CEMENTING_FAILURE at
    zero. Also found telemetry only exists for one well (`WELL-HGJ-012`), not
    all 12 — ruling out telemetry-based features for a general cross-well model.
  - **Built a real training pipeline** (`modules/02_nwis_backend/ml/`):
    `feature_engineering.py` (depth, formation pore-pressure gradient, formation
    stratigraphic group, trajectory inclination, well type — deliberately
    excluding mud weight/overbalance, since no historical event carries a mud
    weight and a model can't learn from a constant), `train_hazard_models.py`
    (per-hazard-type `LogisticRegression`, only for hazard types with ≥8
    historical positives — a threshold that automatically excludes MUD_LOSS (3),
    TORQUE_SPIKE (0), and CEMENTING_FAILURE (0) from training, not silently but
    with a logged reason), `hazard_predictor.py` (inference: loads a trained
    model where one exists, physics heuristic where it doesn't, and — always,
    on both paths — adds the overbalance term as a physics adjustment on top,
    since that's real domain knowledge no amount of this training data can
    teach a model).
  - **Honest cross-validation, not just a training-set claim:** used
    leave-one-**well**-out (not ordinary k-fold — rows from the same well share
    formations/trajectory and would leak between folds) to report real
    out-of-sample ROC-AUC per hazard type before committing to the final model.
    Real, measured results: **KICK 0.817** (genuine signal), **STUCK_PIPE
    0.622**, **WELLBORE_INSTABILITY 0.606** (both barely better than random —
    reported as such, not oversold).
  - **Added `HazardRiskAssessment.m_ml_source`** ("trained_model" |
    "heuristic_fallback") to the API response — verified live via
    `/api/v2/analyze` that MUD_LOSS/TORQUE_SPIKE correctly report
    `heuristic_fallback` while STUCK_PIPE/KICK/WELLBORE_INSTABILITY report
    `trained_model`, so the distinction is visible to any caller, not buried.
  - Added `python run_server.py --train-ml` entry point; added
    scikit-learn/joblib/numpy to requirements.txt.
  - Re-ran the full validation suite and a live server smoke test (auth,
    negative-depth rejection, the corridor alert-attribution fix from Step 7)
    — all still pass; composite hazard scores visibly changed (confirming the
    new predictor is actually wired in, not silently bypassed).
* **What this is not:** a clinically validated predictive model. 10–14 positive
  examples is a real, acknowledged limitation — the point of this work was a
  genuine, retrainable pipeline ready for real historical Oil India event data,
  with honest performance reporting, not a claim that today's numbers are
  production-grade accuracy.

### Step 9: Research-Validated DORS Upgrade + Searchable Knowledge Repository
* **Date & Time:** 2026-09-28
* **Action:** User asked to customize/fine-tune Module 02 against the PS and real
  precedent, then move straight to the next open gap. Researched real commercial/
  government/academic precedent first (Corva, Novi Labs, a Schlumberger patent,
  multiple SPE papers, BSEE's public data, DGH's NGDR), then applied the most
  concrete, sourced finding immediately:
  - **DORS trajectory scoring rebuilt from a real patent's method.** The original
    `score_trajectory()` compared only a single scalar (each well's *average*
    inclination) — two wells that build angle at completely different depths could
    score identically if their averages happened to match. Rebuilt it to compare
    the full inclination AND azimuth *profile* (10 sampled points across the two
    wells' overlapping measured-depth range, azimuth compared with proper 0/360
    wraparound handling via unit-vector interpolation) aggregated via a blend of
    mean and max distance — directly modeled on Schlumberger's "Offset Well
    Analysis Using Well Trajectory Similarity" patent (WO2021029996A1, which uses
    a Modified Hausdorff Distance across vertical/horizontal/angular components).
    Added shared `inclination_at_md`/`azimuth_at_md` helpers to
    `stratigraphic_correlator.py` (also deduplicating a private copy in
    `ml/feature_engineering.py` that was doing the same interpolation separately).
  - **Verified this is a real behavioral improvement, not just different numbers:**
    re-ran the DORS ranking at the same well/depth used throughout this project's
    testing — the #1-ranked offset well changed from a 12.3km-away well to a
    58km-away well with a perfect formation match (same formation, same depth
    window) and 96.4% trajectory similarity. Confirmed by hand-checking the
    weighted sum against the component scores that this is mathematically
    correct, not a bug — and it's a *more* convincing demonstration of the
    project's own "nearby is not the same as relevant" thesis than the previous
    scoring gave.
  - **Checked the Assam-Arakan formation list against real published stratigraphy**
    (DGH's own Assam-Arakan basin document, USGS Bulletin 2208-D, AAPG): the
    existing formation sequence (Alluvium → Tipam Sandstone → Girujan Clay →
    Barail → Kopili → Sylhet Limestone → Langpar → Basement) already matches the
    real, published sequence correctly — no fix needed there.
  - **Built the searchable knowledge repository** (PS outcome iii — the gap
    identified two sessions ago and deferred until ML was done):
    `search/knowledge_search.py` embeds each event's narrative + mitigation +
    outcome text via `sentence-transformers` (all-MiniLM-L6-v2) and ranks by
    cosine similarity; falls back to keyword substring matching if
    sentence-transformers isn't installed or fails to load (same
    real-capability-with-honest-fallback pattern as the cloud OCR fallback and
    the ML hazard model). New endpoint `GET /api/v2/events/search` — verified
    genuinely semantic, not keyword overlap in disguise: the query "pipe got
    stuck against the wall of the hole" (zero literal word overlap with the
    actual event text) correctly retrieved STUCK_PIPE events describing "Tight
    hole observed while tripping out." Combines with the existing structured
    filters (hazard_type/formation/depth/severity) to narrow candidates first.
  - **Fixed a real routing bug before it ever shipped:** FastAPI matches routes
    in registration order, and `/api/v2/events/{well_id}` (a wildcard path
    segment) was registered before the new `/api/v2/events/search` — meaning
    every search request would have been silently swallowed by
    `get_well_events(well_id="search")` instead of reaching the search endpoint
    at all. Caught by inspecting `app.routes` directly before considering this
    done, not just by testing the happy path.
  - Full validation suite re-run and passing after all changes.

### Step 10: Live Replay Simulation — Real-Time Alert Stream
* **Date & Time:** 2026-09-28
* **Action:** Closed the last of the three PS-gap items identified two sessions ago
  (ML model → knowledge search → this): PS outcome vi ("real-time alerts") and
  Phase 5 ("Live Replay Simulation"), which turned out to be the same piece of work.
  - **Honest design decision, made explicit up front:** the synthetic telemetry
    stream covers exactly one well (`WELL-HGJ-012`) over an 8-metre depth window
    (2128.5–2136.0m, one simulated hour) — replaying that alone would barely move
    and would never cross a risk corridor. Drove the simulated depth from the
    well's full trajectory (surface to TD) instead, so the replay actually
    traverses meaningful depth range. Consequence, stated in the module docstring
    rather than glossed over: sensor-anomaly scoring (`A_sensor`) only has genuine
    telemetry to work with while simulated depth is inside that same 8m window —
    correctly (and pre-existing-ly) zero elsewhere, not faked.
  - **Built `live/replay_engine.py`** (async generator, depth-stepped replay of
    `orchestrator.analyze()`) and `GET /api/v2/live/replay/{well_id}` (Server-Sent
    Events, chosen over WebSocket since this is server-push-only and needs no
    client library beyond `curl -N` or `EventSource`).
  - **Verified with a real, saved stream, not just "the server responded 200":**
    replayed `WELL-HGJ-012` from 30m to TD (2838m) across 9 ticks. Result showed
    correct formation progression (Dihing → Tipam Sandstone → Girujan Clay →
    Barail Sandstone → Barail Coal-Shale → Kopili) with overall risk correctly
    escalating LOW → MODERATE → HIGH, and **two distinct, correctly-attributed
    alerts firing exactly at corridor boundaries** ("0m to historical STUCK PIPE
    zone (MRN-006 analog)" at 1434m; "0m to historical KICK zone (HGJ-010 analog)"
    at TD) — the ML/heuristic split (`m_ml_source`) stayed consistent with every
    earlier verification throughout.
  - **Verified clean disconnect handling**, not just the happy path: started a
    50-tick/1s-per-tick replay, force-killed the client 2.5s in, confirmed via the
    server log that no further ticks were computed afterward — no orphaned
    background loop left running server-side.
  - **Noted, not silently ignored:** a browser's native `EventSource` API cannot
    set custom headers, so real frontend integration (Phase 4, whenever it
    happens) will need either a cookie-based session or a query-string token
    variant of the auth check — flagged in the endpoint's own docstring as a known
    gap this endpoint alone doesn't solve.
  - Full validation suite re-run and passing.
* **Status after this step:** all three PS gaps identified in the "understand the
  problem statement in depth" pass are now closed (ML model, searchable knowledge
  repository, real-time alerts). The only PS outcomes still unaddressed are ii and
  vii — the map-based visualization and dashboard — which is Phase 4, a frontend
  build with real design decisions (map library, hosting, visual design) not yet
  made.

### Step 11: Curation Review Workflow (Module 01) + Facet Search (Module 02)
* **Date & Time:** 2026-09-28
* **Action:** User asked to research OpenEI's Geothermal Data Repository (GDR —
  the actual source of this project's one real test document, the Utah FORGE DDR)
  for genuinely applicable ideas, then confirmed building the two that were
  backend-only and well-scoped: a curation/review workflow, and faceted search.
  - **Curation review workflow (Module 01).** GDR states its metadata "undergoes
    curation review... before publication." This project already had the schema
    hook for exactly that (`ValidationStatus.MANUAL_REVIEW`) but — same
    dead-code pattern found repeatedly throughout this project — nothing had
    ever set it, and there was no endpoint for a human to act on it. Added
    `reviewed`/`reviewed_by`/`review_decision`/`review_notes`/`field_annotations`
    to `DocumentExtractionResult`, and three new endpoints
    (`api/routes/review.py`): `GET /review/queue`, `POST /review/{doc_id}/decision`
    (approve/reject), `POST /review/{doc_id}/annotate` (a human-readable
    correction note attached to a specific field — deliberately NOT an automatic
    deep-path JSON patch, since a slightly-wrong path silently corrupting data is
    a worse failure mode than requiring a human to write the correct value out).
  - **A real bug found and fixed before it shipped, not caught by luck:** first
    attempt at the confidence-based MANUAL_REVIEW trigger
    (`overall_confidence < 0.5`) was tested against a genuinely blank scanned
    page — and it silently failed to fire. Investigated why: RapidOCR itself
    logged "text detection result is empty" (0 characters extracted), yet
    Docling's self-reported confidence for that page was **86%** — the same
    confidence-doesn't-mean-correct-content gap already documented in
    `tier2_ocr_engine.py` from Step 3, now caught biting a *second* piece of
    code that trusted the same signal. Fixed by adding a second, independent
    trigger: any scanned page whose extracted text is under 20 characters
    escalates to review regardless of what confidence claims. Re-tested the
    exact same blank-page document — correctly escalated this time, verified
    live through the full API (appeared in `/review/queue`, annotated,
    approved, correctly disappeared from the queue afterward, `validation_status`
    correctly moved `PENDING_MANUAL_REVIEW` → `PASS`).
  - **Faceted search (Module 02).** GDR's search UI shows counts per filter
    value ("Utah FORGE, UT (372)"). Added `_compute_facets()` to
    `/api/v2/events` and `/api/v2/events/search`, returning counts by
    hazard_type/formation/severity/well_id. Verified: facets on the
    unfiltered endpoint sum correctly to all 39 events; facets narrow
    correctly when a structured filter is applied (14/14 when
    `hazard_type=STUCK_PIPE`); facets on the search endpoint correctly reflect
    the full candidate set (39), not just the `top_n` results actually
    returned — matching GDR's own pattern of showing full breakdown counts
    even when only a page of results is displayed.
  - **What was explicitly NOT copied from GDR, and why:** GDR is a
    multi-contributor federated repository (146 organizations). That's
    structurally opposite to this project's DGH-sovereignty pitch (Oil India's
    data staying air-gapped, not federated with other operators) — copying that
    model would contradict the system's own stated differentiator, so it wasn't.
  - Full validation suites for both modules re-run and passing after all changes.

### Step 12: Prasad Branch Integration + Module Restructuring + Frontend Build-Out
* **Date & Time:** 2026-09-28
* **Action:** User shared a teammate's ("Prasad") parallel branch and asked for an
  honest review followed by integration of what's genuinely worth taking, kept
  well-organized. Two independent audit agents reviewed the backend (4 modules)
  and frontend (11 pages) against the same rigor standard as this project's own
  code — found real quality (a genuine drilling-physics digital twin, a properly
  implemented SPE minimum-curvature trajectory engine, 8/11 real working
  frontend pages) alongside real problems (a benchmark report with fabricated
  PR-AUC/lead-time/false-alarm numbers; a `SystemStatusPage` that fetched real
  health data then ignored it in favor of a hardcoded "105/105 TESTS PASSING"
  banner; a trajectory-similarity scorer that was a *regression* vs. this
  project's own Hausdorff-profile comparison).
  - **Ported, not force-merged:** `physics_engine` + `predictive_analytics` split
    into their own modules (`04_physics_engine`, `05_predictive_analytics`,
    matching Prasad's own internal "Module 4/5" docstring numbering) rather than
    bundled — 13/13 and 19/19 tests passing respectively, including the exact
    causal-chain tests (lost circulation, kick, full closed-loop demo) that were
    failing in Prasad's own branch. The fabricated benchmark report
    (`model_benchmarking.py`) was explicitly excluded, not carried over.
  - **`well_intelligence` upgrades merged additively into `modules/02_nwis_backend`**
    without touching `score_trajectory()`'s existing (better) Hausdorff
    comparison: real minimum-curvature TVD interpolation (fixed a genuine bug —
    old code flat-clamped TVD for any MD past the last survey station),
    structural fault-boundary gating (verified against the synthetic testbed:
    found 2 real fault-like well pairs, confirmed the 0.20 penalty fires
    correctly), and a new `ahead_of_bit` corridor endpoint reimplemented against
    this project's own schema rather than Prasad's incompatible coordinate
    system.
  - **Frontend fully ported** (`frontend/`) and rewired to this project's real
    two backends (was pointed at Prasad's own, different, backend) — the two
    fabricated pages (`DocumentIngestionPage`, `SystemStatusPage`) were rebuilt
    for real rather than carried over as-is.
  - **Modules 04/05 wired to a real FastAPI + WebSocket API** (`/api/v3`) —
    previously just tested Python libraries with no HTTP surface at all. Verified
    live, not just unit-tested: injected a `LOST_CIRCULATION` scenario through
    the running server and got back a real, evidence-chained CRITICAL alert
    ("Pump LCM & Reduce Rate... Spot 25 bbl medium-grade LCM pill").
  - **Built two new features closing PS-outcome gaps:** a real PDF evidence
    viewer (`GET /api/v1/documents/{doc_id}/file` + `PdfEvidenceViewer.tsx`) and
    a Knowledge Copilot (`CopilotPage.tsx`) — deliberately built as a **grounded
    retrieval assistant, not a generative one**: no LLM API is configured
    anywhere in this project, so it parses simple entities from the query and
    composes an answer strictly from real `/api/v2/*` results, each claim
    traceable to a real record. Also built the side-by-side top-3
    DORS-ranked-offset-well correlation view (previously one well at a time via
    a dropdown).
  - **Built a new PostgreSQL/PostGIS/pgvector/TimescaleDB database layer**
    (`database/`) modeled on OSDU/WITSML/PPDM, as a new, standalone layer
    explicitly **not yet wired into modules 01/02's existing SQLite/JSON
    storage** — verified live with real data (12 wells, 1245 trajectory
    stations, 97 formation tops, 39 embedded events, 3600 telemetry records)
    and real proof-of-concept queries against all three extensions (a PostGIS
    radius search, a pgvector cosine-similarity search, a TimescaleDB
    `time_bucket()` aggregation).
  - Two of the four parallel execution agents building this hit the account's
    session rate limit mid-task; recovered by checking actual on-disk/live-server
    state directly rather than trusting either agent's un-verified self-report,
    and finished the remaining work (Copilot page, database Docker/migration
    tooling, two page wirings) directly.
* **Status after this step:** all 7 PS-outcome modules have real, live-verified
  implementations for the first time. Known residual gaps carried forward
  honestly: modules 01/02 still run on their original storage, not the new
  database; the module numbering under `modules/` does not 1:1 match the PS's
  7-outcome numbering (documented, not yet resolved); no real-world data had
  been run through any of this yet.

### Step 13: First Real-Data Benchmark (Equinor Volve Field) — Module 01
* **Date & Time:** 2026-09-29
* **Action:** Sourced real, open-licensed drilling data (Equinor's Volve field,
  North Sea) via Databricks Marketplace/Delta Sharing, pulled 14 real documents
  (~120 MB) spanning drilling reports, mud logs, completion reports, formation
  pressure, petrophysical, biostrat, geochem, and trajectory survey reports
  across wells 15/9-F-1 (+A/C), F-9, F-12, and 15/9-19 A/B — and ran all 14
  through module 01's real extraction pipeline, not a simulation.
  - **Result:** 979 pages processed, 100% completion rate, 96.6–99.2%
    self-reported confidence. On the surface, a clean run.
  - **Real bugs this surfaced that synthetic data never could, found by reading
    actual extracted output against the source PDFs:**
    1. **"Kick off"/"kicked off" (directional-drilling term for starting to
       build inclination) is systematically misclassified as `KICK` (a
       well-control emergency).** Verified with direct quotes: *"Bit #1... kicked
       off and drilled without problem to 2345m"* → extracted as `KICK`/HIGH
       severity. Root cause: a bare substring match on "kick" with no
       distinction from "kick off"/"kicked off"/"kick-off". Of 34 total `KICK`
       classifications across the 14 documents, a large fraction are this exact
       false positive.
    2. **Zero formation tops extracted across all 14 documents (979 pages).**
       Not a fluke — the entity extractor's formation-name list is hardcoded to
       Assam basin names (Tipam Sandstone, Barail Coal-Shale, etc.) with no path
       to recognize North Sea formations. A real generalization ceiling, not a
       transient bug.
    3. **Well-name correctly extracted in only 1 of 14 documents** (`15/9-F-1`,
       from the BIOSTRAT report). The other 13 returned `None`, `"/"`,
       `"Report"`, `"evaluation"`, or `"REPORT"` — the heuristic was overfit to
       the one original Oil India test document's layout.
    4. **Schema gap between modules:** module 01's `EventType` enum includes
       `GAS_INFLUX` and `EQUIPMENT_FAILURE`, neither of which exists in module
       02's `HazardType` enum. Even a perfectly-extracted event of either type
       currently has nowhere to go downstream.
  - **What was confirmed genuinely correct, not just broken** — spot-checked
    real extractions, not assumed: `STUCK_PIPE` and `LOST_CIRCULATION`
    classifications on this same real data were accurate (*"Due to stuck pipe,
    the string was severed and the well plugged back"* → correctly `STUCK_PIPE`).
    The pipeline is not uniformly broken; the kick/kickoff ambiguity and the
    basin-specific vocabulary are the two concrete, scoped problems.
  - **The 96.6–99.2% confidence score tracked none of the above** — confirmed
    directly (not assumed) that this metric measures OCR/text-extraction
    confidence only, never semantic/entity correctness, on a real, previously
    untested document set.
  - **Data requirements identified for the remaining pipelines, concretely, not
    speculatively:** M2/M4/M6 need structured trajectory data — the Volve share
    has this as **WITSML XML** per well (already located, not yet pulled),
    which is directly usable, versus the **PDF** "Standard Survey Report" files
    pulled this round, which are not. M3/M5 need the kick/kickoff fix applied
    first, or the real events extracted this round would poison any Hit@5 /
    leave-one-well-out evaluation built from them as labels.
* **Status after this step:** first real-data benchmark complete for module 01,
  fully documented including what failed, not just what passed. Fix priority
  set: (1) kick/kickoff regex, (2) basin-configurable formation-name list, (3)
  well-name extraction heuristic, (4) `EventType`/`HazardType` enum
  reconciliation — in progress next.

### Step 14: Fixing the Real Bugs Found in Step 13
* **Date & Time:** 2026-09-29
* **Action:** Fixed items (1) and (2) from Step 13's priority list, then
  re-verified against the exact same real Volve document rather than trusting
  the code change in isolation.
  - **Kick/kickoff false positive** (`pipeline/tier3_entity_extractor.py`):
    added a preprocessing step that neutralizes `kick(?:ed)?[\s-]?off` to a
    placeholder token before event-type and severity keyword matching, so the
    bare `"kick"` keyword no longer fires on the directional-drilling sense.
  - **Basin-hardcoded formation list** (`models/domain_rules.py`): replaced the
    single `ASSAM_ARAKAN_FORMATIONS` constant with a `FORMATION_PROFILES` dict
    and a `get_active_formations()` getter reading `NWIS_FORMATION_PROFILE`
    (default unchanged). Added a real, web-verified `NORTH_SEA_VOLVE` profile
    (Hugin, Draupne, Heather, Utsira, Skagerrak, etc. — checked against
    published Volve field stratigraphy, not guessed). Updated both call sites
    in `tier3_entity_extractor.py` (event-narrative formation tagging and
    `extract_formation_tops()`) to use the getter instead of the hardcoded
    Assam list.
  - **A real deployment bug found while re-verifying, not caused by the code
    fix itself:** re-testing against the running server initially showed NO
    change at all. Root cause: an orphaned worker process from hours earlier in
    this session (`PID 30628`, 369 MB resident) was still bound to port 8001
    alongside the newly-started process — `taskkill` on the reloader's PID had
    only killed the supervisor, not this leftover worker, so requests were
    silently still being served by stale pre-fix code. Confirmed by calling
    `extract_drilling_events()` directly in a fresh interpreter (correctly
    returned 0 events for a "kicked off and drilled" sentence) while the API
    still returned the old, wrong answer — isolating the bug to process
    state, not the code. Fixed by force-killing every PID bound to 8001 and
    confirming exactly one clean listener before re-testing.
  - **Re-verified against the same real document** (`WELL-15_9-19B_END_OF_WELL_REPORT.pdf`,
    the worst offender from Step 13) on the genuinely-reloaded server:
    - Formation tops: 0 → **1** (`Ty Formation` — a real Volve-field formation,
      confirming the basin-profile fix works end-to-end, not just in a unit
      test). Still low relative to how many formations the 77-page document
      likely names — `extract_formation_tops()`'s regex requires a depth
      figure to appear shortly after the formation name in the same match, and
      real prose doesn't always phrase it that tightly (e.g. *"above the
      Balder formation, which showed full returns"* has no adjacent depth
      number). Noted as a real, separate limitation, not silently claimed as
      fully solved.
    - `KICK` events: 20 → 13, and **every one of the 13 remaining is a
      genuine well-control mention** on inspection — flow checks, a
      pit-volume gain, a shut-in, and several sentences that literally read
      *"Well control incident (19B)"* in the source text. Zero of the
      "kicked off"/"kick off"/"kick-off" directional-drilling false positives
      that dominated the original 20 remain. The fix improved precision
      without losing real positives, confirmed by reading the actual
      remaining narratives, not just the count delta.
* **Status after this step:** items (1) and (2) fixed and verified against
  real data end-to-end (not unit-tested in isolation and assumed to work).
  Items (3) well-name extraction and (4) `EventType`/`HazardType` enum
  reconciliation still open, next.

### Step 15: Well-Name Extraction Fix — Including a Real Environment Bug Found
While Verifying It
* **Date & Time:** 2026-09-29
* **Action:** Fixed item (3) from Step 13's list. The original single pattern
  (`WELL\s*(?:NAME|NO|NUMBER|#)?[:\.\s]+(...)`) had an OPTIONAL qualifier, so
  it matched "WELL REPORT", "WELL CONTROL", "WELL EVALUATION" — any word after
  "WELL " — just as readily as a real labeled well name. Replaced with a
  3-tier, each-candidate-validated approach in
  `pipeline/tier1_native_extractor.py`: (1) a strict pattern requiring the
  NAME/NO/NUMBER/# qualifier (not optional — this alone is what excludes
  "WELL REPORT" etc.) but with punctuation after it now OPTIONAL, since real
  Volve documents use `"Well NO 15/9-F-11, F-11 T2..."` with only whitespace,
  no colon; (2) a filename-shape fallback bounded to the well-ID pattern
  itself rather than a generic greedy character class; (3) the original loose
  pattern as a last resort. Every candidate is checked for containing a digit
  before acceptance — a real well identifier always has one, a section
  heading generally doesn't.
  - **Iterated through two more real bugs found only by testing against real
    data, not assumed fixed after the first pass:**
    1. The strict pattern's required punctuation (`[:\.]`) failed against the
       real `"Well NO 15/9-F-11"` format (no colon) — fixed by making it
       optional while keeping the qualifier required.
    2. The filename fallback then swallowed job-metadata: this API saves
       uploads as `"{job_id}_{original_filename}"`
       (`api/routes/ingest.py`), and the job-id hex string satisfied the
       well-ID shape pattern's first segment just as well as "WELL" did —
       producing well names like `"D59F2BC68F_WELL-15"`. Fixed by stripping
       the known `"JOB-[hex]_"` prefix before matching, rather than trying to
       make the shape pattern guess around it.
  - **A real environment bug, unrelated to this project's own code, that
    nearly invalidated every verification pass:** repeated re-tests kept
    returning IDENTICAL results to before the fix, even after "restarting"
    the server each time. Root cause, confirmed step by step: an old worker
    process (PID 18984) never actually died despite `taskkill` repeatedly
    reporting success — `Get-Process -Id 18984` and `Stop-Process` both
    independently confirmed via PowerShell that **Windows itself has no
    record of this PID**, yet `Get-NetTCPConnection` showed it still owning
    port 8001 in LISTEN state and continuing to serve real HTTP responses. An
    orphaned kernel-level socket with no owning process — a genuine anomaly of
    this sandboxed environment, not a bug in `run_server.py`. Confirmed the
    real fix was correct throughout via direct, out-of-process Python calls to
    `extract_document_metadata()` (which correctly returned the fixed value)
    even while the API kept returning the stale one — isolating the
    discrepancy to process/OS state, not the code, before spending any more
    time doubting the fix itself. Resolved pragmatically by moving module 01
    to port 8011 for verification rather than continuing to fight an
    unkillable socket.
  - **Final verification, on a genuinely fresh single-process server,
    confirmed via `netstat`/PowerShell before testing** (not assumed clean):
    ran all 14 real Volve documents through the actual `/api/v1/ingest` →
    `/api/v1/results` flow one more time.
    | Metric | Before (Step 13) | After (Steps 14+15) |
    |---|---|---|
    | Well names correct/well-ID-shaped | 1/14 | **14/14** |
    | Formation tops extracted | 0 | **38** |
    | Total hazard events | 135 | 119 |
    | `KICK` classifications | 34 | 17 (100% of the remaining 17 confirmed genuine on inspection — real flow-checks, a pit-volume gain, a shut-in, several literally reading "Well control incident" in the source text) |
* **Status after this step:** items (1), (2), (3) from Step 13's fix list are
  now fixed and verified end-to-end against the same real documents that
  originally exposed them. Item (4), `EventType`/`HazardType` enum
  reconciliation between modules 01 and 02, remains open — next.

### Step 16: EventType / HazardType Enum Reconciliation
* **Date & Time:** 2026-09-29
* **Action:** Fixed item (4), the last item from Step 13's list. Module 01's
  `EventType` (10 values) and module 02's `HazardType` (6 values) evolved
  independently with no mapping between them. Added
  `EVENT_TYPE_TO_HAZARD_TYPE` and `to_hazard_type()` to module 01's
  `models/schemas.py`, with each mapping decision justified individually
  rather than guessed:
  - 4 values map directly (identical names): `MUD_LOSS`, `STUCK_PIPE`,
    `KICK`, `WELLBORE_INSTABILITY`.
  - `LOST_CIRCULATION` → `MUD_LOSS` (a loss mechanism specifically; module 02
    doesn't distinguish mechanisms, only the hazard as a whole).
  - `GAS_INFLUX` → `KICK` (the leading indicator/early form of a well-control
    kick; treating it as anything less would understate severity).
  - `EQUIPMENT_FAILURE`, `DEVIATION_CONTROL`, `NPT_OPERATIONAL`, `UNKNOWN` →
    `None`, explicitly. None of these describe a geological hazard a future
    offset well would encounter at the same formation — which is what
    `HazardType` exists to rank — so mapping them to something would be
    fabricating a relationship, not reconciling one.
  - Returns module 02's HazardType as a raw string rather than importing
    module 02's enum class, since module 01 does not (and should not) take a
    dependency on module 02 — the actual integration boundary, whenever one
    is built, constructs module 02's `HazardType` from this value itself.
  - No live code path currently pushes module 01 events into module 02's
    store, so this is deliberately built as a ready, documented translation
    layer for that future integration point, not a live wire-up — stated
    honestly rather than implying an integration exists that doesn't.
  - Verified directly: iterated all 10 `EventType` values through
    `to_hazard_type()`, confirmed each resolves exactly as documented above.
* **Status after this step:** all four items identified in Step 13's real-data
  benchmark are now fixed and verified — three against the real Volve
  documents end-to-end, one by direct exhaustive enum-mapping verification.
  This closes the first full real-data-benchmark-to-fix cycle for module 01.
  User asked to extend real-data validation to the remaining backend
  pipelines (M2/M4 correlation, M3 search, M5 predictive, M6 alerts) and
  document each one's benchmark in this log as it's done — starting now.

### Step 17: Real-Data Benchmark — M2/M4 (Stratigraphic Correlator + DORS
Trajectory Scoring), Module 02
* **Date & Time:** 2026-09-29
* **Action:** The Volve documents pulled for Step 13 included two real COMPASS
  directional-survey PDF reports (`*_TRAJECTORY_SURVEY_ACTUAL.pdf`, wells
  15/9-F-1 and 15/9-F-12) — real MD/inclination/azimuth/TVD survey stations
  from surface to TD, not synthetic. Wrote `real_data/parse_real_trajectories.py`
  to extract these into module 02's exact `SurveyStation`/`WellTrajectory`
  shape, then ran module 02's actual `tvd_at_md`/`inclination_at_md`/
  `azimuth_at_md` (stratigraphic correlator) and `score_trajectory` (DORS)
  functions against the real, parsed result.
  - **Parsing itself surfaced and required fixing two real bugs before the
    data could be trusted, found by inspecting output, not assumed correct
    after the first pass:** (1) a naive 10-number sliding-window chunker
    initially produced physically-impossible rows (inclination=150.15° near
    surface, MD=0 with nonzero TVD) from unrelated header numeric blocks
    ("Tie On Depth: 145.90", magnetic model data) — fixed by enforcing the
    one universal invariant a real survey table always satisfies: MD strictly
    increasing row to row. (2) One remaining outlier survived that filter (a
    tie-on-point row with `ew_m` implausibly jumping to 2464.55 between two
    otherwise-consistent neighbors) — fixed with a targeted
    neighbor-consistency check (a station whose displacement jump from BOTH
    neighbors exceeds 200m while its neighbors are mutually consistent is the
    artifact, not the real data). Final counts: 100 real stations for F-1
    (MD 145.9–3632.0m), 210 for F-12 (MD 174.0–3520.0m).
  - **Validated interpolation accuracy against real brackets**: picked MDs
    falling between two real stations (not on one) and confirmed
    `tvd_at_md`'s minimum-curvature interpolation stays within the real
    TVD bracket in both cases (F-1: interpolated 1625.42m within real
    1609.6–1641.07m bracket; F-12: interpolated 1660.21m within real
    1655.63–1664.78m bracket).
  - **Validated `score_trajectory` on two real, genuinely different-shaped
    wells** — the exact case the Hausdorff-profile approach (Step 12's
    integration) was built to get right over a single average-inclination
    scalar: F-1 builds to ~49.5° and holds; F-12 builds further to ~55°, and
    the two wells' azimuths are on nearly opposite headings (~302° vs ~106°)
    for most of their length. `score_trajectory(F-12, F-1) = 0.6655` —
    meaningfully below 1.0, correctly differentiating two real wells that
    share a field and well type but not a trajectory shape. Sanity check:
    `score_trajectory(F-1, F-1) = 1.0` exactly, confirming self-comparison
    is not distorted by the same parsing/interpolation pipeline.
* **Status after this step:** M2 (offset-well trajectory relevance) and M4
  (stratigraphic correlation) validated against real directional-survey data
  for the first time — both the interpolation math and the DORS trajectory
  similarity scoring behave correctly on genuine data, not just the
  synthetic testbed. Next: M3 (search) using the real, now-correctly-labeled
  events from module 01's Step 13–16 fixes.

### Step 18: Real-Data Benchmark — M3 (Knowledge Search), Module 02
* **Date & Time:** 2026-09-29
* **Action:** A genuine cross-module real-data test: took the 119 real events
  extracted by module 01's now-fixed pipeline (Steps 13–16, real Volve
  documents) and ran them through module 02's actual
  `search/knowledge_search.py::search_events()` — the first time these two
  modules' real outputs have been chained together, not just each tested in
  isolation.
  - Reconciled module 01's `EventType` into module 02's `DrillingEvent`
    shape using the `to_hazard_type()` mapping built in Step 16 itself (a
    second, independent real use of that mapping beyond the enum-iteration
    check it got in Step 16). 117 of 119 events had a HazardType equivalent
    and loaded; 2 did not (per Step 16's documented `None` cases) and were
    correctly excluded rather than silently coerced.
  - Built a small ground-truthed query set (`real_data/validate_m3_search.py`)
    by actually reading the real narratives for matching content first, not
    guessing — e.g. found 4 near-duplicate real events describing the same
    Draupne Formation pack-off incident (a real provenance artifact: both
    `WELL-15_9-F-1_MUD_LOG.pdf` and `WELL-15_9-F-1_MUD_LOG_COMBINED.pdf` were
    ingested from Step 13 and turned out to contain the same underlying
    report content, producing duplicate events — noted honestly here rather
    than silently left unexplained).
  - **Result: `search_mode: "semantic"` genuinely ran** (sentence-transformers
    loaded successfully, not the keyword fallback), and **Hit@5 = 2/2** on
    the ground-truthed queries:
    - `"pack off in Draupne formation"` → top result 0.674 cosine similarity,
      all 4 ground-truth duplicate events placed in the top 5.
    - `"stuck pipe freed with heavy overpull"` → top result 0.765, correctly
      ranked the exact "150 Tons overpull" events above a real but genuinely
      less-relevant "25 t overpull" tight-hole event.
    - A third, unlabeled query (`"gas show while tripping out of hole"`) — no
      fixed ground truth, but all 5 results returned were real, genuine
      trip-gas narratives with no off-topic results, sensibly ranked by
      cosine similarity (0.517 down to 0.432).
  - **Honestly scoped smaller than the methodology this was modeled on** — the
    PS-outcome research pass earlier found published petroleum-RAG papers use
    ~30-40 hand-labeled queries at this kind of benchmark; this pass used 3,
    limited by how much real, distinct event content exists in the 119
    events pulled so far. Stated as a real limitation, not glossed over.
* **Status after this step:** M3 validated against real data end-to-end,
  chaining module 01's real extraction directly into module 02's real search
  for the first time. M5 (predictive risk) and M6 (real-time alerts)
  considered next, but **honestly not attempted with the current real-data
  pull**: M5's leave-one-well-out methodology needs real labeled events
  spread across many wells to produce a meaningful number of folds, and the
  current pull covers only ~5 wells' worth of narrative events — forcing a
  benchmark on that would produce a number without real statistical meaning,
  which this log has consistently avoided doing elsewhere. Flagged as
  needing a broader real-data pull (the WITSML XML per-well data already
  located in the Volve share, not yet retrieved) before attempting, rather
  than run a low-value exercise just to have a number.

### Step 19: Broader Real-Data Validation — M2/M4 at Scale (22 Real Wells,
Proper WITSML XML)
* **Date & Time:** 2026-09-29
* **Action:** User pulled the broader WITSML XML trajectory data flagged as
  needed in Step 18 (all wells' `trajectory`/`log` folders from the same
  Volve Databricks share, not just the 2 hand-picked PDF reports). Two real
  bugs surfaced in the pull script itself before the data was usable:
  - `IsADirectoryError` — some wells' `log/` folders contain numbered
    subfolders (`log/1/`, `log/2/`, different survey runs) rather than files
    directly; the first pull script assumed a flat listing. Fixed by
    switching to `shutil.copytree()` (handles arbitrary nesting) instead of
    a manual `listdir()` + `copy()` loop.
  - Result: 181 real files across ~20 wells.
  - Wrote `real_data/parse_witsml_trajectories.py` — proper WITSML 1.4.1.1
    XML parsing via `xml.etree.ElementTree` (namespace-aware), extracting
    `<trajectoryStation>` elements directly into module 02's exact
    `SurveyStation` shape (`md`/`tvd`/`incl`/`azi`/`dispNs`/`dispEw` map
    1:1 — no heuristic column-order inference needed, unlike the PDF
    parsing in Step 17, since this is real structured data). Handled two
    real data-shape findings: multiple XML files per wellbore are different
    survey RUNS over overlapping MD ranges, not one continuous log (merged
    and de-duplicated by MD); the same physical well appears under multiple
    name-string variants across different real records (e.g. `"15/9-F-12"`
    vs `"NO 15/9-F-12"` — different service companies'/eras' naming
    conventions in the source data, left as distinct entries rather than
    silently merged, since it's not certain without deeper investigation
    that they represent identical wellbores).
  - **Result: 22 real wells with usable trajectory data**, several spanning
    nearly the full well depth with hundreds of real stations (F-11: 564
    stations to 4770m; F-10: 575 stations to 5300m) — a substantially
    broader real dataset than Step 17's 2 wells.
  - **Bulk interpolation-accuracy check**: 100 random real bracket midpoints
    across all 22 wells — **98/100 correct** (interpolated TVD fell within
    the real station-to-station bracket). The 2 "failures" were small
    overshoots (~1-2m past the bracket edge) at points of significant
    trajectory curvature — investigated rather than dismissed: minimum
    curvature, unlike linear interpolation, is not guaranteed to be
    perfectly monotonic between two stations when the wellbore is
    curving meaningfully between them, so a small overshoot there is
    plausibly correct physics colliding with a naive "must stay in the
    linear bracket" check, not necessarily a bug. Reported honestly as an
    open question rather than claimed as a clean 100%.
  - **Pairwise `score_trajectory` across 6 real well combinations,
    hand-selected to test both "should score similar" and "should score
    very different" cases**:
    | Pair | Max inclinations | Score |
    |---|---|---|
    | F-4 vs F-5 | 55.2° vs 55.1° (near-identical build) | **0.7917** |
    | F-15A vs F-15B | 33.8° vs 60.4° | 0.8720 |
    | F-12 vs F-14 | 55.2° vs 81.1° | 0.7439 |
    | F-12 vs F-15 | 55.2° vs 85.8° | 0.7058 |
    | F-9 vs F-9 A | 11.6° vs 59.1° | 0.6016 |
    | **F-10 vs F-11** | **88.1° (near-horizontal) vs 1.6° (near-vertical)** | **0.4651 (lowest of all pairs tested)** |
    The two most physically dissimilar real wells in the set (F-10, nearly
    horizontal; F-11, nearly vertical) correctly scored lowest — the exact
    behavior the Hausdorff-profile approach exists to get right.
  - **Full real ranking**: scored all 21 other real wells against F-12 as
    the active well. Real, non-degenerate spread from 0.5900 to 0.8751, no
    ties, no collapse to a single value. One honest observation flagged, not
    resolved: the `"NO 15/9-*"`-prefixed name-variant wells cluster near the
    bottom of the ranking (0.59–0.61) somewhat uniformly — plausibly a real
    trajectory-shape signal, but also plausibly a data-quality confound if
    those particular XML records have a different/truncated MD coverage
    than their counterparts. Not investigated further this pass; noted so
    it isn't mistaken for a clean, fully-explained result.
* **Status after this step:** M2/M4 now validated against 22 real wells (up
  from 2), with the DORS trajectory scoring shown to behave correctly across
  genuinely varied real trajectory shapes, not just one pair. M5/M6 remain
  open — this pull's `log/` folders turned out to contain only metadata
  (`MetaFileInfo.txt`), not actual curve/event data, so real hazard-event
  depth data for M5/M6 still isn't available from this source; module 01's
  extracted narrative events (Steps 13–16) remain the only real event source
  so far, and their well-coverage is still the limiting factor flagged in
  Step 18.

### Step 20: PS 26121 Word-By-Word Gap Analysis, Then Real-Data Extraction
For 5 Missing Parameters
* **Date & Time:** 2026-09-29
* **Action:** User asked for the PS to be re-read word-by-word against the
  actual schemas (not the earlier, partially-inaccurate third-party audit
  that had been pasted in), to find any named parameters with no
  implementation. Cross-checked every hazard/data-category the PS names
  explicitly (problem-description item iii; expected-outcome item v;
  relevant-data item viii/ix) against `HazardType`/`EventType`
  enums and the `Well`/`FormationTop`/`DrillingEvent`/`CasingRecord`
  schemas directly (not from memory or the audit) — found 5 real gaps:
  1. **Overpressure zones** (outcome v) — no hazard type existed at all,
     despite `pore_pressure_gradient_ppg` already being a field.
  2. **Fishing operations** (relevant-data ix) — no event type existed.
  3. **Casing programs** (problem-description iii) — module 01 already had
     a `CasingRecord` schema (`casing_size_inches`, `shoe_depth_md_m`,
     `top_of_cement_md_m`) but grepping the codebase found zero call sites
     anywhere — the entity extractor's own `extract_all_entities()`
     literally had `"casing_records": [],  # Implemented in phase 2`.
     Modeled, never wired — the same shape of gap as the stratigraphic
     endpoint found in Step 17's era.
  4. **Cementing practices** (problem-description iii) — `CEMENTING_FAILURE`
     existed as a hazard *classification* but no data field to correlate
     actual cementing practice against; `top_of_cement_md_m` existed on the
     unwired `CasingRecord` above.
  5. **Reservoir characteristics** (problem-description iii) — no
     porosity/permeability/water-saturation field existed anywhere.
  - **Before writing any code, checked whether real data actually supports
    each gap** (the same discipline as every other step in this log) by
    keyword-scanning the 14 real Volve PDFs with PyMuPDF: overpressure (2
    real docs, genuine bar-vs-gradient findings), casing (9 real docs,
    strong table data), cementing (5 real docs), reservoir characteristics
    (6 real docs, up to 36 real matches in one document) all confirmed
    real. **Fishing operations: zero matches across all 14 documents** —
    the only one of the 5 not validated against real data.
  - **Added, matched across both modules**: `EventType.OVERPRESSURE_ZONE`
    / `HazardType.OVERPRESSURE_ZONE` (module 01/02), `EventType.
    FISHING_OPERATION` (module 01 only — deliberately no HazardType
    equivalent, same reasoning as EQUIPMENT_FAILURE: an operational
    response to a prior failure, not itself a formation-tied geological
    hazard), `FormationTop.porosity_pct` / `.permeability_md` / `.
    water_saturation_pct` (both modules), extended `EVENT_TYPE_TO_HAZARD_TYPE`.
  - **Wrote and validated 3 new real extraction functions** in
    `tier3_entity_extractor.py` against the real documents identified
    above, iterating through real bugs exactly as every prior extraction
    step in this log has:
    1. `extract_casing_records()` — **3 real bugs found and fixed**,
       not zero: (a) fractional casing sizes ("13 3/8") were being turned
       into the string "13.3/8" by a naive space-to-dot replace, which
       `float()` correctly rejects, silently dropping every fractional
       casing size — real casing programs are almost always fractional
       (13 3/8", 9 5/8", 7"). Fixed with a real fraction parser. (b) The
       separator between the MD and TVD number groups was fully optional
       (`\s*\|?\s*`, matchable as zero characters), so a real row with
       only ONE number after it (a liner shoe with no TVD listed, real
       case: `'9 5/8" Casing shoe\n3090'`) got matched by splitting the
       single contiguous digit string into two arbitrary halves ("30" +
       "90") instead of correctly failing to match — found by directly
       inspecting the regex's captured groups against the real text, not
       assumed correct after the count looked plausible. Fixed by
       requiring at least one real separator character, plus a genuine
       single-number fallback pattern so that real row isn't dropped
       either. (c) A near-duplicate real row (2570.7 vs 2570.0 for the
       same physical 14" string in WELL-15_9-F-12_COMPLETION.pdf) survives
       as two records because exact-float dedup doesn't catch a ~0.7m
       rounding difference — disclosed honestly, not silently merged or
       hidden.
    2. `extract_reservoir_properties()` — **1 real bug found and fixed**:
       the first "permeability...mD" match in
       `WELL-15_9-F-1_PETROPHYSICAL.pdf` was *"cut offs correspond to a
       overburden corrected core permeability of 0.5 mD, and are also
       applied for the other formations"* — a methodology CUTOFF
       threshold, not an actual reservoir reading. The exact same class of
       mistake as formation-tops originally matching methodology prose
       instead of a real data table. Fixed by skipping any match within 60
       characters of "cut off"/"cutoff"/"cut-off" and checking all matches
       (not just the first) for a genuine one. **Honest residual
       limitation, not fixed**: `WELL-15_9-F-1_PETROPHYSICAL.pdf` — the
       one document whose entire purpose is reservoir characterization (28
       real porosity mentions, 28 permeability, 14 water-saturation per
       the keyword scan) — still yields **zero** extracted values after
       the fix, because nearly every real mention there is methodology
       prose explaining *how* porosity is derived (*"Total porosity, PHIF,
       is derived from the density log..."*) rather than a headline value
       statement the regex can anchor on. The two completion reports
       (which state porosity as a single narrative sentence: *"porosity of
       0.17"*) work; the dedicated petrophysical report does not. Stated
       plainly rather than glossed over.
    3. `EventType.OVERPRESSURE_ZONE` keyword matching — deliberately used
       only the unambiguous "overpressur" stem, not "abnormal pressure":
       a real match for that exact phrase in
       `WELL-15_9-19B_END_OF_WELL_REPORT.pdf` turned out to be a NEGATIVE
       case (*"the losses were **not** due to abnormal pressure
       conditions"*) — the same false-positive shape kick/kickoff had in
       Step 13 — so it was excluded before it ever caused a wrong
       classification, rather than found and fixed after the fact.
  - **Final real tallies across all 14 real Volve documents**:
    | Metric | Value |
    |---|---|
    | Real casing records extracted | 10, across 3/14 documents |
    | Real reservoir-property readings | 2/14 documents (both completion reports) |
    | Real overpressure events | 5, all in 1/14 documents (`WELL-15_9-F-1A_COMPLETION.pdf`), 100% genuine on inspection |
    | Fishing operations | 0/14 — schema added, not real-data-validated |
  - **Explicitly out of scope this step, stated rather than silently
    skipped**: module 02's DORS 5-factor formula and the risk corridor
    engine were NOT modified to actually weight/use these 5 new fields in
    scoring — that's a deliberate, separate architectural decision (DORS's
    weights are an established, already-validated formula; changing them
    needs its own explicit discussion, not a silent side effect of a
    schema addition). What exists after this step: the fields are real,
    extractable, and schema-ready on both modules — not yet consumed by
    any scoring engine.
* **Status after this step:** All 5 PS-named gaps found in the word-by-word
  audit now have real schema support; 4 of 5 (overpressure, casing,
  cementing's top-of-cement field, reservoir characteristics) are validated
  against real Volve data with real bugs found and fixed during that
  validation. Fishing operations has schema support only — honestly
  disclosed as unvalidated against real data, since the current 14-document
  pull contains none. Downstream scoring-engine integration (making DORS/
  risk-corridor actually use these fields) remains open and was explicitly
  scoped out of this step rather than rushed in.

### Step 21: Wiring the 5 New Fields Into Live Scoring — Real Gaps Found,
Not Just a Mechanical Pass
* **Date & Time:** 2026-09-29
* **Action:** User asked for Step 20's schema additions to be wired into
  live scoring "completely" rather than left as inert fields. Read the
  actual engine code first (`dors_engine.py`, `risk_corridor_engine.py`,
  `hazard_predictor.py`, `orchestrator.py`) before changing anything, to
  find genuine integration points rather than force every new field into
  DORS's already-validated 5-factor formula just because it was possible.
  - **Found the real, load-bearing gap, not a cosmetic one**:
    `orchestrator.py`'s `ALL_HAZARDS` — the literal list the live
    `/api/v2/analyze` endpoint loops over to build every well's hazard
    assessment — was a **hardcoded list of 5**, not derived from the
    `HazardType` enum. It was missing `OVERPRESSURE_ZONE` (expected, just
    added in Step 20) **and `CEMENTING_FAILURE`, which has existed in the
    enum since before this session** — meaning `/api/v2/analyze` has never
    once computed a cementing-failure risk assessment for any well, ever,
    until this fix. Found by tracing the actual call path
    (`assess_hazard()` → its one real call site → the loop that drives it)
    rather than assuming the enum addition alone would be sufficient.
  - Every OTHER engine already derived hazard coverage dynamically
    (`risk_corridor_engine.py`'s 4-pillar dict comprehension:
    `{h.value: 0.0 for h in HazardType}`) or degrades safely on an unknown
    hazard type (`hazard_predictor.py`'s `HIGH_RISK_FORMATIONS.get()`) —
    `ALL_HAZARDS` was the one place a real gap could hide silently.
  - **Added a genuine, not fabricated, sensor-anomaly signal for
    OVERPRESSURE_ZONE** in `compute_sensor_anomaly()`: the d-exponent
    (`TelemetryRecord.d_exponent` — already existed in the schema, unused
    until now) is the real, standard petroleum-engineering real-time
    overpressure indicator — a DECREASING d-exponent trend below the
    normal compaction line signals entering an undercompacted,
    overpressured zone. Implemented as a directional trend comparison
    (recent 5-sample average vs. prior baseline), not the same undirected
    z-score helper the other hazards use, since direction specifically
    matters here and the existing helper doesn't distinguish it.
  - Added real mitigation-action text for `OVERPRESSURE_ZONE` in both
    places recommended actions are looked up (`_build_corridor`,
    `assess_hazard`) — mud-weight/d-exponent/connection-gas/kill-mud
    guidance, the standard real response, not placeholder text.
  - Added `OVERPRESSURE_ZONE: {"Kopili", "Barail Coal-Shale"}` to
    `hazard_predictor.py`'s heuristic formation-risk table — both formation
    names already established elsewhere in this codebase's domain rules
    (not newly invented), chosen because shale-dominated, undercompacted
    intervals are the same general geological reasoning already used for
    why they appear under STUCK_PIPE/WELLBORE_INSTABILITY above.
  - **Verified live, not just unit-level**: restarted module 02 fresh,
    called the real `GET /api/v2/analyze/WELL-NHK-001?depth=2500`
    endpoint, and confirmed both `CEMENTING_FAILURE` and
    `OVERPRESSURE_ZONE` now appear in the response with real computed
    composite scores and correct `m_ml_source: "heuristic_fallback"`
    attribution — not assumed correct from reading the code.
  - **Casing programs and reservoir characteristics — deliberately NOT
    forced into DORS or hazard scoring**, because neither is a hazard or a
    trajectory/formation-match signal DORS's formula was built to weigh;
    doing so would fabricate a relationship the PS doesn't actually ask
    for (PS iii asks to *correlate* casing programs and cementing
    practices, not score risk from them). Reservoir characteristics
    (`porosity_pct`/`permeability_md`/`water_saturation_pct`) are already
    live-servable with zero further work — they're fields on
    `FormationTop`, and `GET /api/v2/formations/{well_id}` already
    `model_dump()`s the whole object, so any real value Step 20's
    extractor finds is automatically exposed. Casing needed its own model
    on module 02's side to be servable at all — added `CasingRecord`
    (plain fields, mirroring module 01's `CasingRecord` but without the
    `ExtractedField` wrapper, matching this module's style) — but stated
    honestly in its own docstring that nothing populates it yet, since
    module 01 and module 02 still aren't connected (the same gap
    documented in `logger/09_VERIFIED_STATUS...md` §2.3). That connection
    is the separately-scoped Postgres/integration work, not silently
    implied as finished by adding a schema.
* **Status after this step:** `OVERPRESSURE_ZONE` and `CEMENTING_FAILURE`
  are now fully live in the per-well hazard assessment pipeline — real
  scores, real mitigation text, real (if heuristic-only) formation risk,
  verified end-to-end against the running server. Reservoir
  characteristics are live-servable with no further wiring needed.
  Casing/cementing correlation across wells has its module-02-side model
  ready but is genuinely blocked on the module 01↔02 connection, not
  glossed over as done.

### Step 22: Real-Data Hazard Model Retraining — Real Benchmarks, Genuinely
Mixed Results
* **Date & Time:** 2026-09-29
* **Action:** User asked to retrain the hazard prediction models on real
  data instead of the synthetic testbed, then find a way to validate and
  benchmark it honestly despite the small real sample found. Built
  `real_data/train_hazard_models_real.py`, reusing module 02's own
  `build_features()` (not reimplemented) so the real-data model goes
  through the exact same feature-extraction code as the synthetic one.
  - **Real data assembled**: re-ran module 01's fixed extraction (with
    `NWIS_FORMATION_PROFILE=NORTH_SEA_VOLVE` set — a real bug in my own
    reconnaissance script's first pass forgot this, producing 0 real
    formation tops until corrected) fresh against all 14 real Volve
    documents, yielding 33 real depth-tagged events (of 119 total real
    events — most narrative events simply don't state a depth) and 43 real
    formation tops, across 4 real wells: 15/9-F-1, 15/9-F-12, 15/9-F-1C,
    15/9-19B.
  - **A second real bug found in my own script**: a naive filename-based
    well-ID parser collapsed all 33 events into one bogus well bucket on
    Windows paths (backslash vs. the `/`-only split it assumed). Fixed
    with a proper regex bounded by known document-type suffixes
    (DRILLING/COMPLETION/MUD/TRAJECTORY/END/etc.), confirmed correct by
    checking the resulting per-well counts summed back to the real totals.
  - **Sourced 15/9-19B's trajectory, genuinely not found**: searched our
    own real WITSML pull (confirmed zero matches), 19B's own real 77-page
    End-of-Well-Report for an embedded survey table (confirmed none), and
    external sources (GitHub WITSML tutorials, academic Volve papers,
    dedicated Volve-analysis sites) — no source confirms structured
    trajectory data exists for 19B anywhere in the public release. Plausible
    reason found, not just assumed: 19B is part of the field's original
    1993-era discovery/appraisal well cluster (15/9-19 S → SR → A → B),
    logged with MWD/wireline before WITSML real-time logging was standard
    practice — the real WITSML trajectories we do have are all later
    F-series field-development wells. Not fabricated or approximated as a
    workaround.
  - **Real, disclosed methodology deviation to reach the training
    threshold**: module 02's live `build_training_dataset()` hard-excludes
    any well with no real trajectory. Wrote `build_training_dataset_soft()`
    which instead uses `build_features()`'s own documented 0.0-inclination
    fallback for exactly this case, so 19B's real events aren't dropped
    entirely — but every row built this way is tagged, counted, and
    reported (19/55 rows for STUCK_PIPE, 18/53 for WELLBORE_INSTABILITY use
    the fallback), not silently blended in as equivalent to a real
    trajectory reading.
  - **Real leave-one-well-out CV, reported PER FOLD, not just a mean** —
    the extra validation step the user asked for, since a single mean can
    hide real instability with only 3 wells:

    | Hazard | Fold (held-out well) | Real AUC |
    |---|---|---|
    | STUCK_PIPE | 15/9-19B | 0.683 |
    | STUCK_PIPE | 15/9-F-1 | 0.633 |
    | STUCK_PIPE | 15/9-F-1C | 0.667 |
    | **STUCK_PIPE mean** | (3 folds, 55 rows) | **0.661** (synthetic: 0.622) |
    | WELLBORE_INSTABILITY | 15/9-19B | 0.578 |
    | WELLBORE_INSTABILITY | 15/9-F-1 | 0.667 |
    | WELLBORE_INSTABILITY | 15/9-F-1C | 0.400 |
    | **WELLBORE_INSTABILITY mean** | (3 folds, 53 rows) | **0.548** (synthetic: 0.606) |

    **Honest read, not glossed over**: STUCK_PIPE's real result is
    consistent across all 3 folds (0.63–0.68) and slightly *beats* the
    synthetic model — a genuine, if small, real signal. WELLBORE_INSTABILITY
    is NOT consistent (0.40–0.667, a 26-point swing) and its mean is both
    worse than synthetic AND close to random guessing (0.5) — the per-fold
    view is what reveals this; the mean alone would have hidden it. This
    real model should not be presented as reliable.
  - **A second, sample-size-independent validation layer**: inspected the
    trained models' actual coefficients (standardized feature space) for
    physical sensibility, per the user's request to find additional real
    ways to validate. **Real, structural finding**: `pore_pressure_ppg` and
    `formation_group_code` came out at ~0.000 for BOTH hazard types — the
    model learned nothing from either. Root cause traced, not just
    observed: module 01 does not extract a real per-formation pore-pressure
    gradient, so every real formation top in this training set carries
    module 02's constant regional default (9.0 ppg) — a model cannot learn
    a relationship from a feature that never varies, the exact same
    documented limitation the codebase already discloses for mud_weight/
    overbalance (`ml/feature_engineering.py`'s own module docstring). This
    means 2 of the 5 real features are currently inert with real data, and
    the real signal that exists (STUCK_PIPE's 0.661) is coming from depth,
    well_type, and inclination alone.
  - Saved real models separately (`real_data/real_trained_models/*_REAL.joblib`)
    rather than overwriting the deployed synthetic ones — this is a
    benchmark result to inform a deployment decision, not a silent swap.
* **Status after this step:** Real, honest benchmarks now exist for
  STUCK_PIPE and WELLBORE_INSTABILITY, validated two independent ways
  (per-fold real leave-one-well-out CV, and a physics-coefficient sanity
  check) rather than one number taken at face value. STUCK_PIPE's real
  result is usable and slightly better than synthetic. WELLBORE_INSTABILITY's
  is not reliable at the current real sample size. The concrete next lever
  to actually improve both, identified and not yet pulled: extract real
  per-formation pore pressure (currently a module 01 gap) and/or pull more
  of the ~1,759 real Volve DDRs beyond the 14 processed so far — the real
  root cause of both the small-N problem and the inert pore-pressure
  feature is breadth of real data pulled, not a modeling choice.

### Step 23: Real Casing/Cementing Cross-Module Wiring (Without the Full
Postgres Migration)
* **Date & Time:** 2026-09-29
* **Action:** Closed the casing/cementing cross-module gap flagged at the
  end of Step 21 — proportionately, not via the full (still-paused)
  Postgres migration. Re-extracted real `CasingRecord` data across all 14
  real Volve documents (not just the 4-well ML-training subset from Step
  22): **10 real casing records across 2 real wells** (15/9-F-12: 6,
  15/9-F-1A: 4).
  - Added `casing_records_by_well` to `data_store.py`, loaded from a
    dedicated `real_data/real_casing_records_all.json` path (not
    `data/synthetic/`) — kept explicitly separate from the synthetic
    Assam-Arakan testbed, which these real Volve wells have nothing to do
    with; additive, not merged/fabricated onto synthetic well IDs.
  - Added `GET /api/v2/casing/{well_id}` and `GET /api/v2/casing` (list of
    every well with real casing data) — the actual live cross-module wire
    for PS 26121 item (iii)'s "correlate casing programs, cementing
    practices" ask.
  - **A real routing bug found while testing live, not assumed working from
    the code**: real Volve well IDs contain a literal `/` (e.g.
    `15/9-F-12` — the field's actual block/well naming convention).
    FastAPI's default `{well_id}` path parameter doesn't match a decoded
    slash even when URL-encoded (`%2F`) in the request — confirmed by
    getting a generic, route-level 404 rather than this endpoint's own
    detailed one. Fixed with the `{well_id:path}` converter. This is the
    first endpoint in this API to ever serve a real Volve-style well ID,
    so the bug had no chance to surface before now — worth checking
    whether `/api/v2/formations/{well_id}` and others have the same latent
    issue if real well IDs are ever queried there too.
  - **Verified live against the running server**, not just code review:
    `GET /api/v2/casing` correctly lists both real wells; `GET
    /api/v2/casing/15%2F9-F-12` returns all 6 real records; `GET
    /api/v2/casing/WELL-NHK-001` (a synthetic well) correctly 404s with an
    honest message rather than fabricating an empty-but-200 response.
* **Status after this step:** Casing/cementing data now has a genuine,
  live, real cross-module path — module 01's real extraction feeds a real
  module 02 endpoint. The full Postgres migration (automatic, live sync of
  *any* newly-uploaded document's casing data) remains the larger,
  separately-scoped item this proportionate fix does not replace.

### Step 24: Deployed the Real STUCK_PIPE Model, Kept WELLBORE_INSTABILITY
on Synthetic — a Deliberate, Verified Decision
* **Date & Time:** 2026-09-29
* **Action:** Closed the second item from the user's "do sequentially"
  list. Before deploying anything, traced exactly why
  WELLBORE_INSTABILITY's worst real CV fold (15/9-F-1C, AUC=0.400) was so
  bad: that held-out well has exactly **1** real positive example, so that
  fold's AUC reduces to "did the model rank one single case above the
  negatives" — an inherently near-coin-flip statistic, not necessarily
  evidence the model itself is broken. A more precise, honest
  characterization than a blanket "unreliable," but the conclusion is the
  same: not enough real data yet to trust it.
  - **Deployed STUCK_PIPE's real model** (Step 22's benchmark: 0.661 mean
    AUC, consistent 0.63–0.68 across all 3 real folds, genuinely beating
    synthetic's 0.622).
  - **A real, genuine format bug caught before it could silently break
    inference**: the real training script (Step 22) saved models under key
    `"pipeline"`; `hazard_predictor.py`'s actual consuming code
    (`entry["model"].predict_proba(...)`) expects key `"model"`. Found by
    reading the real consumer code, not assumed compatible. Fixed by
    re-saving in the exact expected format before deployment, rather than
    copying the file as-is and finding out at runtime.
  - **Backed up the synthetic model first**
    (`stuck_pipe_model_SYNTHETIC_BACKUP.joblib`) — reversible, not a
    destructive overwrite.
  - **Left `wellbore_instability_model.joblib` completely untouched** —
    the deliberate decision, not an oversight.
  - **Verified live, not just via the sanity-check inference call**:
    restarted the server fresh, called the real `/api/v2/analyze`
    endpoint, and confirmed STUCK_PIPE's composite score actually changed
    (0.3392 → 0.2748) — proof the real model is genuinely driving live
    inference, not just sitting on disk — while WELLBORE_INSTABILITY's
    score and `trained_model` source stayed exactly as before (still the
    original synthetic model).
* **Status after this step:** STUCK_PIPE is now live on real Volve data.
  WELLBORE_INSTABILITY stays on synthetic, correctly and deliberately, with
  the specific reason (single-positive-example test fold) documented
  rather than left as a vague "small sample" excuse.

---
*This log will be continuously updated throughout the development lifecycle.*

