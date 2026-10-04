"""
Tests for Pass 4's document -> PostgreSQL write-through and the document ->
drilling_events handoff (app.modules.document_intelligence.db.service).

Kinds: well-name resolution and ExtractedField-unwrapping are pure unit
tests (no database). The sync/handoff round-trip tests need a REACHABLE
PostgreSQL at localhost:5433 (database/docker-compose.yml's default) with
the canonical schema + migrate_seed.py's well catalog loaded; when it is
not reachable those tests are SKIPPED with an explicit reason, same
pattern as modules/02_nwis_backend/tests/test_db_foundation.py.
"""
from __future__ import annotations

import psycopg
import pytest

from app.modules.document_intelligence.db import service as doc_service
from app.modules.nwis.db import connection
from app.modules.nwis.db.connection import get_connection

TEST_DSN = "postgresql://nwis:nwis_dev_password@localhost:5433/nwis"


def _db_reachable() -> bool:
    try:
        with psycopg.connect(TEST_DSN, connect_timeout=2) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


_DB_UP = _db_reachable()


def requires_db(fn):
    skip = pytest.mark.skipif(
        not _DB_UP,
        reason="No reachable NWIS PostgreSQL at localhost:5433 -- start it (see database/README.md)",
    )
    return pytest.mark.db(skip(fn))


@pytest.fixture(autouse=True)
def _point_connection_at_test_db(monkeypatch):
    monkeypatch.setattr(connection, "_DSN", TEST_DSN)
    monkeypatch.setattr(connection, "_pool", None)
    yield
    connection.close_pool()


# ---------------------------------------------------------------------------
# resolve_well_id — pure unit tests, no database
# ---------------------------------------------------------------------------

KNOWN_IDS = ["15/9-F-1", "15/9-F-12", "WELL-BGJ-007", "WELL-NHK-001"]


def test_resolve_exact_match():
    assert doc_service.resolve_well_id("15/9-F-1", KNOWN_IDS) == "15/9-F-1"


def test_resolve_underscore_slash_variant():
    """Confirmed-real OCR variation: '15_9-F-1' for the real well_id '15/9-F-1'."""
    assert doc_service.resolve_well_id("15_9-F-1", KNOWN_IDS) == "15/9-F-1"


def test_resolve_bare_well_code():
    """Synthetic wells' extracted well_name is the bare code without the
    'WELL-' prefix (e.g. 'BGJ-007' for well_id 'WELL-BGJ-007')."""
    assert doc_service.resolve_well_id("BGJ-007", KNOWN_IDS) == "WELL-BGJ-007"


def test_resolve_strips_known_report_type_prefix():
    """Reproduces a confirmed-live bug in module 01's own filename-fallback
    well-name regex (tier1_native_extractor.py): for a filename shaped
    '{TYPE}_WELL-{id}...pdf' it extracts 'DDR_WELL-NHK-001' instead of
    'WELL-NHK-001' -- this resolver works around it at the data-
    interpretation layer rather than touching the extraction pipeline."""
    assert doc_service.resolve_well_id("DDR_WELL-NHK-001", KNOWN_IDS) == "WELL-NHK-001"
    assert doc_service.resolve_well_id("WCR-WELL-BGJ-007", KNOWN_IDS) == "WELL-BGJ-007"


@pytest.mark.parametrize("junk", ["REPORT", "evaluation", "/", "NHK-105", "", None])
def test_resolve_rejects_unresolvable_input(junk):
    """Junk / near-miss / unknown well names must resolve to None, never a
    guessed well_id -- observed verbatim in real extraction output."""
    assert doc_service.resolve_well_id(junk, KNOWN_IDS) is None


def test_unwrap_extracted_field_dict():
    assert doc_service._unwrap({"normalized_value": 1850.5, "confidence": 0.9}) == 1850.5


def test_unwrap_bare_scalar():
    assert doc_service._unwrap(42.0) == 42.0


