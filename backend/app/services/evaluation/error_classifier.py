import logging
from typing import Any

logger = logging.getLogger(__name__)

ERROR_CATEGORIES = [
    "PDF_EXTRACTION_ERROR",
    "ENTITY_RESOLUTION_ERROR",
    "CONCEPT_EXTRACTION_ERROR",
    "KG_COVERAGE_ERROR",
    "CORRECTIVE_RETRIEVAL_ERROR",
    "EVIDENCE_MATCH_ERROR",
    "RANKING_ERROR",
    "OMISSION_CLASSIFICATION_ERROR",
    "ATTRIBUTION_EXTRACTION_ERROR",
    "CREDIT_COMPARISON_ERROR",
    "EVIDENCE_FUSION_ERROR",
]


class ErrorClassifier:
    """
    Classifies benchmark failure cases into machine-readable pipeline stages.
    """

    @staticmethod
    def classify_failure(
        expected_type: str,
        predicted_findings: list[dict[str, Any]],
        resolved_people: list[str],
    ) -> str:
        if expected_type == "AMBIGUOUS_ENTITY_CASE" and resolved_people:
            return "ENTITY_RESOLUTION_ERROR"

        if expected_type == "OMISSION_POSITIVE":
            if not predicted_findings:
                return "KG_COVERAGE_ERROR"
            has_omission = any(f.get("finding_type") == "POTENTIAL_OMISSION" for f in predicted_findings)
            if not has_omission:
                return "OMISSION_CLASSIFICATION_ERROR"

        if expected_type in ["UNDERATTRIBUTION_CASE", "CREDIT_ALIGNMENT"]:
            if not predicted_findings:
                return "ATTRIBUTION_EXTRACTION_ERROR"
            has_credit = any("CREDIT" in f.get("finding_type", "") or "ATTRIBUTION" in f.get("finding_type", "") for f in predicted_findings)
            if not has_credit:
                return "CREDIT_COMPARISON_ERROR"

        return "EVIDENCE_MATCH_ERROR"
