"""
Agentic Knowledge Copilot — the tool-calling loop over Google's Gemini API
(gemini-2.5-flash), grounded entirely in this project's own real data via
the tool catalog in agent/tools.py.

Design, per the approved plan and this project's own established patterns:
  - Gemini (free-tier) instead of a locally-hosted Ollama model — chosen so
    the deployed instance (Render free tier has no GPU/4.7GB RAM budget for
    a local 7B model) gets the full agentic experience without hosting an
    LLM ourselves. tools.py's OpenAI/Ollama-style TOOL_SCHEMAS are converted
    to Gemini's FunctionDeclaration shape by _to_gemini_tool() below —
    tools.py itself is untouched; it stays the single source of truth for
    the tool catalog across whichever LLM backend calls it.
  - THREE separate Gemini API keys (GEMINIKEY1/2/3), each from a separate
    free-tier Google account, rotated on failure — not for redundancy
    against one flaky key, but to multiply the effective free request
    quota roughly 3x before the Copilot has to fall back to keyword search.
    A request tries key 1; on a rate-limit/quota error (HTTP 429) or a
    transient server error (5xx) it tries key 2, then key 3; only once ALL
    THREE have failed does the turn raise GeminiUnavailable and the caller
    falls back to the deterministic keyword path. A genuine auth error
    (bad key, 401/403) is treated the same as a rate limit here — skip to
    the next key — since from the caller's perspective both mean "this key
    can't serve this request right now," and the whole point of three keys
    is to never surface that distinction to the end user.
  - The system prompt enforces the same grounding discipline the Ollama
    version used (unchanged): never state a fact that didn't come back
    from a tool call; cite well_id/event_id/source_document for every
    claim; say so plainly when nothing relevant was found.
  - A bounded loop (MAX_TOOL_ROUNDS) prevents a runaway tool-call cycle.
  - If every configured key fails (or none are configured at all), this
    module raises GeminiUnavailable rather than silently returning a
    degraded answer — the caller (server.py's route) falls back to the
    existing deterministic keyword-match path and reports an honest "mode"
    to the frontend, exactly as the Ollama version did and exactly as every
    other optional capability in this codebase already does (docling,
    cloud OCR fallback, semantic search's own keyword-fallback path).
"""
from __future__ import annotations

import os
from typing import Any, AsyncIterator, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from loguru import logger

from app.modules.nwis.agent.tools import TOOL_SCHEMAS, execute_tool

GEMINI_MODEL = os.environ.get("NWIS_GEMINI_MODEL", "gemini-flash-lite-latest")
MAX_TOOL_ROUNDS = 4

# Three separate free-tier Google accounts' API keys, rotated on failure to
# multiply the effective free quota (see module docstring). Read lazily via
# _configured_keys() rather than frozen at import time, so tests can
# monkeypatch os.environ and so a key added/rotated via a process restart
# is picked up without any other code change.
_KEY_ENV_VARS = ("GEMINIKEY1", "GEMINIKEY2", "GEMINIKEY3")


def _configured_keys() -> list[str]:
    return [v for v in (os.environ.get(name, "").strip() for name in _KEY_ENV_VARS) if v]


class GeminiUnavailable(RuntimeError):
    """Raised when every configured Gemini key has failed (or none are
    configured at all) -- kept distinct from a normal model response so the
    caller can fall back honestly instead of surfacing a raw API error."""


def _to_gemini_tool(schemas: list[dict[str, Any]]) -> genai_types.Tool:
    """Converts tools.py's OpenAI/Ollama-style TOOL_SCHEMAS (a list of
    {"type": "function", "function": {name, description, parameters}})
    into one Gemini Tool with a FunctionDeclaration per entry. tools.py's
    `parameters` is already plain JSON Schema, which FunctionDeclaration
    accepts directly (confirmed live: enum/required/object nesting all
    convert correctly with no manual Schema construction needed)."""
    declarations = [
        genai_types.FunctionDeclaration(
            name=entry["function"]["name"],
            description=entry["function"]["description"],
            parameters=entry["function"]["parameters"],
        )
        for entry in schemas
    ]
    return genai_types.Tool(function_declarations=declarations)


_GEMINI_TOOL = _to_gemini_tool(TOOL_SCHEMAS)

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


def _is_retryable_on_another_key(exc: Exception) -> bool:
    """True for exactly the failure modes a different key might not hit:
    rate limit/quota (429), auth (401/403 -- a revoked or mistyped key),
    and transient server-side errors (5xx). False for anything else (a
    genuine 400 bad-request from a malformed payload would fail identically
    on every key, so there's no point burning all three on it)."""
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        return code in (401, 403, 429) or (code is not None and code >= 500)
    return isinstance(exc, (ConnectionError, TimeoutError))