def test_unwrap_none():
    assert doc_service._unwrap(None) is None


# ---------------------------------------------------------------------------
# sync_document / handoff_events — require a live database
# ---------------------------------------------------------------------------

def _fake_result(**overrides) -> dict:
    base = {
        "document_id": "DOC-TEST-FIXTURE-0001",
        "job_id": "JOB-TESTFIXTURE",
        "source_filename": "test_fixture.pdf",
        "document_type": "DAILY_DRILLING_REPORT",
        "well_name": "WELL-NHK-001",
        "operator": "Oil India Limited",
        "report_date": None,
        "total_pages": 1, "pages_processed": 1, "scanned_pages": 0,
        "template_used": None,
        "extraction_started_at": "2026-10-04T00:00:00",
        "extraction_completed_at": "2026-10-04T00:00:01",
        "total_processing_time_ms": 100.0,
        "cloud_fallback_pages_count": 0, "cloud_fallback_providers_used": [],
        "total_npt_hours": 0.0,
        "validation_status": "PASS",
        "overall_confidence": 0.9,
        "flagged_fields_count": 0, "physics_violations_count": 0,
        "witsml_compliant": True,
        "reviewed": False, "reviewed_by": None, "reviewed_at": None,
        "review_decision": None, "review_notes": None, "field_annotations": [],
        "all_formation_tops": [], "all_npt_records": [], "all_casing_records": [],
        "mud_properties": [], "all_drilling_events": [],
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _cleanup_fixture_rows():
    yield
    if not _DB_UP:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM drilling_events WHERE event_id LIKE 'EVT-TESTFIXTURE%'")
        conn.execute("DELETE FROM document_review WHERE document_id LIKE 'DOC-TEST-FIXTURE%'")
        conn.execute("DELETE FROM document_extractions WHERE document_id LIKE 'DOC-TEST-FIXTURE%'")
        conn.execute("DELETE FROM documents WHERE document_id LIKE 'DOC-TEST-FIXTURE%'")


@requires_db
def test_sync_document_resolves_well_and_upserts_idempotently():
    result = _fake_result()

    first = doc_service.sync_document(result)
    assert first["synced"] is True
    assert first["well_id"] == "WELL-NHK-001"

    second = doc_service.sync_document(result)
    assert second["synced"] is True

    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE document_id = %s", (result["document_id"],)
        ).fetchone()[0]
    assert count == 1, "re-syncing the same document_id must UPSERT, never duplicate"


@requires_db
def test_handoff_skips_unapproved_document():
    """An un-reviewed document's events are extraction candidates, not
    confirmed drilling facts -- migrated=0 regardless of event content."""
    result = _fake_result(all_drilling_events=[{
        "event_id": "EVT-TESTFIXTURE1", "event_type": "MUD_LOSS", "severity": "HIGH",
        "depth_start_md_m": {"normalized_value": 1850.5}, "depth_end_md_m": None,
        "formation": "Barail Sandstone", "raw_narrative": "test", "loss_rate_bbl_hr": None,
        "npt_hours": 0.0, "mitigation_description": None, "outcome": None, "confidence": 0.9,
    }])
    out = doc_service.handoff_events(result)
    assert out["migrated"] == 0
    assert out["reason"] == "not_approved"


