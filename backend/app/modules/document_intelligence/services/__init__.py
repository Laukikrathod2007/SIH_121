"""
Document Intelligence Services Package.
"""

from app.modules.document_intelligence.services.native_extractor import (
    extract_page_native,
    detect_document_type,
    extract_document_metadata,
    get_word_bounding_boxes,
    is_page_scanned,
)
from app.modules.document_intelligence.services.ocr_engine import (
    extract_document_with_docling,
    create_tier2_page_result,
)
from app.modules.document_intelligence.services.entity_extractor import extract_all_entities
from app.modules.document_intelligence.services.template_learner import (
    learn_from_document,
    get_template_for_document,
    DocumentTemplate,
)
from app.modules.document_intelligence.services.physics_validator import run_physics_validation
from app.modules.document_intelligence.services.pipeline_orchestrator import process_document

__all__ = [
    "extract_page_native",
    "detect_document_type",
    "extract_document_metadata",
    "get_word_bounding_boxes",
    "is_page_scanned",
    "extract_document_with_docling",
    "create_tier2_page_result",
    "extract_all_entities",
    "learn_from_document",
    "get_template_for_document",
    "DocumentTemplate",
    "run_physics_validation",
    "process_document",
]
