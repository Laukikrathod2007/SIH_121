"""
NWIS Document Intelligence Module.
Provides native/OCR document parsing, domain NER, coordinate learning, and physics validation.
"""

from app.modules.document_intelligence.routes.document_routes import router as document_router
from app.modules.document_intelligence.controllers.document_controller import (
    DocumentController,
    document_controller,
)

__all__ = ["document_router", "DocumentController", "document_controller"]
