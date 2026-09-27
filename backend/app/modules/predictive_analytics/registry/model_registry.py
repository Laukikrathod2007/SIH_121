"""
Module 5 Predictive Risk Analytics -- Model Registry.

Implements Part K:
Tracks model metadata, artifact versions, training/validation wells,
evaluation metrics, and calibration scores.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.config import settings

REGISTRY_DIR = settings.DATA_DIR / "models"
REGISTRY_FILE = REGISTRY_DIR / "model_registry.json"


class ModelMetadata(BaseModel):
    model_id: str
    model_name: str
    version: str = "1.0.0"
    hazard: str
    architecture: str
    dataset_version: str = "1.0.0"
    feature_version: str = "1.0.0"
    preprocessor_version: str = "1.0.0"
    physics_version: str = "1.0.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    training_wells: List[str] = Field(default_factory=list)
    validation_wells: List[str] = Field(default_factory=list)
    test_wells: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    calibration: Dict[str, float] = Field(default_factory=dict)
    is_active: bool = True


class ModelRegistry:
    """Persistent JSON-backed registry of trained models and artifact versions."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.file_path = registry_file or REGISTRY_FILE
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, ModelMetadata] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for m in data:
                entry = ModelMetadata(**m)
                self._entries[entry.model_id] = entry
        except Exception:
            self._entries = {}

    def save(self) -> None:
        data = [m.model_dump() for m in self._entries.values()]
        tmp_file = self.file_path.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_file.replace(self.file_path)

    def register_model(self, meta: ModelMetadata) -> None:
        self._entries[meta.model_id] = meta
        self.save()

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        return self._entries.get(model_id)

    def list_models(self) -> List[ModelMetadata]:
        return list(self._entries.values())