async def _gemini_generate(
    contents: list[genai_types.Content], *, with_tools: bool
) -> genai_types.GenerateContentResponse:
    """Tries each configured key in order, returning the first successful
    response. Raises GeminiUnavailable only once every key has been tried
    and failed (or none are configured)."""
    keys = _configured_keys()
    if not keys:
        raise GeminiUnavailable("No Gemini API key configured (set GEMINIKEY1, optionally 2/3).")

    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[_GEMINI_TOOL] if with_tools else None,
        # Manual control over the tool-calling loop (see module docstring) —
        # this project streams each tool_call/tool_result to the frontend
        # as it happens, which the SDK's automatic_function_calling loop
        # does not expose a hook for.
        automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
    )

    last_exc: Optional[Exception] = None
    for key_index, key in enumerate(keys, start=1):
        try:
            client = genai.Client(api_key=key)
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=config,
            )
            return response
        except Exception as exc:  # noqa: BLE001 — deliberately broad, see _is_retryable_on_another_key
            last_exc = exc
            if _is_retryable_on_another_key(exc):
                logger.warning(
                    f"Gemini key #{key_index} failed ({type(exc).__name__}: {exc}) — "
                    f"trying next key." if key_index < len(keys) else
                    f"Gemini key #{key_index} failed ({type(exc).__name__}: {exc}) — no more keys."
                )
                continue
            # Not a "try another key" failure (e.g. a malformed request) —
            # every key would hit the same error, so fail fast.
            raise GeminiUnavailable(f"Gemini request failed: {type(exc).__name__}: {exc}") from exc

    raise GeminiUnavailable(
        f"All {len(keys)} configured Gemini key(s) failed. Last error: "
        f"{type(last_exc).__name__}: {last_exc}"
    ) from last_exc


async def check_gemini_reachable() -> bool:
    """A cheap, fast liveness probe — used by the route handler to decide
    up front whether to attempt the agentic path at all. Tries only the
    first configured key with a minimal request; a real turn still rotates
    through all three on failure, this probe is just a fast up-front check
    so a totally unconfigured/dead setup fails over to keyword-fallback
    immediately rather than after the first real chat call's full retry
    sequence."""
    keys = _configured_keys()
    if not keys:
        return False
    try:
        client = genai.Client(api_key=keys[0])
        await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part(text="ping")])],
            config=genai_types.GenerateContentConfig(max_output_tokens=1),
        )
        return True
    except Exception as exc:
        # A rate-limited first key does not mean Gemini-the-feature is
        # down — it might still serve a real request on key 2/3. Only
        # report "unreachable" for the probe's own purpose (should we
        # attempt the agentic path at all) when the failure isn't the kind
        # a key rotation would fix.
        return _is_retryable_on_another_key(exc) and len(keys) > 1


def _part_to_dict(part: genai_types.Part) -> dict[str, Any]:
    return {"function_call": part.function_call, "text": part.text}


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

    Raises GeminiUnavailable if every configured key fails (or none are
    configured) — the caller falls back to the non-agentic path in that
    case; every other failure mode (a tool erroring, the model producing no
    final answer after MAX_TOOL_ROUNDS) is reported as a normal "error"
    event instead, since Gemini itself IS reachable in that case and a
    fallback would be dishonest about what actually happened.
    """
    context_line = ""
    if active_well_id:
        context_line = f"\n\nThe user's active well right now is '{active_well_id}'"
        if active_depth is not None:
            context_line += f" at a current bit depth of {active_depth:.1f}m MD"
        context_line += ". Use this well/depth when the user's question doesn't name one explicitly."

    # Gemini's system_instruction is set per-request in config (above), not
    # as a message in `contents` — context_line still needs to reach the
    # model, so it's prepended to the first user turn instead.
    contents: list[genai_types.Content] = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=user_message + context_line)]),
    ]
    global SYSTEM_PROMPT  # noqa: PLW0603 — read-only use below; not reassigned

    for round_num in range(MAX_TOOL_ROUNDS):
        response = await _gemini_generate(contents, with_tools=True)
        candidates = response.candidates or []
        if not candidates:
            yield {"type": "error", "detail": "The assistant did not produce a response."}
            return

        parts = candidates[0].content.parts if candidates[0].content else []
        function_calls = [p.function_call for p in parts if p.function_call is not None]
        text_parts = [p.text for p in parts if p.text]

        if not function_calls:
            final_text = "".join(text_parts).strip()
            if final_text:
                yield {"type": "answer", "text": final_text}
            else:
                yield {"type": "error", "detail": "The assistant did not produce an answer."}
            return

        # The model may request several tool calls in one round; execute
        # each for real and feed every result back before the next round.
        contents.append(genai_types.Content(role="model", parts=parts))
        response_parts: list[genai_types.Part] = []
        for call in function_calls:
            name = call.name or ""
            arguments = dict(call.args or {})
            yield {"type": "tool_call", "tool": name, "arguments": arguments}

            result = await execute_tool(name, arguments)
            yield {"type": "tool_result", "tool": name, "result": result}
            response_parts.append(
                genai_types.Part(function_response=genai_types.FunctionResponse(name=name, response=result))
            )
        contents.append(genai_types.Content(role="user", parts=response_parts))

    # Exhausted MAX_TOOL_ROUNDS without a final answer — ask once more
    # with tools disabled so the model is forced to synthesize from
    # whatever it has gathered so far, rather than looping forever.
    try:
        response = await _gemini_generate(contents, with_tools=False)
        candidates = response.candidates or []
        parts = candidates[0].content.parts if candidates and candidates[0].content else []
        final_text = "".join(p.text for p in parts if p.text).strip()
        if final_text:
            yield {"type": "answer", "text": final_text}
            return
    except GeminiUnavailable:
        pass
    yield {"type": "error", "detail": "Could not reach a final answer within the allowed number of lookups."}


async def run_keyword_fallback(
    user_message: str,
    *,
    active_well_id: Optional[str] = None,
    active_depth: Optional[float] = None,
) -> AsyncIterator[dict[str, Any]]:
    """Deterministic, keyword-search fallback when Gemini is unavailable
    (no keys configured, or all three failed). Yields tool_call,
    tool_result, and a grounded answer assembled from actual database
    results, citing all sources honestly."""
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

    parts = ["**[Keyword Search Mode — AI Assistant Unavailable]**\n"]
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
