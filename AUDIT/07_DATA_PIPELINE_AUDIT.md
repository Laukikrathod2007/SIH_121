# Data Pipeline Audit — Document Intelligence, Knowledge Search, Historical Data

**Date:** 2026-10-04
**Method:** Full pipeline trace through actual source code, plus a live end-to-end test: a real PDF was uploaded through module 01's real ingestion API during this audit and the complete result inspected.

---

## 1. Document-intelligence pipeline (module 01) — layer by layer

```
PDF → ingestion → native text extraction → scanned-page detection → OCR
    → cloud fallback → entity extraction → template learning
    → physics validation → review → JSON output → downstream consumer
```

| Layer | File | Technology (confirmed from imports) | Trigger | Real or simulated |
|---|---|---|---|---|
| Tier 1 — native extraction | `pipeline/tier1_native_extractor.py` | **PyMuPDF** (`import fitz`) | Every page, always attempted first | Real |
| Scanned-page detection | same file, `is_page_scanned()` | Heuristic: `char_count < 50 AND image_coverage > 60%` | Per page | Real (heuristic, not simulated — a real signal, just not perfect) |
| Tier 2 — OCR | `pipeline/tier2_ocr_engine.py` | **IBM Docling**, confirmed live via `/health`: `"docling":{"status":"ok"}` | At least one page fails Tier-1 scan check | Real |
| Cloud fallback | `pipeline/cloud_fallback.py` | Real HTTP (`httpx`) to Reducto and Extend.ai commercial APIs | `page_confidence < 0.75` AND a key is configured | **Real and currently LIVE on this checkout** — `modules/01_document_intelligence/.env` has both keys set, and the live `/health` endpoint confirms `"cloud_fallback":{"status":"configured","reducto_key_set":true,"extend_key_set":true,"master_switch_enabled":true}`. The module's own docstring claiming "100% air-gapped" and "never tested against a live account" is **stale/contradicted** — several inline code comments say request/response shapes were "confirmed against a live key," and the circuit is actively armed on this instance (though the specific live test document in this audit scored 0.99 confidence, so it did not fire) |
| Tier 3 — entity extraction | `pipeline/tier3_entity_extractor.py` | **Regex/keyword pattern matching — confirmed NOT NLP/NER/LLM.** Full import list: `re, time, typing, loguru` + internal schema/rule modules. Zero ML libraries. Live `/health` explicitly states spaCy (installed in the environment) is `"not currently used by the pipeline"` | Every page's extracted text | Real (as regex, not as "AI/NLP" — see note below) |
| Layer 4 — template learning | `pipeline/layer4_template_learner.py` | Pure Python/hashlib/JSON coordinate-fingerprint caching, MD5-based template IDs | Runs after every document | Real — "learning" here means positional-coordinate caching, not a trained statistical model |
| Layer 5 — physics validation | `pipeline/layer5_physics_validator.py` | Deterministic domain-rule checks (`models/domain_rules.py` constants) | Runs on every extracted numeric field | Real — confirmed live: a test document's deliberately-malformed "3.2 ppg" mud weight was auto-corrected to "13.2" and flagged `FAILED_PHYSICS_VALIDATION`, exactly as designed |

### Precise technology classification (per task's explicit instruction not to blur this)
- **OCR: genuinely real** (Docling, confirmed via import and live health check).
- **Entity extraction: genuinely regex/rules, NOT NLP/ML/LLM.** This is a real, working, and defensible engineering choice for a document-structure-extraction task, but calling it "NLP" or "AI" to a judge would be inaccurate. The module's own live health check is honest about this.
- **"Data analytics" (physics validation, template learning): real, deterministic, not ML.**

### Live end-to-end test performed this audit
```
POST /api/v1/ingest (real sample PDF)
  → {"job_id":"JOB-F33DC0296F","status":"QUEUED"}
GET /api/v1/jobs/JOB-F33DC0296F
  → {"status":"COMPLETED","message":"Completed: 1 pages | 3 events | Confidence: 99.0%"}
GET /api/v1/results/DOC-D2DBE26DF2D9
  → real structured JSON: well_name "NHK-105", 2 formation tops, 3 drilling events
    (STUCK_PIPE/MUD_LOSS/MUD_LOSS), mud_weight_ppg auto-repaired 3.2→13.2 with
    validation_status "FAILED_PHYSICS_VALIDATION", template_used fired (Layer 4),
    cloud_fallback_pages_count: 0 (not needed for this document)
```
This proves the full 6-layer chain runs live and produces real, internally-consistent output — not a stub.

