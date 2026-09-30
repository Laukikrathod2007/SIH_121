"""
Models & benchmarks: every number here is measured by code in this repo.

  GET /models/benchmarks   hazard-model CV metrics, sensor-model benchmark,
                           document-extraction accuracy vs hand labels.

Sources:
  * data/models/hazard_model_metrics.json  <- ml/train_hazard_models.py
  * data/models/sensor_benchmark.json      <- predictive_analytics/evaluation/model_benchmarking.py
  * extraction accuracy                    <- computed live: data/output/*.json vs data/sample_docs/ground_truth.json
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["Models & Benchmarks"])
MODELS_DIR = settings.DATA_DIR / "models"


def _read(path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _num(v: Any) -> Optional[float]:
    if isinstance(v, dict):
        v = v.get("normalized_value")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def extraction_benchmark() -> Dict[str, Any]:
    from app.modules.document_intelligence.models.schemas import EVENT_TYPE_TO_HAZARD_TYPE, EventType

    truth = _read(settings.SAMPLE_DOCS_DIR / "ground_truth.json") or {"documents": {}}
    latest: Dict[str, dict] = {}
    for f in (settings.DATA_DIR / "output").glob("*.json"):
        d = _read(f)
        if not d:
            continue
        name = re.sub(r"^JOB-[0-9A-F]+_", "", d.get("source_filename") or "", flags=re.IGNORECASE)
        if name in truth["documents"] and (name not in latest or (d.get("extraction_completed_at") or "") > (latest[name].get("extraction_completed_at") or "")):
            latest[name] = d

    docs: List[dict] = []
    tp = fp = fn = depth_ok = depth_total = 0
    wells_ok = 0
    for name, gt in truth["documents"].items():
        d = latest.get(name)
        if d is None:
            continue
        extracted = []
        for p in d.get("pages", []):
            for e in p.get("drilling_events", []):
                try:
                    hz = EVENT_TYPE_TO_HAZARD_TYPE.get(EventType(e.get("event_type")))
                except ValueError:
                    hz = None
                if hz:
                    extracted.append({"hazard": hz, "depth_m": _num(e.get("depth_start_md_m"))})
        unmatched = list(extracted)
        doc_tp = 0
        for g in gt["events"]:
            match = next((x for x in unmatched if x["hazard"] == g["hazard"] and (
                g["depth_m"] is None or (x["depth_m"] is not None and abs(x["depth_m"] - g["depth_m"]) <= 5))), None)
            if match:
                unmatched.remove(match)
                doc_tp += 1
                if g["depth_m"] is not None:
                    depth_total += 1
                    depth_ok += 1
            elif g["depth_m"] is not None:
                depth_total += 1
        doc_fp, doc_fn = len(unmatched), len(gt["events"]) - doc_tp
        tp, fp, fn = tp + doc_tp, fp + doc_fp, fn + doc_fn
        well_ok = (d.get("well_name") or "").upper() == gt["well_name"].upper()
        wells_ok += int(well_ok)
        docs.append({
            "document": name, "pages": d.get("total_pages"), "processing_ms": d.get("total_processing_time_ms"),
            "labelled_events": len(gt["events"]), "matched": doc_tp, "missed": doc_fn, "spurious": doc_fp,
            "well_name_expected": gt["well_name"], "well_name_extracted": d.get("well_name"), "well_name_correct": well_ok,
            "read_confidence": d.get("overall_confidence"), "validation_status": d.get("validation_status"),
        })

    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return {
        "documents_scored": len(docs),
        "labelled_events": tp + fn,
        "event_precision": round(precision, 3),
        "event_recall": round(recall, 3),
        "event_f1": round(2 * precision * recall / max(1e-9, precision + recall), 3),
        "well_name_accuracy": round(wells_ok / max(1, len(docs)), 3),
        "rule": "event counts as found when hazard type matches and depth is within 5 m of the label",
        "documents": docs,
    }


def real_document_runs() -> List[dict]:
    """Throughput on real public drilling reports (backend-working's benchmark runs; no accuracy labels)."""
    runs: Dict[str, dict] = {}
    folder = settings.ROOT_DIR / "modules" / "01_document_intelligence" / "benchmarks" / "results"
    for f in sorted(folder.glob("benchmark_*.json")):
        d = _read(f)
        if d and d.get("pdf_name"):
            runs[d["pdf_name"]] = d  # latest run per document wins (files sort by timestamp)
    return [
        {"document": d["pdf_name"], "pages": d.get("pages_processed"), "events_found": d.get("events_extracted"),
         "ms_per_page": d.get("ms_per_page"), "total_ms": d.get("processing_time_ms"), "run_at": d.get("timestamp")}
        for d in runs.values()
    ]


@router.get("/models/benchmarks")
async def model_benchmarks():
    hazard = _read(MODELS_DIR / "hazard_model_metrics.json")
    sensor = _read(MODELS_DIR / "sensor_benchmark.json")
    extraction = extraction_benchmark()
    extraction["real_document_runs"] = real_document_runs()
    return {
        "offset_hazard_models": hazard,
        "sensor_risk_models": sensor,
        "document_extraction": extraction,
    }
