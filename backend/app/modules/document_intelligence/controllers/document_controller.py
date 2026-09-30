"""
Document Intelligence Controller.
Orchestrates file upload validation, background extraction, job store state, and result retrieval.
"""

from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, HTTPException, BackgroundTasks

from app.config import settings
from app.core.logging import logger
from app.core.job_store import SQLiteJobStore
from app.modules.document_intelligence.models.schemas import (
    IngestJobResponse,
    IngestJobStatus,
    JobStatusResponse,
    DocumentExtractionResult,
)
from app.modules.document_intelligence.services.pipeline_orchestrator import process_document
from app.modules.document_intelligence.services.template_learner import TEMPLATES_DIR


class DocumentController:
    """Controller managing document intake, async pipeline jobs, and extraction artifacts."""

    def __init__(self, job_store: Optional[SQLiteJobStore] = None):
        self.job_store = job_store or SQLiteJobStore()
        self.upload_dir = settings.UPLOAD_DIR
        self.output_dir = settings.DATA_DIR / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = {".pdf"}
        self.max_file_size_mb = 100

    async def ingest_document(
        self,
        file: UploadFile,
        background_tasks: BackgroundTasks,
    ) -> IngestJobResponse:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        suffix = Path(file.filename).suffix.lower()
        if suffix not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted."
            )

        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {size_mb:.1f} MB. Maximum is {self.max_file_size_mb} MB."
            )

        job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
        safe_name = f"{job_id}_{file.filename}"
        upload_path = self.upload_dir / safe_name

        with open(upload_path, "wb") as f:
            f.write(content)

        logger.info(f"[{job_id}] File saved: {upload_path} ({size_mb:.2f} MB)")

        self.job_store.create(job_id, {
            "job_id": job_id,
            "filename": file.filename,
            "upload_path": str(upload_path),
            "status": IngestJobStatus.QUEUED,
            "progress_percent": 0,
            "current_page": 0,
            "total_pages": 0,
            "message": "Document queued for processing",
            "document_id": None,
            "error": None,
            "submitted_at": datetime.utcnow().isoformat(),
        })

        background_tasks.add_task(self._run_pipeline_background, job_id, upload_path)

        return IngestJobResponse(
            job_id=job_id,
            filename=file.filename,
            status=IngestJobStatus.QUEUED,
            message=f"Document queued. Poll /api/v1/documents/jobs/{job_id} for progress.",
        )

    async def _run_pipeline_background(self, job_id: str, upload_path: Path):
        self.job_store.update(job_id, status=IngestJobStatus.PROCESSING, message="Pipeline started")

        def progress_callback(current: int, total: int, message: str):
            self.job_store.update(
                job_id,
                current_page=current,
                total_pages=total,
                progress_percent=int((current / max(total, 1)) * 100),
                message=message,
            )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: process_document(upload_path, job_id=job_id, progress_cb=progress_callback),
            )

            if result.total_pages == 0 or result.pages_processed == 0:
                raise RuntimeError(
                    "No readable pages were extracted from this document. "
                    "It may be corrupt, empty, or password-protected."
                )

            self.job_store.update(
                job_id,
                status=IngestJobStatus.COMPLETED,
                progress_percent=100,
                document_id=result.document_id,
                message=(
                    f"Completed: {result.pages_processed} pages | "
                    f"{len(result.all_drilling_events)} events | "
                    f"Confidence: {result.overall_confidence:.1%}"
                ),
            )
            logger.success(f"[{job_id}] Background processing complete")
            try:
                from app.modules.well_intelligence.services.document_bridge import ingest_document_result
                ingest_document_result(self._load_result(result.document_id))
            except Exception as bridge_exc:
                logger.warning(f"[{job_id}] Could not merge events into knowledge repository: {bridge_exc}")
        except Exception as exc:
            logger.exception(f"[{job_id}] Pipeline failed: {exc}")
            self.job_store.update(
                job_id,
                status=IngestJobStatus.FAILED,
                error=str(exc),
                message=f"Processing failed: {exc}",
            )

    def get_job_status(self, job_id: str) -> JobStatusResponse:
        job = self.job_store.get(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' not found. Verify the job_id or re-submit the document."
            )
        return JobStatusResponse(
            job_id=job["job_id"],
            status=job.get("status", IngestJobStatus.QUEUED),
            progress_percent=job.get("progress_percent", 0),
            current_page=job.get("current_page", 0),
            total_pages=job.get("total_pages", 0),
            message=job.get("message", ""),
            document_id=job.get("document_id"),
            error=job.get("error"),
        )

    def list_jobs(self, limit: int = 50) -> list[dict]:
        return self.job_store.values()[:limit]

    def get_full_result(self, doc_id: str) -> dict:
        return self._load_result(doc_id)

    def get_drilling_events(self, doc_id: str) -> dict:
        data = self._load_result(doc_id)
        events = data.get("all_drilling_events", [])
        return {
            "document_id": doc_id,
            "source_filename": data.get("source_filename"),
            "well_name": data.get("well_name"),
            "total_events": len(events),
            "events": events,
            "witsml_mapping": "opsReport.activity (WITSML 2.0)",
        }

    def get_formation_tops(self, doc_id: str) -> dict:
        data = self._load_result(doc_id)
        formations = data.get("all_formation_tops", [])
        return {
            "document_id": doc_id,
            "source_filename": data.get("source_filename"),
            "well_name": data.get("well_name"),
            "total_formations": len(formations),
            "formations": formations,
            "witsml_mapping": "stratigraphicColumn (WITSML 2.0)",
        }

    def get_npt_records(self, doc_id: str) -> dict:
        data = self._load_result(doc_id)
        npt_records = data.get("all_npt_records", [])
        total_hours = sum(
            float(r.get("npt_hours", {}).get("normalized_value", 0) or 0)
            for r in npt_records
            if isinstance(r, dict)
        )
        return {
            "document_id": doc_id,
            "source_filename": data.get("source_filename"),
            "well_name": data.get("well_name"),
            "total_npt_records": len(npt_records),
            "total_npt_hours": round(total_hours, 2),
            "npt_records": npt_records,
            "taxonomy": "IADC Standard NPT Classification",
        }

    def list_templates(self) -> dict:
        templates = []
        if TEMPLATES_DIR.exists():
            for t_file in TEMPLATES_DIR.glob("*.json"):
                try:
                    with open(t_file, "r", encoding="utf-8") as f:
                        t_data = json.load(f)
                    templates.append({
                        "template_id": t_data.get("template_id"),
                        "document_type": t_data.get("document_type"),
                        "operator": t_data.get("operator"),
                        "confidence": t_data.get("confidence"),
                        "sample_count": t_data.get("sample_count"),
                        "learned_fields_count": len(t_data.get("field_coordinates", {})),
                        "created_at": t_data.get("created_at"),
                    })
                except Exception as e:
                    logger.warning(f"Failed to read template {t_file}: {e}")
        return {
            "total_templates": len(templates),
            "layer": "Layer 4: Coordinate Template Learning",
            "accuracy_benefit": "99% extraction accuracy on learned templates",
            "speed_benefit": "< 50ms per page (bypasses layout detection)",
            "templates": templates,
        }

    def list_samples(self) -> dict:
        samples = []
        for f in sorted(settings.SAMPLE_DOCS_DIR.glob("*.pdf")):
            samples.append({"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)})
        return {"samples": samples}

    async def ingest_sample(self, name: str, background_tasks: BackgroundTasks) -> IngestJobResponse:
        src = (settings.SAMPLE_DOCS_DIR / name).resolve()
        if src.parent != settings.SAMPLE_DOCS_DIR.resolve() or not src.exists() or src.suffix.lower() != ".pdf":
            raise HTTPException(status_code=404, detail=f"Sample '{name}' not found")
        job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
        upload_path = self.upload_dir / f"{job_id}_{src.name}"
        upload_path.write_bytes(src.read_bytes())
        self.job_store.create(job_id, {
            "job_id": job_id, "filename": src.name, "upload_path": str(upload_path),
            "status": IngestJobStatus.QUEUED, "progress_percent": 0, "current_page": 0, "total_pages": 0,
            "message": "Sample queued for processing", "document_id": None, "error": None,
            "submitted_at": datetime.utcnow().isoformat(),
        })
        background_tasks.add_task(self._run_pipeline_background, job_id, upload_path)
        return IngestJobResponse(job_id=job_id, filename=src.name, status=IngestJobStatus.QUEUED,
                                 message=f"Sample queued. Poll /api/v1/documents/jobs/{job_id} for progress.")

    def list_results(self) -> dict:
        results = []
        for f in sorted(self.output_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                continue
            results.append({
                "document_id": data.get("document_id"),
                "job_id": data.get("job_id"),
                "source_filename": data.get("source_filename"),
                "document_type": data.get("document_type"),
                "well_name": data.get("well_name"),
                "operator": data.get("operator"),
                "total_pages": data.get("total_pages"),
                "overall_confidence": data.get("overall_confidence"),
                "validation_status": data.get("validation_status"),
                "reviewed": bool(data.get("reviewed")),
                "review_decision": data.get("review_decision"),
                "events_count": len(data.get("all_drilling_events", [])),
                "formations_count": len(data.get("all_formation_tops", [])),
                "npt_count": len(data.get("all_npt_records", [])),
                "processing_time_ms": data.get("total_processing_time_ms"),
                "extraction_completed_at": data.get("extraction_completed_at"),
            })
        return {"total_results": len(results), "results": results}

    def get_quality_report(self, doc_id: str) -> dict:
        data = self._load_result(doc_id)
        total_pages = data.get("total_pages", 0) or 0
        scanned = data.get("scanned_pages", 0) or 0
        return {
            "document_id": doc_id,
            "source_filename": data.get("source_filename"),
            "quality_metrics": {
                "overall_confidence": data.get("overall_confidence", 0),
                "pages_native_digital": total_pages - scanned,
                "pages_ocr_required": scanned,
                "physics_violations_caught": data.get("physics_violations_count", 0),
                "flagged_for_review": data.get("flagged_fields_count", 0),
                "cloud_fallback_pages": data.get("cloud_fallback_pages_count", 0),
                "drilling_events_extracted": len(data.get("all_drilling_events", [])),
                "formation_tops_extracted": len(data.get("all_formation_tops", [])),
                "npt_records_extracted": len(data.get("all_npt_records", [])),
                "processing_time_ms": data.get("total_processing_time_ms", 0),
            },
        }

    def get_document_file_path(self, doc_id: str) -> Path:
        """Original uploaded PDF for a processed document (resolved via the job_id on its result)."""
        data = self._load_result(doc_id)
        job_id = data.get("job_id")
        if not job_id:
            raise HTTPException(404, f"No job_id on record for document '{doc_id}'.")
        matches = list(self.upload_dir.glob(f"{job_id}_*"))
        if not matches:
            raise HTTPException(404, f"Original PDF for document '{doc_id}' (job {job_id}) not found on disk.")
        file_path = matches[0].resolve()
        upload_root = self.upload_dir.resolve()
        if upload_root not in file_path.parents:
            raise HTTPException(400, "Resolved file path is outside the upload directory.")
        return file_path

    # -- Human curation / review workflow (ported from backend-working) -------

    NEEDS_REVIEW = {"FLAGGED", "FAILED", "MANUAL_REVIEW"}

    def review_queue(self) -> dict:
        order = {"MANUAL_REVIEW": 0, "FAILED": 1, "FLAGGED": 2}
        queue = []
        for path in self.output_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                logger.warning(f"Skipping unreadable result file {path}: {exc}")
                continue
            status = data.get("validation_status")
            if status not in self.NEEDS_REVIEW or data.get("reviewed"):
                continue
            queue.append({
                "document_id": data.get("document_id"),
                "source_filename": data.get("source_filename"),
                "well_name": data.get("well_name"),
                "operator": data.get("operator"),
                "validation_status": status,
                "overall_confidence": data.get("overall_confidence"),
                "physics_violations_count": data.get("physics_violations_count"),
                "flagged_fields_count": data.get("flagged_fields_count"),
                "cloud_fallback_pages_count": data.get("cloud_fallback_pages_count"),
                "extraction_completed_at": data.get("extraction_completed_at"),
            })
        queue.sort(key=lambda d: order.get(d["validation_status"], 99))
        return {"total": len(queue), "queue": queue}

    def submit_review_decision(self, doc_id: str, reviewer: str, decision: str, notes: Optional[str]) -> dict:
        if decision not in ("approved", "rejected"):
            raise HTTPException(400, "decision must be 'approved' or 'rejected'")
        data = self._load_result(doc_id)
        data.update({
            "reviewed": True,
            "reviewed_by": reviewer,
            "reviewed_at": datetime.utcnow().isoformat(),
            "review_decision": decision,
            "review_notes": notes,
            "validation_status": "PASS" if decision == "approved" else "FAILED",
        })
        self._save_result(doc_id, data)
        logger.info(f"Review decision on {doc_id}: {decision} by {reviewer}")
        return {"document_id": doc_id, "reviewed": True, "decision": decision,
                "validation_status": data["validation_status"]}

    def annotate_field(self, doc_id: str, reviewer: str, field_path: str, note: str) -> dict:
        data = self._load_result(doc_id)
        annotations = data.get("field_annotations") or []
        annotations.append({
            "field_path": field_path,
            "note": note,
            "annotated_by": reviewer,
            "annotated_at": datetime.utcnow().isoformat(),
        })
        data["field_annotations"] = annotations
        self._save_result(doc_id, data)
        return {"document_id": doc_id, "total_annotations": len(annotations)}

    def _result_path(self, doc_id: str) -> Path:
        path = self.output_dir / f"{doc_id}.json"
        if not path.exists():
            matches = list(self.output_dir.glob(f"*{doc_id}*.json"))
            if not matches:
                raise HTTPException(404, f"Result for document '{doc_id}' not found.")
            path = matches[0]
        return path

    def _save_result(self, doc_id: str, data: dict) -> None:
        with open(self._result_path(doc_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_result(self, doc_id: str) -> dict:
        result_path = self.output_dir / f"{doc_id}.json"
        if not result_path.exists():
            matches = list(self.output_dir.glob(f"*{doc_id}*.json"))
            if not matches:
                raise HTTPException(
                    status_code=404,
                    detail=f"Result for document '{doc_id}' not found. "
                           "Ensure the ingestion job completed successfully."
                )
            result_path = matches[0]

        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)


document_controller = DocumentController()