---

## 2. Knowledge search pipeline (module 02)

```
documents/data → extraction (module 01) → normalization → storage/index
    → embedding → retrieval → result ranking → frontend
```

| Stage | Location | Technology |
|---|---|---|
| OCR | Module 01 only (see above) | Docling |
| Entity extraction | Module 01 only (see above) | Regex/keyword — NOT NLP |
| Embedding | `modules/02_nwis_backend/search/knowledge_search.py` | **Real** `sentence-transformers` model `all-MiniLM-L6-v2` (`_get_model()`, confirmed real import and live `search_mode: "semantic"` responses) |
| Vector search | same file | **NOT a real vector index.** A flat in-process Python dict (`_embedding_cache`) with a brute-force `for`-loop cosine-similarity scan — confirmed from the actual code, not assumed. The module's own docstring explicitly discloses this: "premature engineering at today's data volume" to build a real FAISS/pgvector index at ~44 events |
| Keyword fallback | same file, `_keyword_search()` | Triggered if the embedding model fails to load or the semantic path throws |

**Precision per task instruction**: the embedding step IS genuinely ML-based and can honestly be called AI; the brute-force similarity scan is NOT a production vector index, but is an honest and adequate choice at current scale. Module 01's regex extraction should never be called "NLP/AI" — this audit and the live health check both confirm it isn't.

### Live test
```
GET /api/v2/events/search?query=stuck pipe in sandstone
  → search_mode: "semantic", 44 total candidates, 10 returned, real relevance
    scores (top: 0.7707), results mix real Volve-sourced events with
    synthetic ones in one ranked list
```

---

## 3. Historical drilling intelligence data — real vs synthetic, precisely

- **Synthetic**: `modules/02_nwis_backend/data/synthetic/drilling_events.json` — exactly **39 events** (confirmed by direct count, matches the module's own docstring claim).
- **Real**: `real_data/real_events_depth_tagged_fresh.json` — 33 raw real depth-tagged events; after `data_store.py`'s load-time filter (must belong to a known real well AND have a non-null hazard_type) and dedup (collapsing the same real incident narrated across multiple source PDFs for the same well), **5 real events survive into the live store**.
- **Live-confirmed total**: `GET /api/v2/health` → `"events": 44"` — **exactly 39 + 5**, confirmed by partitioning a live full event pull by `event_id` prefix (`EVT-xxxxxxxx` = synthetic, `EVT-REAL-0xx` = real).
- This is accurately described as a **mixed store**: predominantly synthetic (39/44, ~89%), with a smaller real overlay (5/44, ~11%) — not a disguised or homogeneous dataset. `data_store.py`'s own comments are explicit and non-deceptive about this provenance (e.g., a comment explaining a dropped-formation-tops count as "a known reconnaissance-script parsing bug, not fabricated data being hidden").

### Evidence/citation PDFs
- `evidence-server/pdfs/`: **42 files** — 39 match the synthetic `DDR_WELL-*.pdf` naming convention, **3 are real Volve documents** (`WELL-15_9-F-12_COMPLETION.pdf`, `WELL-15_9-F-1_MUD_LOG.pdf`, `WELL-15_9-F-1_MUD_LOG_COMBINED.pdf`) — exact count re-confirmed this audit, unchanged from the prior pass.
- Citations in live search results resolve to these exact real filenames (e.g., `"source_document":"volve\\WELL-15_9-F-1_MUD_LOG.pdf"`) — not placeholders.
- `nwis-map-package/server/pdfs/` (the superseded vendored copy) has **39 files, synthetic-only, zero real Volve documents** — this is the original package before its evidence set was extended with real documents in the live `evidence-server/`.

---

## Unverified in this pass
- Whether `evidence-server`'s own HTTP endpoint was separately curled to confirm it serves these 42 files live (file existence and citation-string matching were confirmed; the live HTTP serve itself was separately confirmed in `AUDIT/04_E2E_VERIFICATION.md`'s evidence-viewer test, so this is cross-confirmed across audits, not actually open).
- Exact reconciliation of which specific real events were excluded by the dedup logic (the mechanism and the final count of 5 are both confirmed; a row-by-row accounting of the other ~21 raw real events' disposition was not performed).
- Whether `real_data/real_events_module01.json` (119 records, a broader extraction set) is consumed anywhere — grep found no `.py` reference to this exact filename outside `real_data/` itself. Likely an intermediate/broader artifact, not wired into the live store. Marked UNVERIFIED rather than asserted.
