"""
Pytest path setup for Module 5's tests.

test_system_review.py exercises the full causal chain (physics simulation ->
feature engineering -> predictive fusion -> alerting), so it imports directly
from Module 4 (modules/04_physics_engine)'s simulation/, models/ and
data_pipeline/ packages, not just Module 5's own predictive/ package. This
mirrors the same sys.path insert predictive/realtime_inference.py does at
runtime (see the comment there) -- test collection needs the same access.
"""
from __future__ import annotations

import sys
from pathlib import Path

_MODULE_05_ROOT = Path(__file__).resolve().parent.parent
_MODULE_04_ROOT = _MODULE_05_ROOT.parent / "04_physics_engine"

for _root in (_MODULE_05_ROOT, _MODULE_04_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
