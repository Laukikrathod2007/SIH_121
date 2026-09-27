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

---
*This log will be continuously updated throughout the development lifecycle.*

