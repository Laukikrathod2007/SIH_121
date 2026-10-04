"""
Repository layer for module 01's PostgreSQL write-through — the only place
in this package that writes raw SQL. service.py calls these; the pipeline
orchestrator and review routes never touch a connection or a SQL string
directly (same separation module 02's db/ package already uses).

All writes here are idempotent UPSERTs keyed on the real business key the
application already generates (document_id, event_id) — re-running the
same extraction (e.g. a retried ingest, or this write-through itself being
retried after a transient DB error) must not create duplicate rows.
"""

from __future__ import annotations

from typing import Any, Optional

from psycopg.rows import dict_row
from psycopg.types.json import Json


class DocumentRepository:
    """Data access for `documents` + `document_review`."""

    def __init__(self, conn):
        self._conn = conn

    def upsert_document(self, doc: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO documents (
                document_id, job_id, source_filename, document_type, well_id, well_name,
                operator, report_date, total_pages, pages_processed, scanned_pages,
                template_used, extraction_started_at, extraction_completed_at,
                total_processing_time_ms, cloud_fallback_pages_count,
                cloud_fallback_providers_used, total_npt_hours, validation_status,
                overall_confidence, flagged_fields_count, physics_violations_count,
                witsml_compliant
            ) VALUES (
                %(document_id)s, %(job_id)s, %(source_filename)s, %(document_type)s,
                %(well_id)s, %(well_name)s, %(operator)s, %(report_date)s, %(total_pages)s,
                %(pages_processed)s, %(scanned_pages)s, %(template_used)s,
                %(extraction_started_at)s, %(extraction_completed_at)s,
                %(total_processing_time_ms)s, %(cloud_fallback_pages_count)s,
                %(cloud_fallback_providers_used)s, %(total_npt_hours)s, %(validation_status)s,
                %(overall_confidence)s, %(flagged_fields_count)s, %(physics_violations_count)s,
                %(witsml_compliant)s
            )
            ON CONFLICT (document_id) DO UPDATE SET
                job_id = excluded.job_id,
                document_type = excluded.document_type,
                well_id = excluded.well_id,
                well_name = excluded.well_name,
                operator = excluded.operator,
                report_date = excluded.report_date,
                total_pages = excluded.total_pages,
                pages_processed = excluded.pages_processed,
                scanned_pages = excluded.scanned_pages,
                template_used = excluded.template_used,
                extraction_completed_at = excluded.extraction_completed_at,
                total_processing_time_ms = excluded.total_processing_time_ms,
                cloud_fallback_pages_count = excluded.cloud_fallback_pages_count,
                cloud_fallback_providers_used = excluded.cloud_fallback_providers_used,
                total_npt_hours = excluded.total_npt_hours,
                validation_status = excluded.validation_status,
                overall_confidence = excluded.overall_confidence,
                flagged_fields_count = excluded.flagged_fields_count,
                physics_violations_count = excluded.physics_violations_count,
                witsml_compliant = excluded.witsml_compliant
            """,
            doc,
        )

    def upsert_review(self, doc_id: str, review: dict[str, Any]) -> None:
        """review keys: reviewed, reviewed_by, reviewed_at, review_decision,
        review_notes, field_annotations (a list — stored as JSONB)."""
        self._conn.execute(
            """
            INSERT INTO document_review (
                document_id, reviewed, reviewed_by, reviewed_at, review_decision,
                review_notes, field_annotations
            ) VALUES (
                %(document_id)s, %(reviewed)s, %(reviewed_by)s, %(reviewed_at)s,
                %(review_decision)s, %(review_notes)s, %(field_annotations)s
            )
            ON CONFLICT (document_id) DO UPDATE SET
                reviewed = excluded.reviewed,
                reviewed_by = excluded.reviewed_by,
                reviewed_at = excluded.reviewed_at,
                review_decision = excluded.review_decision,
                review_notes = excluded.review_notes,
                field_annotations = excluded.field_annotations
            """,
            {
                "document_id": doc_id,
                "reviewed": review.get("reviewed", False),
                "reviewed_by": review.get("reviewed_by"),
                "reviewed_at": review.get("reviewed_at"),
                "review_decision": review.get("review_decision"),
                "review_notes": review.get("review_notes"),
                "field_annotations": Json(review.get("field_annotations") or []),
            },
        )

    def insert_extractions(self, document_id: str, extractions: list[dict[str, Any]]) -> int:
        """Generic field/value/confidence rows (document_extractions —
        schema.sql's "task requirement #7" table). Re-inserted fresh on
        every write-through: delete-then-insert for this one document
        rather than an UPSERT, since document_extractions rows have no
        natural key of their own (bigserial id) and the set of extracted
        fields for a given document_id is wholly owned/regenerated by that
        document's own extraction, not accumulated across runs."""
        if not extractions:
            self._conn.execute("DELETE FROM document_extractions WHERE document_id = %s", (document_id,))
            return 0
        self._conn.execute("DELETE FROM document_extractions WHERE document_id = %s", (document_id,))
        with self._conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO document_extractions (
                    document_id, field_name, field_value, confidence,
                    extraction_method, page_number, validation_status
                ) VALUES (%(document_id)s, %(field_name)s, %(field_value)s, %(confidence)s,
                          %(extraction_method)s, %(page_number)s, %(validation_status)s)
                """,
                extractions,
            )
        return len(extractions)

    def get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT d.*, r.reviewed, r.reviewed_by, r.reviewed_at, r.review_decision,
                       r.review_notes, r.field_annotations
                FROM documents d
                LEFT JOIN document_review r ON r.document_id = d.document_id
                WHERE d.document_id = %s
                """,
                (document_id,),
            )
            return cur.fetchone()

    def count_documents(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


class EventHandoffRepository:
    """Data access for the document -> drilling_events handoff (`wells`
    FK lookups + idempotent drilling_events UPSERT)."""

    def __init__(self, conn):
        self._conn = conn

    def well_exists(self, well_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM wells WHERE well_id = %s", (well_id,)).fetchone()
        return row is not None

    def valid_hazard_codes(self) -> set[str]:
        rows = self._conn.execute("SELECT code FROM hazard_type").fetchall()
        return {r[0] for r in rows}

    def upsert_event(self, event: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO drilling_events (
                event_id, well_id, event_type, severity, depth_start_md_m, depth_end_md_m,
                formation, raw_narrative, npt_hours, loss_rate_bbl_hr,
                mitigation_description, outcome, confidence, source_document_id,
                source_page, extraction_confidence, source_type
            ) VALUES (
                %(event_id)s, %(well_id)s, %(event_type)s, %(severity)s, %(depth_start_md_m)s,
                %(depth_end_md_m)s, %(formation)s, %(raw_narrative)s, %(npt_hours)s,
                %(loss_rate_bbl_hr)s, %(mitigation_description)s, %(outcome)s, %(confidence)s,
                %(source_document_id)s, %(source_page)s, %(extraction_confidence)s, %(source_type)s
            )
            ON CONFLICT (event_id) DO UPDATE SET
                well_id = excluded.well_id,
                event_type = excluded.event_type,
                severity = excluded.severity,
                depth_start_md_m = excluded.depth_start_md_m,
                depth_end_md_m = excluded.depth_end_md_m,
                formation = excluded.formation,
                raw_narrative = excluded.raw_narrative,
                npt_hours = excluded.npt_hours,
                loss_rate_bbl_hr = excluded.loss_rate_bbl_hr,
                mitigation_description = excluded.mitigation_description,
                outcome = excluded.outcome,
                confidence = excluded.confidence,
                source_document_id = excluded.source_document_id,
                source_page = excluded.source_page,
                extraction_confidence = excluded.extraction_confidence
            """,
            event,
        )
