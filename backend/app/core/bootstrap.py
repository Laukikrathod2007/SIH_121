"""
Startup bootstrap: runs the NWIS data pipeline so the app is fully populated
on first load, not only after someone clicks through it.

Order (each step idempotent — safe on every restart):
  1. Demo data layer   — build demo_augmentation.json and the source DDR/WCR
                          PDFs if they are missing (deterministic generators).
  2. Document pipeline — every bundled report in data/sample_docs goes through
                          the real extraction pipeline (text/OCR -> entities ->
                          physics validation) exactly like an upload, and is
                          recorded as a completed ingestion job. Reports already
                          processed are skipped.
  3. Knowledge bridge  — all extraction results are merged into the live
                          knowledge repository (searchable, and feeding the
                          risk corridors when depth + well are known).
  4. Alert scan        — the risk/alert engine runs for the active well at its
                          planning depth so the alert center reflects the
                          current state. Skipped if that well already has alerts.

Real deployments replace step 1 with the OIL archive and step 2's sample folder
with the ingestion drop folder; nothing else changes.
"""

from __future__ import annotations

import importlib.util
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.core.logging import logger

SYNTHETIC_DIR = settings.SYNTHETIC_DATA_DIR
SOURCE_DOCS_DIR = settings.DATA_DIR / "source_documents"
OUTPUT_DIR = settings.DATA_DIR / "output"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SYNTHETIC_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def ensure_demo_data() -> None:
    aug = SYNTHETIC_DIR / "demo_augmentation.json"
    if not aug.exists():
        out = _load_script("augment_demo").build()
        aug.write_text(json.dumps(out, indent=2), encoding="utf-8")
        logger.info("Bootstrap: generated demo_augmentation.json")
    samples_missing = not any(settings.SAMPLE_DOCS_DIR.glob("DDR_*.pdf"))
    if not SOURCE_DOCS_DIR.exists() or not any(SOURCE_DOCS_DIR.glob("*.pdf")) or samples_missing:
        _load_script("generate_source_documents").main()
        logger.info("Bootstrap: generated source documents and sample reports")


def _processed_sources() -> set[str]:
    names = set()
    for f in OUTPUT_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            names.add(re.sub(r"^JOB-[0-9A-F]+_", "", data.get("source_filename") or "", flags=re.IGNORECASE))
        except Exception:
            continue
    return names


def process_bundled_reports() -> int:
    """Run each bundled sample report through the real pipeline once."""
    from app.core.job_store import SQLiteJobStore
    from app.modules.document_intelligence.models.schemas import IngestJobStatus
    from app.modules.document_intelligence.services.pipeline_orchestrator import process_document

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = _processed_sources()
    store = SQLiteJobStore()
    processed = 0
    for src in sorted(settings.SAMPLE_DOCS_DIR.glob("*.pdf")):
        if src.name in done:
            continue
        job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
        upload = settings.UPLOAD_DIR / f"{job_id}_{src.name}"
        upload.write_bytes(src.read_bytes())
        store.create(job_id, {
            "job_id": job_id, "filename": src.name, "upload_path": str(upload),
            "status": IngestJobStatus.PROCESSING, "progress_percent": 0, "current_page": 0, "total_pages": 0,
            "message": "Startup pipeline: processing bundled report", "document_id": None, "error": None,
            "submitted_at": datetime.utcnow().isoformat(),
        })
        try:
            result = process_document(upload, job_id=job_id)
            store.update(
                job_id, status=IngestJobStatus.COMPLETED, progress_percent=100,
                current_page=result.pages_processed, total_pages=result.total_pages,
                document_id=result.document_id,
                message=(f"Completed: {result.pages_processed} pages | {len(result.all_drilling_events)} events | "
                         f"Confidence: {result.overall_confidence:.1%}"),
            )
            processed += 1
        except Exception as exc:  # one bad report must not stop the app
            logger.exception(f"Bootstrap: pipeline failed for {src.name}: {exc}")
            store.update(job_id, status=IngestJobStatus.FAILED, error=str(exc), message=f"Processing failed: {exc}")
    return processed


def seed_alerts() -> int:
    from app.modules.well_intelligence.services.alert_center import AlertCenter
    from app.modules.well_intelligence.services.data_store import NWISDataStore
    from app.modules.well_intelligence.services.orchestrator import NWISOrchestrator

    store = NWISDataStore()
    well = store.wells_by_id.get(store.active_well_id)
    center = AlertCenter()
    if well is None or center.list(well_id=well.well_id):
        return 0
    # Same planning depth the Live well screen opens at (85% of TD).
    depth = round(well.total_depth_md_m * 0.85)
    result = NWISOrchestrator(store).analyze(active_well_id=well.well_id, current_depth_m=depth)
    return len(center.evaluate(result, source="startup_scan"))


def ensure_model_benchmarks() -> None:
    """Train/benchmark models whose measured metrics are missing.
    Offset hazard models are quick (seconds) and run inline; the sensor-model
    benchmark (~35 s of physics simulation) runs in a background thread so the
    API is available immediately."""
    import threading

    models_dir = settings.DATA_DIR / "models"
    if not (models_dir / "hazard_model_metrics.json").exists():
        from app.modules.well_intelligence.ml.train_hazard_models import train_all_models
        train_all_models()
        logger.info("Bootstrap: trained offset hazard models")
    if not (models_dir / "sensor_benchmark.json").exists():
        def _run():
            try:
                from app.modules.predictive_analytics.evaluation.model_benchmarking import ModelBenchmarkPipeline
                ModelBenchmarkPipeline().run_full_training_and_benchmarking()
                logger.success("Bootstrap: sensor-model benchmark complete")
            except Exception as exc:
                logger.exception(f"Bootstrap: sensor benchmark failed: {exc}")
        threading.Thread(target=_run, name="sensor-benchmark", daemon=True).start()


def run_startup_pipeline() -> dict:
    """Steps 2-4. Call ensure_demo_data() BEFORE the data store loads."""
    from app.modules.well_intelligence.services.document_bridge import ingest_all_outputs

    summary = {}
    try:
        summary["reports_processed"] = process_bundled_reports()
    except Exception as exc:
        logger.exception(f"Bootstrap: document pipeline failed: {exc}")
    try:
        summary["events_bridged"] = ingest_all_outputs()
    except Exception as exc:
        logger.exception(f"Bootstrap: knowledge bridge failed: {exc}")
    try:
        ensure_model_benchmarks()
    except Exception as exc:
        logger.exception(f"Bootstrap: model benchmarks failed: {exc}")
    try:
        summary["alerts_raised"] = seed_alerts()
    except Exception as exc:
        logger.exception(f"Bootstrap: alert scan failed: {exc}")
    logger.success(f"Startup pipeline complete: {summary}")
    return summary
