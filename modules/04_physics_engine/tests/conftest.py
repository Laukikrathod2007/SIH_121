"""Pytest path setup for Module 4's tests -- puts the module root on sys.path
so `from simulation...`, `from data_pipeline...`, `from models...` resolve."""
from __future__ import annotations

import sys
from pathlib import Path

_MODULE_04_ROOT = Path(__file__).resolve().parent.parent
if str(_MODULE_04_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_04_ROOT))
