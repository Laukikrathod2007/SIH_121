"""
Unit Tests for Document Intelligence Pipeline & Domain Physics Validator.
"""

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.document_intelligence.models.domain_rules import validate_field, fuzzy_match_formation


def test_physics_validation_rules():
    # Test valid mud weight
    valid, status, msg = validate_field("mud_weight_ppg", 11.5)
    assert valid is True
    assert status == "PASS"

    # Test physically impossible mud weight (< freshwater 8.33 ppg)
    valid, status, msg = validate_field("mud_weight_ppg", 5.2)
    assert valid is False
    assert status == "FAIL"

    # Test physically impossible ROP (> 200 m/hr)
    valid, status, msg = validate_field("rop_m_hr", 350.0)
    assert valid is False
    assert status == "FAIL"


def test_fuzzy_formation_matching():
    matched = fuzzy_match_formation("Tipam Sandsone")
    assert matched in ["Tipam Sandstone", "TIPAM"]

    matched_kopili = fuzzy_match_formation("KOPLI")
    assert matched_kopili in ["Kopili Shale", "KOPILI"]


if __name__ == "__main__":
    test_physics_validation_rules()
    test_fuzzy_formation_matching()
    print("[PASS] All Document Intelligence tests passed!")