@requires_db
def test_handoff_migrates_approved_event_with_resolvable_well_and_depth():
    result = _fake_result(
        reviewed=True, reviewed_by="pytest", review_decision="approved",
        all_drilling_events=[{
            "event_id": "EVT-TESTFIXTURE2", "event_type": "MUD_LOSS", "severity": "HIGH",
            "depth_start_md_m": {"normalized_value": 1850.5}, "depth_end_md_m": None,
            "formation": "Barail Sandstone", "raw_narrative": "test event", "loss_rate_bbl_hr": None,
            "npt_hours": 2.0, "mitigation_description": "raised mud weight", "outcome": "controlled",
            "confidence": 0.9,
        }],
    )
    # drilling_events.source_document_id REFERENCES documents(document_id)
    # -- the real call order (orchestrator.py then review.py) always syncs
    # the document before any event handoff can run; this fixture mirrors
    # that order rather than skipping straight to handoff_events().
    doc_service.sync_document(result)
    out = doc_service.handoff_events(result)
    assert out["migrated"] == 1
    assert out["skipped"] == 0
    assert out["well_id"] == "WELL-NHK-001"

    with get_connection() as conn:
        row = conn.execute(
            "SELECT well_id, event_type, source_type, source_document_id FROM drilling_events WHERE event_id = %s",
            ("EVT-TESTFIXTURE2",),
        ).fetchone()
    assert row == ("WELL-NHK-001", "MUD_LOSS", "REAL", result["document_id"])

    # Re-running must UPSERT, not duplicate.
    doc_service.handoff_events(result)
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM drilling_events WHERE event_id = %s", ("EVT-TESTFIXTURE2",)
        ).fetchone()[0]
    assert count == 1


@requires_db
def test_handoff_skips_unmapped_hazard_type_without_inventing_one():
    """GAS_INFLUX/LOST_CIRCULATION/EQUIPMENT_FAILURE/etc. have no row in
    the canonical hazard_type table -- must be skipped, never coerced."""
    result = _fake_result(
        reviewed=True, reviewed_by="pytest", review_decision="approved",
        all_drilling_events=[{
            "event_id": "EVT-TESTFIXTURE3", "event_type": "GAS_INFLUX", "severity": "HIGH",
            "depth_start_md_m": {"normalized_value": 2000.0}, "depth_end_md_m": None,
            "formation": None, "raw_narrative": "test", "loss_rate_bbl_hr": None,
            "npt_hours": 0.0, "mitigation_description": None, "outcome": None, "confidence": 0.9,
        }],
    )
    out = doc_service.handoff_events(result)
    assert out["migrated"] == 0
    assert out["skipped"] == 1
    assert out["skip_detail"][0]["reason"] == "unmapped_hazard_type"

    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM drilling_events WHERE event_id = %s", ("EVT-TESTFIXTURE3",)
        ).fetchone()[0]
    assert count == 0


@requires_db
def test_handoff_skips_event_missing_depth():
    result = _fake_result(
        reviewed=True, reviewed_by="pytest", review_decision="approved",
        all_drilling_events=[{
            "event_id": "EVT-TESTFIXTURE4", "event_type": "KICK", "severity": "HIGH",
            "depth_start_md_m": None, "depth_end_md_m": None,
            "formation": None, "raw_narrative": "test", "loss_rate_bbl_hr": None,
            "npt_hours": 0.0, "mitigation_description": None, "outcome": None, "confidence": 0.9,
        }],
    )
    out = doc_service.handoff_events(result)
    assert out["migrated"] == 0
    assert out["skipped"] == 1
    assert out["skip_detail"][0]["reason"] == "missing_depth"


@requires_db
def test_handoff_skips_unresolvable_well_name():
    result = _fake_result(
        well_name="REPORT",
        reviewed=True, reviewed_by="pytest", review_decision="approved",
        all_drilling_events=[{
            "event_id": "EVT-TESTFIXTURE5", "event_type": "KICK", "severity": "HIGH",
            "depth_start_md_m": {"normalized_value": 2000.0}, "depth_end_md_m": None,
            "formation": None, "raw_narrative": "test", "loss_rate_bbl_hr": None,
            "npt_hours": 0.0, "mitigation_description": None, "outcome": None, "confidence": 0.9,
        }],
    )
    out = doc_service.handoff_events(result)
    assert out["migrated"] == 0
    assert out["skipped"] == 1
    assert out["skip_detail"][0]["reason"] == "unresolved_well_name"
