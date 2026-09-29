"""
NWIS Module 02 — Searchable Knowledge Repository

Closes PS 26121 outcome iii: "Create a searchable knowledge repository of
drilling events, lessons learned, operational challenges, and mitigation
measures." The pre-existing GET /api/v2/events endpoint only filters on
structured fields (hazard_type, formation, depth range, severity) — it has
no way to answer something like "find events where a mud weight increase
fixed wellbore instability," which is exactly what "lessons learned" means:
searching the free text, not just the metadata.

Design:
  - Semantic search via sentence-transformers (all-MiniLM-L6-v2 — small, fast,
    well-established for this kind of short-document search) over each
    event's combined narrative + mitigation + outcome text.
  - Graceful degradation: if sentence-transformers isn't installed (or fails
    to load), falls back to case-insensitive keyword/substring matching over
    the same text — the search endpoint still works, just less semantically
    aware. Matches this project's established pattern (Module 01's cloud
    OCR fallback, Module 02's ML-model fallback) of a real capability with an
    honest, functional degradation path rather than a hard failure.
  - Embeddings are computed once per process and cached in memory — with
    only 39 synthetic events this is instant; if this ever needs to scale to
    a real multi-thousand-event archive, swap the flat cosine-similarity scan
    below for a proper vector index (e.g. FAISS/pgvector), but that's
    premature engineering at today's data volume.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
from dataclasses import dataclass

from loguru import logger
from models.schemas import DrillingEvent

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_model_load_attempted = False
_embedding_cache: dict[str, "np.ndarray"] = {}  # event_id -> embedding vector


def _searchable_text(event: DrillingEvent) -> str:
    """The single source of truth for what text an event is searched over —
    used identically whether embedding for semantic search or falling back
    to keyword search, so the two modes search the same content."""
    parts = [
        event.event_type.value.replace("_", " "),
        event.formation or "",
        event.raw_narrative or "",
        event.mitigation_description or "",
        event.outcome or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _get_model():
    """Lazy-load the embedding model. Returns None (triggering keyword
    fallback) if sentence-transformers isn't installed or fails to load —
    never raises, so a missing optional dependency can't take down search."""
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Loaded semantic search model: {EMBEDDING_MODEL_NAME}")
    except Exception as exc:
        logger.warning(
            f"sentence-transformers unavailable ({exc}) — knowledge search "
            "falls back to keyword matching. Install with: pip install sentence-transformers"
        )
        _model = None
    return _model


def _keyword_search(query: str, events: List[DrillingEvent]) -> List[Tuple[DrillingEvent, float]]:
    """Fallback: case-insensitive substring match, scored by how many of the
    query's words appear in the event's searchable text (crude but honest —
    no false claim of semantic understanding)."""
    query_words = [w for w in query.lower().split() if w]
    if not query_words:
        return [(e, 0.0) for e in events]

    scored = []
    for event in events:
        text_lower = _searchable_text(event).lower()
        hits = sum(1 for w in query_words if w in text_lower)
        if hits > 0:
            scored.append((event, hits / len(query_words)))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def search_events(
    query: str,
    events: List[DrillingEvent],
    top_n: int = 10,
) -> Tuple[List[Tuple[DrillingEvent, float]], str]:
    """
    Ranks `events` by relevance to `query`. Returns (ranked_results, mode)
    where mode is "semantic" or "keyword_fallback" — surfaced to the API
    response so callers know which search actually ran, not just that
    "search" happened (consistent with this project's m_ml_source /
    extraction_source transparency pattern elsewhere).
    """
    if not query or not query.strip():
        return [(e, 1.0) for e in events[:top_n]], "no_query"

    model = _get_model()
    if model is None:
        return _keyword_search(query, events)[:top_n], "keyword_fallback"

    try:
        import numpy as np

        # Embed any event not already cached (cache survives across calls
        # within this process — see module docstring on why a flat cache is
        # fine at this data volume)
        to_embed = [e for e in events if e.event_id not in _embedding_cache]
        if to_embed:
            texts = [_searchable_text(e) for e in to_embed]
            vectors = model.encode(texts, normalize_embeddings=True)
            for event, vec in zip(to_embed, vectors):
                _embedding_cache[event.event_id] = vec

        query_vec = model.encode([query], normalize_embeddings=True)[0]

        scored = []
        for event in events:
            vec = _embedding_cache.get(event.event_id)
            if vec is None:
                continue
            similarity = float(np.dot(query_vec, vec))  # both normalized -> dot product == cosine similarity
            scored.append((event, similarity))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_n], "semantic"

    except Exception as exc:
        logger.warning(f"Semantic search failed ({exc}) — falling back to keyword matching")
        return _keyword_search(query, events)[:top_n], "keyword_fallback"
