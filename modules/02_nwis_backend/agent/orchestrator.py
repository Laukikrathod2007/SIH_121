"""
Agentic Knowledge Copilot — the tool-calling loop over a local LLM
(Ollama), grounded entirely in this project's own real data via the tool
catalog in agent/tools.py.

Design, per the approved plan and this project's own established
patterns:
  - Local, free LLM via Ollama's /api/chat endpoint (confirmed working
    live before this was written: qwen2.5:7b-instruct correctly selects
    a tool and extracts arguments from natural language, and correctly
    synthesizes a grounded final answer from a real tool result fed
    back to it).
  - The system prompt enforces a grounding discipline matching this
    project's zero-hallucination philosophy (already documented in
    CopilotPage.tsx's own header comment, HistoricalIntelligencePage.tsx's
    "Illustrative summary" labeling, PdfEvidenceViewer.tsx's refusal to
    fabricate a highlight box): never state a fact that didn't come back
    from a tool call; cite well_id/event_id/source_document for every
    claim; say so plainly when nothing relevant was found.
  - A bounded loop (MAX_TOOL_ROUNDS) prevents a runaway tool-call cycle.
  - If Ollama is unreachable at all (not running, model not pulled,
    network error), this module raises OllamaUnavailable rather than
    silently returning a degraded answer — the caller (server.py's new
    route) is responsible for falling back to the existing keyword-match
    CopilotPage logic equivalent and reporting an honest "mode" to the
    frontend, exactly as it already does for every other optional
    capability in this codebase (docling, cloud OCR fallback, semantic
    search's own keyword-fallback path).
"""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Optional

import httpx
from loguru import logger

from app.modules.nwis.agent.tools import TOOL_SCHEMAS, execute_tool

OLLAMA_URL = os.environ.get("NWIS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("NWIS_OLLAMA_MODEL", "qwen2.5:7b-instruct")
MAX_TOOL_ROUNDS = 4
# Ollama's own default load timeout for a model that isn't already
# resident in memory can be well over a minute on CPU -- generous but
# bounded, so a genuinely unreachable Ollama fails fast (connect_timeout)
# while a slow-but-working first load doesn't get killed mid-generation.
_TIMEOUT = httpx.Timeout(connect=3.0, read=120.0, write=10.0, pool=5.0)


class OllamaUnavailable(RuntimeError):
    """Raised when Ollama cannot be reached or errors at the HTTP layer --
    kept distinct from a normal model response so the caller can fall back
    honestly instead of surfacing a raw connection error to the user."""


SYSTEM_PROMPT = """You are the Knowledge Copilot for eRTMAC-NWIS, a drilling decision-support \
system for Oil India Limited. You help drilling engineers find relevant offset-well \
history, risk context, and formation correlation for the well they are currently working.

STRICT GROUNDING RULES — these are not optional:
1. You may ONLY state facts that came back from a tool call you made in this conversation. \
Never state a well name, depth, score, event, or alert that wasn't actually returned by a tool.
2. For every factual claim, cite its source: the well_id, event_id, and — when present in the \
tool result — source_document and source_page. If a record has no source_document, say so \
plainly ("no source document on record") rather than omitting the citation.
3. If a tool call returns no results, or an error, say so honestly. Never invent a plausible- \
sounding answer to fill a gap in the data.
4. Distinguish real historical data from synthetic/demonstration data when the tool result \
includes a source_type field (REAL vs SYNTHETIC) — mention it when it's materially relevant \
to how much weight the user should give the answer.
5. Keep answers concise and operationally useful — a drilling engineer wants the evidence and \
the bottom line, not a long essay.
6. If the user's question doesn't need a tool (e.g. a general question about how the system \
works), you may answer directly without calling a tool — but still never fabricate specific \
well/event data in a direct answer.
"""


async def _ollama_chat(messages: list[dict[str, Any]], *, with_tools: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    if with_tools:
        payload["tools"] = TOOL_SCHEMAS
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise OllamaUnavailable(f"Could not reach Ollama at {OLLAMA_URL}: {type(exc).__name__}") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaUnavailable(f"Ollama returned HTTP {exc.response.status_code}") from exc


async def check_ollama_reachable() -> bool:
    """A cheap, fast liveness probe — used by the route handler to decide
    up front whether to attempt the agentic path at all, so a genuinely
    down Ollama fails over to keyword-fallback immediately rather than
    after a slow timeout on the first real chat call."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2.0, read=3.0, write=2.0, pool=2.0)) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def run_agent_turn(
    user_message: str,
    *,
    active_well_id: Optional[str] = None,
    active_depth: Optional[float] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Runs one bounded agentic tool-calling turn, yielding progress events
    for the caller to stream over SSE:
      {"type": "tool_call", "tool": str, "arguments": dict}
      {"type": "tool_result", "tool": str, "result": dict}
      {"type": "answer", "text": str}
      {"type": "error", "detail": str}

    Raises OllamaUnavailable if Ollama cannot be reached at all — the
    caller falls back to the non-agentic path in that case; every other
    failure mode (a tool erroring, the model producing no final answer
    after MAX_TOOL_ROUNDS) is reported as a normal "error" event instead,
    since Ollama itself IS reachable in that case and a fallback would be
    dishonest about what actually happened.
    """
    context_line = ""
    if active_well_id:
        context_line = f"\n\nThe user's active well right now is '{active_well_id}'"
        if active_depth is not None:
            context_line += f" at a current bit depth of {active_depth:.1f}m MD"
        context_line += ". Use this well/depth when the user's question doesn't name one explicitly."

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + context_line},
        {"role": "user", "content": user_message},
    ]

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await _ollama_chat(messages, with_tools=True)
        message = response.get("message", {})
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            final_text = (message.get("content") or "").strip()
            if final_text:
                yield {"type": "answer", "text": final_text}
            else:
                yield {"type": "error", "detail": "The assistant did not produce an answer."}
            return

        # The model may request several tool calls in one round; execute
        # each for real and feed every result back before the next round.
        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls})
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            arguments = fn.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            yield {"type": "tool_call", "tool": name, "arguments": arguments}

            result = await execute_tool(name, arguments)
            yield {"type": "tool_result", "tool": name, "result": result}
            messages.append({"role": "tool", "content": json.dumps(result, default=str)})

    # Exhausted MAX_TOOL_ROUNDS without a final answer — ask once more
    # with tools disabled so the model is forced to synthesize from
    # whatever it has gathered so far, rather than looping forever.
    try:
        response = await _ollama_chat(messages, with_tools=False)
        final_text = (response.get("message", {}).get("content") or "").strip()
        if final_text:
            yield {"type": "answer", "text": final_text}
            return
    except OllamaUnavailable:
        pass
    yield {"type": "error", "detail": "Could not reach a final answer within the allowed number of lookups."}


