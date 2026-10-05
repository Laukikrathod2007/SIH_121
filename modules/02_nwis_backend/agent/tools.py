"""
Tool catalog for the agentic Knowledge Copilot.

Per the user's explicit decision: the agent calls the app's own EXISTING
route handlers as tools, not a second copy of the query/engine logic. Each
wrapper below calls the real `async def` function already registered on
FastAPI in server.py (module 02) or api/server.py (module 04) — these are
ordinary Python coroutines FastAPI wraps for routing, so calling them
directly here is a genuine in-process function call, not a second HTTP
round-trip to the same backend. This means every honesty/auth/DB-vs-memory
guarantee already built into those handlers (data_source labeling,
503-on-db-unreachable, never-silent-fallback) comes along for free, with
zero duplicated logic — the single-source-of-truth discipline already
established throughout this codebase (see AUDIT/13 §A's own framing of
DbStoreSnapshot for the same reasoning applied to data access).

IMPORTANT: the real route functions declare their optional parameters as
FastAPI `Query(...)` objects, which only resolve to real values when
FastAPI's own dependency-injection layer calls them. Calling them directly
here bypasses that layer, so every wrapper below passes EVERY parameter
explicitly (never relies on a bare keyword default) — confirmed necessary
by reading server.py's actual signatures before writing this file.

Only read-only, non-mutating routes are exposed here. The agent can never
approve/reject a document, mutate an alert's status, or control the
simulator — matching the plan's explicit scope limit.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Tool schemas (Ollama / OpenAI-style function-calling format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_events",
            "description": (
                "Free-text or structured search over the historical drilling-event "
                "knowledge base (lessons learned, NPT incidents, mitigation measures, "
                "outcomes). Use this for questions like 'find events where mud weight "
                "increase fixed wellbore instability' or 'show kicks in Barail Sandstone'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text search query, e.g. the user's question in their own words."},
                    "hazard_type": {
                        "type": "string",
                        "enum": ["MUD_LOSS", "STUCK_PIPE", "KICK", "WELLBORE_INSTABILITY", "TORQUE_SPIKE", "CEMENTING_FAILURE", "OVERPRESSURE_ZONE"],
                        "description": "Optional: narrow to one hazard type first.",
                    },
                    "formation": {"type": "string", "description": "Optional: narrow to events in this formation."},
                    "min_severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "description": "Optional: minimum severity."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_well",
            "description": "Get full identity/metadata for one well: operator, total depth, well type, formation tops, trajectory station count, event count.",
            "parameters": {
                "type": "object",
                "properties": {"well_id": {"type": "string", "description": "The well ID, e.g. '15/9-F-12' or 'WELL-HGJ-012'."}},
                "required": ["well_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_offset_ranking",
            "description": (
                "Get the DORS 5-factor offset-well relevance ranking for an active well "
                "at a given depth — which nearby/historical wells are most relevant right "
                "now, and why (spatial, formation, depth, trajectory, hazard-history factors)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "The active well ID."},
                    "depth": {"type": "number", "description": "Current bit depth in meters MD."},
                },
                "required": ["well_id", "depth"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_corridors",
            "description": "Get historical risk corridors (depth windows with concentrated hazard history) ahead of the current bit depth for a well.",
            "parameters": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "The active well ID."},
                    "depth": {"type": "number", "description": "Current bit depth in meters MD."},
                    "hazard_type": {
                        "type": "string",
                        "enum": ["MUD_LOSS", "STUCK_PIPE", "KICK", "WELLBORE_INSTABILITY", "TORQUE_SPIKE", "CEMENTING_FAILURE", "OVERPRESSURE_ZONE"],
                        "description": "Optional: filter to one hazard type.",
                    },
                },
                "required": ["well_id", "depth"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stratigraphic_alignment",
            "description": (
                "Compare formations/depths across wells correctly (formation-relative, not raw "
                "measured depth) — answers 'what formation is each offset well in at the "
                "equivalent position to our current bit depth'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "well_id": {"type": "string", "description": "The active well ID."},
                    "depth": {"type": "number", "description": "Current bit depth in meters MD."},
                },
                "required": ["well_id", "depth"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_alerts",
            "description": "Get currently active alerts for a well from the live advisory engine (this session's running simulator, if any).",
            "parameters": {
                "type": "object",
                "properties": {"well_id": {"type": "string", "description": "The well ID."}},
                "required": ["well_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alert_history",
            "description": "Get the persisted alert history for a well — past alerts saved to the shared database, across sessions, not just the current live feed.",
            "parameters": {
                "type": "object",
                "properties": {"well_id": {"type": "string", "description": "The well ID."}},
                "required": ["well_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations — each calls the real route handler coroutine
# directly, with every parameter passed explicitly (see module docstring).
# ---------------------------------------------------------------------------

async def _tool_search_events(query: str, hazard_type: Optional[str] = None, formation: Optional[str] = None, min_severity: Optional[str] = None) -> dict:
    from app.modules.nwis.server import search_events_semantic
    try:
        result = await asyncio.to_thread(
            search_events_semantic,
            query=query, hazard_type=hazard_type, formation=formation,
            min_severity=min_severity, depth_min=None, depth_max=None, top_n=8,
        )
    except Exception as exc:
        return _http_exception_to_tool_error(exc, query)
    # Trim to what the model actually needs — the full event payloads are
    # large and mostly irrelevant to answering in natural language; keep
    # exactly the fields the system prompt requires for citation.
    return {
        "search_mode": result["search_mode"],
        "total_candidates": result["total_candidates"],
        "data_source": result["data_source"],
        "results": [
            {
                "relevance_score": r["relevance_score"],
                "event_id": r["event"]["event_id"],
                "well_id": r["event"]["well_id"],
                "event_type": r["event"]["event_type"],
                "severity": r["event"]["severity"],
                "depth_start_md_m": r["event"]["depth_start_md_m"],
                "formation": r["event"].get("formation"),
                "raw_narrative": r["event"].get("raw_narrative"),
                "mitigation_description": r["event"].get("mitigation_description"),
                "outcome": r["event"].get("outcome"),
                "source_document": r["event"].get("source_document"),
                "source_page": r["event"].get("source_page"),
                "source_type": r["event"].get("source_type"),
            }
            for r in result["results"]
        ],
    }


async def _tool_get_well(well_id: str) -> dict:
    from app.modules.nwis.server import get_well
    try:
        result = await asyncio.to_thread(get_well, well_id)
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    well = result["well"]
    return {
        "well_id": well.get("well_id"),
        "well_name": well.get("well_name"),
        "field": well.get("field"),
        "operator": well.get("operator"),
        "well_type": well.get("well_type"),
        "total_depth_md_m": well.get("total_depth_md_m"),
        "status": well.get("status"),
        "source_type": well.get("source_type"),
        "trajectory_stations": result["trajectory_stations"],
        "formation_tops_count": len(result["formation_tops"]),
        "total_events": result["total_events"],
        "data_source": result["data_source"],
    }


async def _tool_get_offset_ranking(well_id: str, depth: float) -> dict:
    from app.modules.nwis.server import rank_offsets
    try:
        result = await asyncio.to_thread(
            rank_offsets, well_id=well_id, depth=depth, radius_km=25.0, top_n=10, max_distance_km=None
        )
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    return {
        "active_well_id": result["active_well_id"],
        "depth_m": result["depth_m"],
        "formation_at_bit": result.get("formation_at_bit"),
        "dors_formula": result["dors_formula"],
        "data_source": result["data_source"],
        "rankings": [
            {
                "rank": r["rank"],
                "well_id": r["well_id"],
                "dors_score": r["dors_score"],
                "distance_km": r.get("distance_km"),
                "component_scores": r.get("component_scores"),
            }
            for r in result["rankings"][:5]
        ],
    }


async def _tool_get_risk_corridors(well_id: str, depth: float, hazard_type: Optional[str] = None) -> dict:
    from app.modules.nwis.server import get_risk_corridors
    try:
        result = await asyncio.to_thread(
            get_risk_corridors, well_id=well_id, depth=depth, hazard_type=hazard_type
        )
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    return {
        "well_id": result["well_id"],
        "depth_m": result["depth_m"],
        "formation_at_bit": result.get("formation_at_bit"),
        "total_corridors": result["total_corridors"],
        "data_source": result["data_source"],
        "corridors": [
            {
                "corridor_id": c["corridor_id"],
                "hazard_type": c["hazard_type"],
                "depth_start_m": c["depth_start_m"],
                "depth_end_m": c["depth_end_m"],
                "event_count": c["event_count"],
                "max_severity": c.get("max_severity"),
                "historical_frequency": c.get("historical_frequency"),
                "recommended_action": c.get("recommended_action"),
                "contributing_wells": c.get("contributing_wells", []),
            }
            for c in result["corridors"][:6]
        ],
    }


async def _tool_get_stratigraphic_alignment(well_id: str, depth: float) -> dict:
    from app.modules.nwis.server import stratigraphic_depth_track
    try:
        result = await asyncio.to_thread(stratigraphic_depth_track, well_id=well_id, depth=depth, top_n=10)
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    # align_horizons_across_wells() returns Dict[str, dict] keyed by
    # well_id (confirmed by reading stratigraphic_correlator.py directly),
    # not a list -- flattened here into a list of {well_id, ...} entries,
    # the shape every other tool's result already uses, so the model
    # doesn't need to special-case this one tool's response structure.
    alignment_dict = result.get("alignment", {}) or {}
    alignment_list = [{"well_id": wid, **data} for wid, data in alignment_dict.items()]
    return {
        "active_well_id": result["active_well_id"],
        "depth_m": result["depth_m"],
        "formation_at_bit": result.get("formation_at_bit"),
        "data_source": result["data_source"],
        "alignment": alignment_list[:8],
    }


async def _tool_get_live_alerts(well_id: str) -> dict:
    from app.modules.physics.api.server import predictive_get_alerts
    try:
        alerts = await predictive_get_alerts(well_id)
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    return {
        "well_id": well_id,
        "active_alert_count": len(alerts),
        "alerts": [
            {
                "alert_id": a["alert_id"], "hazard_type": a["hazard_type"], "severity": a["severity"],
                "measured_depth_m": a["measured_depth_m"], "formation": a["formation"],
                "headline": a["headline"], "status": a["status"],
            }
            for a in alerts
        ],
    }


async def _tool_get_alert_history(well_id: str) -> dict:
    from app.modules.physics.api.server import predictive_get_alert_history
    try:
        result = await asyncio.to_thread(predictive_get_alert_history, well_id, limit=20)
    except Exception as exc:
        return _http_exception_to_tool_error(exc, well_id)
    # Honest tri-state passthrough — never collapse "no history" and
    # "unavailable" into the same shape (same discipline as the route itself).
    if result["status"] != "ok":
        return result
    return {
        "status": "ok",
        "alert_count": len(result["alerts"]),
        "alerts": [
            {
                "alert_id": a["alert_id"], "hazard_type": a["hazard_type"], "severity": a["severity"],
                "headline": a["headline"], "status": a["status"], "created_at": a["created_at"],
            }
            for a in result["alerts"][:10]
        ],
    }


def _http_exception_to_tool_error(exc: Exception, well_id: str) -> dict:
    """A tool call must never let a raw exception (or FastAPI's
    HTTPException with its real status/detail) propagate to the model as
    unstructured text — it gets a clean, honest JSON error payload instead,
    same never-raw-exception discipline as every user-facing field
    elsewhere in this codebase. 404s are reported as a genuine "not found"
    (a real, common, non-error case the model should explain plainly, not
    treat as a system failure); anything else is reported as a real,
    generic failure without leaking internal detail."""
    from fastapi import HTTPException
    if isinstance(exc, HTTPException) and exc.status_code == 404:
        return {"error": "not_found", "detail": f"No data found for well_id '{well_id}'."}
    if isinstance(exc, HTTPException) and exc.status_code == 503:
        return {"error": "unavailable", "detail": "The database is temporarily unavailable."}
    logger.warning(f"Agent tool call failed unexpectedly for well_id '{well_id}': {exc}")
    return {"error": "tool_failed", "detail": "This lookup could not be completed right now."}


TOOL_IMPLEMENTATIONS: dict[str, Callable[..., Any]] = {
    "search_events": _tool_search_events,
    "get_well": _tool_get_well,
    "get_offset_ranking": _tool_get_offset_ranking,
    "get_risk_corridors": _tool_get_risk_corridors,
    "get_stratigraphic_alignment": _tool_get_stratigraphic_alignment,
    "get_live_alerts": _tool_get_live_alerts,
    "get_alert_history": _tool_get_alert_history,
}


async def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one model-requested tool call to its real implementation.
    Never raises — an unknown tool name or a bad-argument call returns an
    honest error payload the model can read and recover from (e.g. retry
    with corrected arguments), rather than crashing the whole turn."""
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if impl is None:
        return {"error": "unknown_tool", "detail": f"No tool named '{name}'."}
    try:
        return await impl(**arguments)
    except TypeError as exc:
        logger.debug(f"Agent tool '{name}' called with bad arguments {arguments}: {exc}")
        return {"error": "bad_arguments", "detail": f"Invalid arguments for '{name}': {exc}"}
