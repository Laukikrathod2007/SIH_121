"""
NWIS Module 01 — Cloud Parser Fallback (Reducto / Extend.ai)

STRATEGIC NOTE — read before enabling this in front of evaluators:
This module's whole reason to exist contradicts the project's own "100%
air-gapped, DGH-sovereignty-compliant" pitch (see benchmarks/run_benchmark.py
and logger/00_PROJECT_OVERVIEW_AND_PS_DECODED.md) — Reducto and Extend.ai are
commercial cloud APIs, and a page routed through either one leaves the local
boundary. That tradeoff was made deliberately: local-only extraction quality
depends on Docling being installed (it usually isn't, in this environment),
and a low-confidence/garbled result is worse for a system whose entire
purpose is trustworthy drilling-risk data than falling back to a paid API for
just the pages that need it. The fallback is therefore:
  - OFF by default unless an API key is actually configured (see below) —
    a document processed with no keys set behaves EXACTLY as before this
    module existed. Zero network calls, zero behavior change, zero risk.
  - Applied per-PAGE, not per-document — a document with 73 confident native
    pages and 1 low-confidence scanned page only sends that 1 page's content
    externally (see orchestrator.py's per-page confidence check).
  - Fully audited — every page that used a cloud provider is tagged via
    PageExtractionResult.extraction_source, and the document-level
    cloud_fallback_pages_count / cloud_fallback_providers_used fields make it
    visible at a glance whether ANY page left the air-gapped boundary.
  - Never fatal — every network call is wrapped, timed out, and logged; any
    failure (no key, network down, bad response, rate limit) just means the
    page keeps its local (possibly lower-confidence) result. This module can
    never make the pipeline crash or hang.

CONFIGURATION (all via environment variables — nothing here requires a code
change to enable/disable/tune):
    NWIS_CLOUD_FALLBACK_ENABLED           default "true" — master kill-switch
    NWIS_REDUCTO_API_KEY                  unset by default — no key, no calls
    NWIS_EXTEND_API_KEY                   unset by default — no key, no calls
    NWIS_EXTEND_WORKSPACE_ID              optional, only needed for org-scoped Extend keys
    NWIS_CLOUD_FALLBACK_CONFIDENCE_THRESHOLD   default 0.75 — pages below this trigger fallback
    NWIS_CLOUD_FALLBACK_TIMEOUT_SECONDS   default 30 — hard timeout per HTTP call

PROVIDER ORDER: Reducto is tried first (if its key is set), then Extend.ai
(if Reducto's key is unset, or Reducto's call failed). Both keys can be set
at once for automatic failover.

ACCURACY NOTE: the request/response shapes below are built from Reducto's and
Extend.ai's published API documentation (docs.reducto.ai, docs.extend.ai) as
of 2026-09-28. Neither has been exercised against a live account/key in this
environment — no key was available to test with. Before relying on this in a
real run, do a smoke test against a real key (see `if __name__ == "__main__"`
below) and fix any drift between the docs and the live API's actual behavior.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, TypedDict
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Load module_root/.env if present, so NWIS_REDUCTO_API_KEY / NWIS_EXTEND_API_KEY
# can live in a local, git-ignored file instead of requiring shell env vars to
# be set in every terminal session. Real environment variables always win
# (override=False) — a value already exported in the shell is never clobbered
# by .env. Safe no-op if python-dotenv isn't installed or no .env exists.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Configuration (read once at import time; env vars set after process start
# won't be picked up — restart the server to change these)
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "off", "")


CLOUD_FALLBACK_ENABLED = _env_bool("NWIS_CLOUD_FALLBACK_ENABLED", True)
REDUCTO_API_KEY = os.environ.get("NWIS_REDUCTO_API_KEY", "").strip()
EXTEND_API_KEY = os.environ.get("NWIS_EXTEND_API_KEY", "").strip()
EXTEND_WORKSPACE_ID = os.environ.get("NWIS_EXTEND_WORKSPACE_ID", "").strip()
# Extend.ai requires this header for any API key created after 2025-04-21
# (confirmed live: an unversioned request returns 400 INVALID_REQUEST,
# "Missing x-extend-api-version version header"). Keep this current per
# https://docs.extend.ai/api-reference/api-versioning.
EXTEND_API_VERSION = os.environ.get("NWIS_EXTEND_API_VERSION", "2026-02-09").strip()
CONFIDENCE_THRESHOLD = float(os.environ.get("NWIS_CLOUD_FALLBACK_CONFIDENCE_THRESHOLD", "0.75"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("NWIS_CLOUD_FALLBACK_TIMEOUT_SECONDS", "30"))

REDUCTO_BASE_URL = "https://platform.reducto.ai"
EXTEND_BASE_URL = "https://api.extend.ai"


class CloudPageResult(TypedDict):
    provider: str          # "reducto" | "extend_ai"
    pages: dict            # {0-indexed page_number: extracted text}
    page_confidence: float  # confidence to assign to any page filled from this result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cloud_fallback_configured() -> bool:
    """True if the master switch is on AND at least one provider has a key set."""
    return CLOUD_FALLBACK_ENABLED and HTTPX_AVAILABLE and bool(REDUCTO_API_KEY or EXTEND_API_KEY)


def should_use_cloud_fallback(page_confidence: float) -> bool:
    """
    Whether a page at this confidence level should be re-processed via a
    cloud fallback provider. Returns False immediately (no further checks,
    no logging noise) if no provider is configured — this is the hot path
    for every document processed without API keys, i.e. every document
    processed in this environment today.
    """
    if not cloud_fallback_configured():
        return False
    return page_confidence < CONFIDENCE_THRESHOLD


def get_cloud_parse_for_document(pdf_path: Path) -> Optional[CloudPageResult]:
    """
    Upload + parse the WHOLE document via the cloud fallback ONCE (not once
    per low-confidence page — both providers bill per page/credit, and
    re-uploading the same file for every flagged page would be wasteful and
    slow). Callers should memoize this per document and slice out the pages
    they actually need. Returns None if unconfigured or if every configured
    provider failed.
    """
    if not cloud_fallback_configured():
        return None

    if REDUCTO_API_KEY:
        result = _try_reducto(pdf_path)
        if result is not None:
            return result
        logger.warning(f"Cloud fallback: Reducto failed for {pdf_path.name}, trying next provider")

    if EXTEND_API_KEY:
        result = _try_extend(pdf_path)
        if result is not None:
            return result
        logger.warning(f"Cloud fallback: Extend.ai failed for {pdf_path.name}")

    logger.warning(f"Cloud fallback: all configured providers failed for {pdf_path.name}")
    return None


# ---------------------------------------------------------------------------
# Reducto (https://docs.reducto.ai)
# ---------------------------------------------------------------------------

def _try_reducto(pdf_path: Path) -> Optional[CloudPageResult]:
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            with open(pdf_path, "rb") as f:
                upload_resp = client.post(
                    f"{REDUCTO_BASE_URL}/upload",
                    headers={"Authorization": f"Bearer {REDUCTO_API_KEY}"},
                    files={"file": (pdf_path.name, f, "application/pdf")},
                )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            file_id = upload_data.get("file_id") or upload_data.get("id")
            if not file_id:
                logger.warning(f"Reducto upload for {pdf_path.name} returned no file_id: {upload_data}")
                return None

            parse_resp = client.post(
                f"{REDUCTO_BASE_URL}/parse",
                headers={
                    "Authorization": f"Bearer {REDUCTO_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"input": file_id},
            )
            parse_resp.raise_for_status()
            data = parse_resp.json()

            chunks = data.get("result", {}).get("chunks", [])
            if not chunks:
                logger.warning(f"Reducto parse for {pdf_path.name} returned no chunks")
                return None

            # Group block content by its source page (bbox.page, 1-indexed
            # per Reducto's docs) so we can slice out individual pages later.
            # A chunk/block without a page number is dropped rather than
            # guessed at — silently misattributing OCR text to the wrong
            # page would be worse than just not using it.
            pages: dict[int, list[str]] = {}
            label_confidences: list[str] = []
            numeric_confidences: list[float] = []
            for chunk in chunks:
                for block in chunk.get("blocks", []):
                    page_1indexed = block.get("bbox", {}).get("page")
                    content = block.get("content", "")
                    if page_1indexed is None or not content:
                        continue
                    pages.setdefault(page_1indexed - 1, []).append(content)
                    if block.get("confidence"):
                        label_confidences.append(block["confidence"])
                    # Confirmed against a live key: blocks also carry a
                    # granular_confidence.parse_confidence float (0-1), which
                    # is more precise than the high/low label alone.
                    parse_conf = (block.get("granular_confidence") or {}).get("parse_confidence")
                    if isinstance(parse_conf, (int, float)):
                        numeric_confidences.append(float(parse_conf))

            if not pages:
                logger.warning(f"Reducto parse for {pdf_path.name}: no block had a page number")
                return None

            page_texts = {p: "\n".join(parts) for p, parts in pages.items()}
            if numeric_confidences:
                conf_score = sum(numeric_confidences) / len(numeric_confidences)
            elif label_confidences:
                conf_score = 0.90 if all(c == "high" for c in label_confidences) else 0.75
            else:
                conf_score = 0.75

            logger.success(
                f"Reducto fallback parsed {pdf_path.name}: {len(page_texts)} page(s) recovered"
            )
            return {"provider": "reducto", "pages": page_texts, "page_confidence": conf_score}

    except Exception as exc:
        logger.warning(f"Reducto fallback raised for {pdf_path.name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Extend.ai (https://docs.extend.ai)
# ---------------------------------------------------------------------------

def _try_extend(pdf_path: Path) -> Optional[CloudPageResult]:
    try:
        headers = {
            "Authorization": f"Bearer {EXTEND_API_KEY}",
            "x-extend-api-version": EXTEND_API_VERSION,
        }
        if EXTEND_WORKSPACE_ID:
            headers["x-extend-workspace-id"] = EXTEND_WORKSPACE_ID

        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            with open(pdf_path, "rb") as f:
                upload_resp = client.post(
                    f"{EXTEND_BASE_URL}/files/upload",
                    headers=headers,
                    files={"file": (pdf_path.name, f, "application/pdf")},
                )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            # Confirmed against a live key (2026-02-09 API version): the
            # response is a flat file object with "id" at the top level, not
            # nested under "file" as older docs (pre-resource-based-API
            # rewrite) described. Check both so this survives either shape.
            file_id = upload_data.get("id") or upload_data.get("file", {}).get("id")
            if not file_id:
                logger.warning(f"Extend.ai upload for {pdf_path.name} returned no id: {upload_data}")
                return None

            parse_resp = client.post(
                f"{EXTEND_BASE_URL}/parse",
                headers={**headers, "Content-Type": "application/json"},
                # Confirmed against a live key (2026-02-09 API version): the
                # file reference field is "file": {"id": ...}, not the older
                # docs' "file": {"fileId": ...} — that shape 400'd with
                # "Invalid input; Path: file".
                json={
                    "file": {"id": file_id},
                    "config": {
                        "chunkingStrategy": {"type": "page"},
                    },
                },
            )
            parse_resp.raise_for_status()
            data = parse_resp.json()

            if data.get("status") == "FAILED":
                logger.warning(f"Extend.ai parse for {pdf_path.name} returned status=FAILED")
                return None

            # Confirmed against a live key (2026-02-09 API version): chunks
            # live under output.chunks, not top-level chunks as older docs
            # described.
            chunks = data.get("output", {}).get("chunks", [])
            if not chunks:
                logger.warning(f"Extend.ai parse for {pdf_path.name} returned no chunks")
                return None

            # With chunkingStrategy=page, chunk index i corresponds directly
            # to 0-indexed page i (chunk 0 = page 1).
            page_texts = {i: c.get("content", "") for i, c in enumerate(chunks) if c.get("content")}
            if not page_texts:
                return None

            logger.success(
                f"Extend.ai fallback parsed {pdf_path.name}: {len(page_texts)} page(s) recovered"
            )
            # The live API DOES expose a real per-chunk OCR confidence
            # (chunk.metadata.avgOcrConfidence) even though the docs we found
            # didn't document it — use the average across chunks rather than
            # a fabricated fixed estimate.
            chunk_confidences = [
                c["metadata"]["avgOcrConfidence"]
                for c in chunks
                if isinstance(c.get("metadata"), dict) and c["metadata"].get("avgOcrConfidence") is not None
            ]
            conf_score = sum(chunk_confidences) / len(chunk_confidences) if chunk_confidences else 0.80
            return {"provider": "extend_ai", "pages": page_texts, "page_confidence": conf_score}

    except Exception as exc:
        logger.warning(f"Extend.ai fallback raised for {pdf_path.name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Manual smoke test — run once you have a real API key to verify the request/
# response shapes above actually match the live API (they were built from
# published docs, not exercised against a live account).
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.cloud_fallback path/to/test.pdf")
        print(f"Configured: reducto_key={'yes' if REDUCTO_API_KEY else 'no'}, "
              f"extend_key={'yes' if EXTEND_API_KEY else 'no'}, "
              f"enabled={CLOUD_FALLBACK_ENABLED}")
        sys.exit(1)

    test_path = Path(sys.argv[1])
    if not cloud_fallback_configured():
        print("No provider configured — set NWIS_REDUCTO_API_KEY or NWIS_EXTEND_API_KEY first.")
        sys.exit(1)

    result = get_cloud_parse_for_document(test_path)
    if result is None:
        print("Both providers failed (or none configured) — see warnings above.")
        sys.exit(1)

    print(f"Provider: {result['provider']}")
    print(f"Pages recovered: {sorted(result['pages'].keys())}")
    for page_num, text in sorted(result["pages"].items())[:3]:
        print(f"--- page {page_num} (first 300 chars) ---")
        print(text[:300])