async def run_keyword_fallback(
    user_message: str,
    *,
    active_well_id: Optional[str] = None,
    active_depth: Optional[float] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Deterministic, keyword-search fallback when Ollama is unavailable.
    Yields tool_call, tool_result, and a grounded answer assembled from
    actual database results, citing all sources honestly."""
    yield {"type": "tool_call", "tool": "search_events", "arguments": {"query": user_message}}
    search_res = await execute_tool("search_events", {"query": user_message})
    yield {"type": "tool_result", "tool": "search_events", "result": search_res}

    rank_res = None
    well_id = active_well_id
    depth = active_depth or 2500.0

    if well_id:
        yield {"type": "tool_call", "tool": "get_offset_ranking", "arguments": {"well_id": well_id, "depth": depth}}
        rank_res = await execute_tool("get_offset_ranking", {"well_id": well_id, "depth": depth})
        yield {"type": "tool_result", "tool": "get_offset_ranking", "result": rank_res}

    parts = ["**[Keyword Search Mode — Local AI Assistant Unavailable]**\n"]
    events = search_res.get("results", [])
    if events:
        parts.append(f"Retrieved {len(events)} relevant historical event(s) matching your query ({search_res.get('data_source', 'in-memory')}):")
        for i, ev in enumerate(events[:4], 1):
            w_id = ev.get("well_id", "Unknown")
            e_id = ev.get("event_id", "Unknown")
            e_type = ev.get("event_type", "EVENT").replace("_", " ")
            sev = ev.get("severity", "UNKNOWN")
            d_start = ev.get("depth_start_md_m", "N/A")
            fm = ev.get("formation") or "Unknown formation"
            narr = ev.get("raw_narrative") or ev.get("outcome") or "No narrative recorded"
            mit = ev.get("mitigation_description") or "No mitigation recorded"
            src_doc = ev.get("source_document") or "no source document on record"
            src_pg = ev.get("source_page")
            pg_str = f", page {src_pg}" if src_pg is not None else ""
            src_type = f" [{ev.get('source_type')}]" if ev.get("source_type") else ""

            parts.append(
                f"\n{i}. **{e_type}** ({sev}) at {w_id} ({d_start}m MD, {fm}){src_type}\n"
                f"   - **Details**: {narr}\n"
                f"   - **Mitigation**: {mit}\n"
                f"   - **Source Citation**: event `{e_id}` from `{src_doc}`{pg_str}"
            )
    else:
        parts.append(f"No historical drilling events matched the keyword query '{user_message}'.")

    if rank_res and not rank_res.get("error"):
        rankings = rank_res.get("rankings", [])
        if rankings:
            parts.append(f"\n\n**Top Offset Wells for {well_id} at {depth}m MD** (DORS formula, {rank_res.get('data_source', 'db')}):")
            for r in rankings[:3]:
                parts.append(
                    f"\n- **{r.get('well_id')}**: DORS score {r.get('dors_score', 0):.4f}, "
                    f"distance {r.get('distance_km', 0):.2f}km"
                )

    final_text = "\n".join(parts)
    yield {"type": "answer", "text": final_text}

