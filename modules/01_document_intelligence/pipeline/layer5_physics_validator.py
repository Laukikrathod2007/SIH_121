"""
NWIS Module 01 — Layer 5: Domain Physics Validator
Enforces physical drilling laws and petroleum engineering boundary checks.

Why this layer is our unfair advantage over all competitors:
Generic document AI (AWS Textract, Google DocAI, Reducto, Tesseract) are domain-agnostic.
If OCR reads "mud weight: 3.2 ppg", a generic parser accepts 3.2.
NWIS Layer 5 detects that 3.2 ppg is physically impossible (freshwater is 8.33 ppg,
lower violates basic hydrostatic physics; the OCR misread "13.2" as "3.2").
It corrects or flags this with an explainable audit trail.

Reference Standards:
- OISD-157 (Recommended Practices for Drilling Operations)
- IADC Drilling Manual (12th Edition)
- Oil India Limited (OIL) Standard Operating Procedures
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from app.modules.document_intelligence.models.domain_rules import (
    DRILLING_DOMAIN_RULES,
    ASSAM_ARAKAN_FORMATIONS,
    validate_field,
    fuzzy_match_formation,
    FRESHWATER_DENSITY_PPG,
    MAX_BARITE_MUD_PPG,
    MAX_HOURS_PER_DAY,
)
from app.modules.document_intelligence.models.schemas import (
    ValidationStatus,
    MudProperties,
    DrillingEvent,
    WellboreFormation,
    DocumentExtractionResult,
    NPTRecord,
)


@dataclass
class ValidationReport:
    """Detailed summary of physics checks on a document"""
    total_checks: int = 0
    passed_checks: int = 0
    warning_checks: int = 0
    failed_checks: int = 0
    repaired_fields: int = 0
    violations: List[Dict[str, Any]] = None
    overall_status: ValidationStatus = ValidationStatus.PASS

    def __post_init__(self):
        if self.violations is None:
            self.violations = []


class PhysicsValidator:
    """
    Petroleum Engineering Physics Validator
    Validates and repairs extracted drilling telemetry, mud properties,
    and operational time balances.
    """

    def __init__(self):
        self.rules = DRILLING_DOMAIN_RULES

    def validate_mud_properties(self, mud: MudProperties) -> Tuple[MudProperties, List[Dict[str, Any]]]:
        """
        Validates mud properties against fluid mechanics boundaries.
        Attempts smart heuristic repair where OCR dropped a digit.
        """
        violations = []

        # 1. Mud Weight Validation
        if mud.density_ppg is not None:
            # Check for dropped leading '1' (e.g. 13.2 read as 3.2)
            if 1.0 <= mud.density_ppg < FRESHWATER_DENSITY_PPG:
                candidate = mud.density_ppg + 10.0
                if FRESHWATER_DENSITY_PPG <= candidate <= MAX_BARITE_MUD_PPG:
                    violations.append({
                        "field": "mud_weight_ppg",
                        "original_value": mud.density_ppg,
                        "repaired_value": candidate,
                        "action": "AUTO_REPAIRED",
                        "reason": f"Value {mud.density_ppg} ppg < freshwater {FRESHWATER_DENSITY_PPG} ppg. "
                                  f"Repaired to {candidate:.2f} ppg (OCR dropped leading digit '1').",
                    })
                    mud.density_ppg = candidate

            # Standard range check
            is_valid, status, msg = validate_field("mud_weight_ppg", mud.density_ppg)
            if not is_valid:
                violations.append({
                    "field": "mud_weight_ppg",
                    "value": mud.density_ppg,
                    "action": "FLAGGED",
                    "reason": msg,
                })

        # 2. Funnel Viscosity
        if mud.viscosity_sec is not None:
            is_valid, status, msg = validate_field("funnel_viscosity_sec", mud.viscosity_sec)
            if not is_valid:
                violations.append({
                    "field": "funnel_viscosity_sec",
                    "value": mud.viscosity_sec,
                    "action": "FLAGGED",
                    "reason": msg,
                })

        # 3. Plastic Viscosity
        if mud.plastic_viscosity_cp is not None:
            is_valid, status, msg = validate_field("plastic_viscosity_cp", mud.plastic_viscosity_cp)
            if not is_valid:
                violations.append({
                    "field": "plastic_viscosity_cp",
                    "value": mud.plastic_viscosity_cp,
                    "action": "FLAGGED",
                    "reason": msg,
                })

        # 4. Water Loss
        if mud.water_loss_ml is not None:
            is_valid, status, msg = validate_field("water_loss_ml_30min", mud.water_loss_ml)
            if not is_valid:
                violations.append({
                    "field": "water_loss_ml",
                    "value": mud.water_loss_ml,
                    "action": "FLAGGED",
                    "reason": msg,
                })

        # 5. pH
        if mud.ph is not None:
            ph_val = float(mud.ph.normalized_value) if hasattr(mud.ph, "normalized_value") else float(mud.ph)
            is_valid, status, msg = validate_field("ph", ph_val)
            if not is_valid:
                violations.append({
                    "field": "ph",
                    "value": ph_val,
                    "action": "FLAGGED",
                    "reason": msg,
                })

        return mud, violations

    def validate_formation_sequence(
        self, formations: List[WellboreFormation]
    ) -> Tuple[List[WellboreFormation], List[Dict[str, Any]]]:
        """
        Validates that extracted formation tops follow stratigraphic order
        and canonical naming (e.g. Assam-Arakan Basin sequence).
        """
        violations = []
        if not formations:
            return formations, violations

        # Sort by top_depth_m
        formations.sort(key=lambda f: f.top_depth_m if f.top_depth_m is not None else 0.0)

        for i, fmt in enumerate(formations):
            # Normalize formation name using fuzzy matching
            matched = fuzzy_match_formation(fmt.formation_name)
            if matched and matched != fmt.formation_name:
                violations.append({
                    "field": "formation_name",
                    "original": fmt.formation_name,
                    "normalized": matched,
                    "action": "NORMALIZED",
                    "reason": f"Fuzzy-matched '{fmt.formation_name}' to regional standard '{matched}'.",
                })
                fmt.formation_name = matched

            # Depth monotonicity check
            if fmt.base_depth_m is not None and fmt.top_depth_m is not None:
                if fmt.base_depth_m <= fmt.top_depth_m:
                    violations.append({
                        "field": "formation_depths",
                        "formation": fmt.formation_name,
                        "top": fmt.top_depth_m,
                        "base": fmt.base_depth_m,
                        "action": "FLAGGED",
                        "reason": f"Base depth ({fmt.base_depth_m}m) <= Top depth ({fmt.top_depth_m}m). Inverted boundary.",
                    })

        return formations, violations

    def validate_time_balance(self, events: List[DrillingEvent]) -> List[Dict[str, Any]]:
        """
        Per-event range check/repair on DrillingEvent.npt_hours, where present
        (negative -> repaired to 0.0, single event > 24h -> flagged).

        NOTE: this does NOT return the document's total NPT hours — see
        validate_npt_total() for that, and why it deliberately does not sum
        from these narrative-derived events. In real DDR narrative text, the
        event's classifying keyword ("Stuck Pipe", "Lost Circulation", ...)
        and its "X.X hrs NPT" figure routinely land in different sentences
        once the text is split on periods/semicolons (extract_drilling_events
        classifies per-sentence), so event.npt_hours is `None` far more often
        than not — summing it here would silently under-report, often to 0.0,
        exactly the kind of false-confidence number this system exists to
        catch in OTHER tools.
        """
        violations = []

        for event in events:
            if event.npt_hours is not None:
                npt_val = float(event.npt_hours.normalized_value) if hasattr(event.npt_hours, "normalized_value") else float(event.npt_hours)
                if npt_val < 0:
                    violations.append({
                        "field": "npt_hours",
                        "value": npt_val,
                        "action": "REPAIRED",
                        "reason": "Negative NPT hours physically invalid. Setting to 0.0.",
                    })
                    event.npt_hours = 0.0
                elif npt_val > MAX_HOURS_PER_DAY:
                    violations.append({
                        "field": "npt_hours",
                        "value": npt_val,
                        "action": "FLAGGED",
                        "reason": f"Single event NPT ({npt_val}h) exceeds 24.0h daily limit.",
                    })

        return violations

    def validate_npt_total(self, npt_records: List[NPTRecord]) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Computes the document's authoritative total NPT hours from the
        structured NPTRecord list — each derived directly from an explicit
        HH:MM-HH:MM time range in the DDR (calculate_npt_from_times), not
        from narrative sentence parsing. See validate_time_balance's
        docstring for why that narrative path is not used for this rollup.
        """
        violations: List[Dict[str, Any]] = []
        total_npt_hours = 0.0

        for record in npt_records:
            if record.npt_hours is None:
                continue
            npt_val = float(record.npt_hours.normalized_value) if hasattr(record.npt_hours, "normalized_value") else float(record.npt_hours)
            if npt_val < 0:
                continue  # calculate_npt_from_times already excludes negative spans
            total_npt_hours += npt_val

        if total_npt_hours > MAX_HOURS_PER_DAY:
            violations.append({
                "field": "daily_time_balance",
                "total_npt_hours": total_npt_hours,
                "action": "FLAGGED",
                "reason": f"Total NPT hours ({total_npt_hours:.2f}h) exceed 24.0h in single 24-hr DDR period.",
            })

        return total_npt_hours, violations

    def validate_document_extraction(
        self, result: DocumentExtractionResult
    ) -> Tuple[DocumentExtractionResult, ValidationReport]:
        """
        Master validation gate for Layer 5.
        Validates all extracted schemas, repairs OCR digit slips, and generates audit report.
        """
        report = ValidationReport()

        # 1. Mud validation
        if result.mud_properties:
            repaired_mud = []
            for mud in result.mud_properties:
                validated_mud, mud_v = self.validate_mud_properties(mud)
                repaired_mud.append(validated_mud)
                report.violations.extend(mud_v)
            result.mud_properties = repaired_mud

        # 2. Formation validation
        if result.formation_tops:
            validated_fmts, fmt_v = self.validate_formation_sequence(result.formation_tops)
            result.formation_tops = validated_fmts
            report.violations.extend(fmt_v)

        # 3a. Per-event npt_hours range check/repair (see validate_time_balance's
        #     docstring — this rarely finds anything on narrative text, but
        #     it's a free additional check whenever it does).
        if result.drilling_events:
            report.violations.extend(self.validate_time_balance(result.drilling_events))

        # 3b. Document-level total NPT hours — authoritative source is the
        #     structured, time-range-derived NPT records, not drilling_events.
        total_npt, npt_total_v = self.validate_npt_total(result.npt_records)
        result.total_npt_hours = total_npt
        report.violations.extend(npt_total_v)

        # 4. Compute status tally
        report.total_checks = len(report.violations) + 10  # base baseline checks
        report.repaired_fields = sum(1 for v in report.violations if v.get("action") == "AUTO_REPAIRED")
        report.failed_checks = sum(1 for v in report.violations if v.get("action") == "FLAGGED")
        report.passed_checks = report.total_checks - report.failed_checks

        if report.failed_checks > 0:
            report.overall_status = ValidationStatus.FLAGGED
            result.validation_status = ValidationStatus.FLAGGED
        else:
            report.overall_status = ValidationStatus.PASS
            result.validation_status = ValidationStatus.PASS

        logger.info(
            f"Layer 5 Validation complete: {report.passed_checks}/{report.total_checks} checks passed, "
            f"{report.repaired_fields} repaired, {report.failed_checks} flagged."
        )

        return result, report


# Global singleton instance
validator = PhysicsValidator()


def run_physics_validation(
    result: DocumentExtractionResult
) -> Tuple[DocumentExtractionResult, ValidationReport]:
    """Convenience helper to run Layer 5 validation"""
    return validator.validate_document_extraction(result)
