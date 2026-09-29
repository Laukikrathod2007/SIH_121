"""
Decision-support routes: well profile, evidence documents, grounded Q&A, alert center.

  GET  /wells/{well_id}/profile          one-call Well Intelligence panel
  GET  /evidence/document?name=...        the PDF an event cites (open with #page=N)
  POST /knowledge/ask                     grounded answer composed only from retrieved events
  GET  /alerts                            alert center (active + history)
  POST /alerts/evaluate/{well_id}?depth=  run analysis at a depth and raise alerts
  POST /alerts/{alert_id}/acknowledge     acknowledge with user + note
  DELETE /alerts                          reset alert history (demo restarts)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.modules.well_intelligence.routes.knowledge_routes import _store, haversine_km
from app.modules.well_intelligence.services.alert_center import AlertCenter
from app.modules.well_intelligence.services.data_store import NWISDataStore

router = APIRouter(tags=["Decision Support"])


# ---------------------------------------------------------------------------
# Well profile
# ---------------------------------------------------------------------------

@router.get("/wells/{well_id}/profile")
async def well_profile(well_id: str):
    """Metadata, trajectory summary, formations, casing, mud program, events, lessons, documents."""
    store = _store()
    w = store.wells_by_id.get(well_id)
    if w is None:
        raise HTTPException(404, f"Well '{well_id}' not found")
    events = sorted(store.events_by_well.get(well_id, []), key=lambda e: e.depth_start_md_m)
    traj = store.all_trajectories.get(well_id)
    stations = traj.stations if traj else []
    docs = sorted({e.source_document for e in events if e.source_document})
    return {
        "well": w.model_dump(mode="json"),
        "trajectory_summary": {
            "stations": len(stations),
            "max_inclination_deg": round(max((s.inclination_deg for s in stations), default=0.0), 1),
            "td_tvd_m": round(stations[-1].tvd_m, 1) if stations else None,
            "horizontal_displacement_m": round(math.hypot(stations[-1].ns_m, stations[-1].ew_m), 1) if stations else None,
        },
        "formations": [t.model_dump(mode="json") for t in store.formation_tops_by_well.get(well_id, [])],
        "casing_program": getattr(store, "casing_by_well", {}).get(well_id, []),
        "mud_program": getattr(store, "mud_program_by_well", {}).get(well_id, []),
        "events": [e.model_dump(mode="json") for e in events],
        "total_npt_hours": round(sum(e.npt_hours for e in events), 1),
        "lessons": [
            {"event_id": e.event_id, "event_type": e.event_type.value, "depth_m": e.depth_start_md_m,
             "formation": e.formation, "mitigation": e.mitigation_description, "outcome": e.outcome,
             "source_document": e.source_document, "source_page": e.source_page}
            for e in events if e.mitigation_description
        ],
        "documents": [f"WCR_{well_id}.pdf"] + docs,
    }


# ---------------------------------------------------------------------------
# Evidence documents
# ---------------------------------------------------------------------------

@router.get("/evidence/document")
async def evidence_document(name: str = Query(..., description="source_document value from an event")):
    """
    Serve the PDF an event cites. Demo DDR/WCRs live in data/source_documents
    (point that folder at the real OIL archive in production); events that
    came from an uploaded report ('file.pdf [DOC-...]') resolve to the upload.
    """
    m = re.search(r"\[(DOC-[A-Z0-9]+)\]", name)
    if m:
        from app.modules.document_intelligence.controllers.document_controller import document_controller
        path = document_controller.get_document_file_path(m.group(1))
    else:
        if "/" in name or "\\" in name or ".." in name:
            raise HTTPException(400, "Invalid document name")
        path = (settings.DATA_DIR / "source_documents" / name).resolve()
        if not path.exists():
            raise HTTPException(404, f"Source document '{name}' is not in the archive")
    return FileResponse(path, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{path.name}"'})


# ---------------------------------------------------------------------------
# Grounded Q&A
# ---------------------------------------------------------------------------

HAZARD_WORDS = {
    "STUCK_PIPE": ["stuck", "sticking", "pack off", "packoff", "overpull", "tight hole"],
    "MUD_LOSS": ["mud loss", "losses", "lost circulation", "loss", "lcm", "returns"],
    "KICK": ["kick", "influx", "overpressure", "over-pressure", "well control", "gas cut"],
    "WELLBORE_INSTABILITY": ["instability", "washout", "caving", "cavings", "collapse", "unstable"],
    "TORQUE_SPIKE": ["torque", "stick-slip", "stick slip", "stall"],
    "CEMENTING_FAILURE": ["cement", "squeeze", "cbl", "bond"],
}
NEARBY_WORDS = ("nearby", "near by", "offset", "around", "neighbour", "neighbor", "near the active", "near this well")


class AskRequest(BaseModel):
    question: str
    well_id: Optional[str] = None      # active-well context for "nearby" / "current depth"
    depth_m: Optional[float] = None    # current bit depth context
    radius_km: float = 25.0


def interpret_question(q: str, store: NWISDataStore, req: AskRequest) -> dict:
    ql = q.lower()
    hazards = [h for h, words in HAZARD_WORDS.items() if any(w in ql for w in words)]
    formations = sorted({t.formation_name for tops in store.formation_tops_by_well.values() for t in tops},
                        key=len, reverse=True)
    formation = next((f for f in formations if f.lower() in ql), None)
    if formation is None:
        formation = next((f for f in formations if f.lower().split()[0] in re.findall(r"[a-z]+", ql)), None)
    depth = None
    m = re.search(r"(\d[\d,]{2,5})\s*(?:m\b|meters|metres)", ql)
    if m:
        depth = float(m.group(1).replace(",", ""))
    elif req.depth_m is not None and any(w in ql for w in ("current depth", "this depth", "current", "ahead", "approaching")):
        depth = req.depth_m
    well = next((w for w in store.all_wells if w.well_name.lower() in ql or w.well_id.lower() in ql), None)
    nearby = bool(req.well_id) and any(w in ql for w in NEARBY_WORDS)
    return {"hazards": hazards, "formation": formation, "depth_m": depth,
            "well_id": well.well_id if well else None, "nearby_of": req.well_id if nearby else None}


@router.post("/knowledge/ask")
async def knowledge_ask(req: AskRequest):
    """
    Answer a question strictly from the event repository. No generative model:
    the question is interpreted into filters, candidates are ranked
    semantically, and the answer is composed only from retrieved records —
    every statement carries the reference numbers of the events behind it.
    """
    from app.modules.well_intelligence.search.knowledge_search import search_events as run_search

    store = _store()
    if not req.question.strip():
        raise HTTPException(400, "Question is empty")
    intent = interpret_question(req.question, store, req)

    events = list(store.all_events)
    if intent["hazards"]:
        events = [e for e in events if e.event_type.value in intent["hazards"]]
    if intent["formation"]:
        events = [e for e in events if e.formation and e.formation.lower() == intent["formation"].lower()]
    if intent["depth_m"] is not None:
        events = [e for e in events if e.provenance_tier != "EXTRACTED_NO_DEPTH"
                  and abs(e.depth_start_md_m - intent["depth_m"]) <= 200]
    if intent["well_id"]:
        events = [e for e in events if e.well_id == intent["well_id"]]
    if intent["nearby_of"] and intent["nearby_of"] in store.wells_by_id:
        c = store.wells_by_id[intent["nearby_of"]]
        near = {w.well_id for w in store.all_wells if w.well_id != c.well_id
                and haversine_km(c.surface_lat, c.surface_lon, w.surface_lat, w.surface_lon) <= req.radius_km}
        events = [e for e in events if e.well_id in near]

    ranked, mode = run_search(req.question, events, top_n=8) if events else ([], "none")

    sources = []
    for i, (e, score) in enumerate(ranked, start=1):
        w = store.wells_by_id.get(e.well_id)
        sources.append({
            "ref": i, "relevance": round(score, 3), "event_id": e.event_id,
            "well_id": e.well_id, "well_name": w.well_name if w else e.well_id,
            "event_type": e.event_type.value, "severity": e.severity,
            "depth_m": e.depth_start_md_m if e.provenance_tier != "EXTRACTED_NO_DEPTH" else None,
            "formation": e.formation, "narrative": e.raw_narrative,
            "mitigation": e.mitigation_description, "outcome": e.outcome, "npt_hours": e.npt_hours,
            "source_document": e.source_document, "source_page": e.source_page,
        })

    if not sources:
        used = [k for k, v in intent.items() if v]
        return {"question": req.question,
                "answer": "No recorded events match this question"
                          + (f" (understood filters: {', '.join(used)})" if used else "")
                          + ". Try a wider depth, another formation or a larger radius.",
                "statements": [], "interpreted": intent, "search_mode": mode,
                "confidence": {"level": "NONE", "reason": "no matching records"}, "wells": [], "sources": []}

    statements = []
    by_type = Counter(s["event_type"] for s in sources)
    depths = [s["depth_m"] for s in sources if s["depth_m"] is not None]
    well_names = sorted({s["well_name"] for s in sources})
    kinds = ", ".join(f"{n} {t.replace('_', ' ').lower()}" for t, n in by_type.most_common())
    statements.append({
        "text": f"{len(sources)} matching record(s) in {len(well_names)} well(s) ({', '.join(well_names)}): {kinds}"
                + ((f", at {depths[0]:.0f} m MD." if len(set(round(d) for d in depths)) == 1
                    else f", between {min(depths):.0f} and {max(depths):.0f} m MD.") if depths else "."),
        "refs": [s["ref"] for s in sources],
    })
    fm = Counter(s["formation"] for s in sources if s["formation"])
    if fm:
        f, n = fm.most_common(1)[0]
        statements.append({"text": f"Most occurred in the {f} ({n} of {len(sources)}).",
                           "refs": [s["ref"] for s in sources if s["formation"] == f]})
    for s in sources[:3]:
        if s["mitigation"]:
            statements.append({
                "text": f"{s['well_name']}" + (f" at {s['depth_m']:.0f} m" if s["depth_m"] is not None else "")
                        + f": {s['mitigation'].rstrip('.')}."
                        + (f" Outcome: {s['outcome'].rstrip('.')}." if s["outcome"] else ""),
                "refs": [s["ref"]],
            })
    npt = sum(s["npt_hours"] or 0 for s in sources)
    if npt:
        statements.append({"text": f"Together these cost {npt:.0f} h of non-productive time.",
                           "refs": [s["ref"] for s in sources if s["npt_hours"]]})

    top = sources[0]["relevance"]
    level = "HIGH" if len(sources) >= 3 and top >= 0.45 else "MEDIUM" if (top >= 0.3 or len(sources) >= 2) else "LOW"
    return {
        "question": req.question,
        "answer": " ".join(st["text"] for st in statements),
        "statements": statements,
        "interpreted": intent,
        "search_mode": mode,
        "confidence": {"level": level, "reason": f"{len(sources)} supporting record(s), best match {top:.2f}"
                                                   + ("" if mode == "semantic" else " (keyword ranking)")},
        "wells": well_names,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Alert center
# ---------------------------------------------------------------------------

class AckRequest(BaseModel):
    user: str = "Drilling engineer"
    note: Optional[str] = None


@router.get("/alerts")
async def list_alerts(well_id: Optional[str] = None,
                      status: Optional[str] = Query(None, description="ACTIVE | ACKNOWLEDGED")):
    alerts = AlertCenter().list(well_id=well_id, status=status)
    return {"total": len(alerts), "active": sum(1 for a in alerts if a["status"] == "ACTIVE"), "alerts": alerts}


@router.post("/alerts/evaluate/{well_id}")
async def evaluate_alerts(well_id: str, depth: float = Query(..., ge=0)):
    """Run the full analysis at a bit depth and raise/update alerts from it."""
    from app.modules.well_intelligence.services.orchestrator import NWISOrchestrator
    store = _store()
    if well_id not in store.wells_by_id:
        raise HTTPException(404, f"Well '{well_id}' not found")
    result = NWISOrchestrator(store).analyze(active_well_id=well_id, current_depth_m=depth)
    raised = AlertCenter().evaluate(result, source="on_demand")
    return {"well_id": well_id, "depth_m": depth, "overall_risk_level": result.overall_risk_level.value,
            "alert_message": result.alert_message, "alerts_raised_or_updated": raised}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, body: AckRequest):
    a = AlertCenter().acknowledge(alert_id, body.user, body.note)
    if a is None:
        raise HTTPException(404, f"Alert '{alert_id}' not found")
    return a


@router.delete("/alerts")
async def clear_alerts(well_id: Optional[str] = None):
    """Reset alert history (e.g. before restarting a demo replay)."""
    return {"cleared": AlertCenter().clear(well_id)}
