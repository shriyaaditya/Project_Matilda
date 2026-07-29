import logging

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """
    Generates deterministic template-based natural language explanations.
    Guarantees:
    - Prose is 100% reconstructable from persisted evidence.
    - Accusatory or subjective language is strictly prohibited.
    """

    @staticmethod
    def generate_explanation(
        finding_type: str,
        person_label: str,
        concept_label: str,
        evidence_strength: str,
        role_summary: str = "",
    ) -> str:
        p_name = person_label.strip()
        c_name = concept_label.strip()

        if finding_type == "POTENTIAL_OMISSION":
            return (
                f"{p_name} was not identified among the document's resolved people. "
                f"Matilda found {evidence_strength.lower()} source-backed historical evidence connecting her to "
                f"{c_name}, which is discussed in the document."
            )
        elif finding_type == "POSSIBLE_UNDERATTRIBUTION":
            return (
                f"Semantic role mismatch: document describes {p_name} as assisting with {c_name}, "
                f"while historical evidence confirms independent discovery or primary execution. ({evidence_strength} evidence)"
            )
        elif finding_type == "POSSIBLE_OVERATTRIBUTION":
            return (
                f"Document assigns a primary attribution role to {p_name} for {c_name}, "
                f"which differs from available historical evidence. ({evidence_strength} evidence)"
            )
        elif finding_type == "CREDIT_ALIGNS":
            return (
                f"Document attribution phrasing for {p_name} regarding {c_name} "
                f"aligns with available historical evidence. ({evidence_strength} evidence)"
            )
        else:
            return (
                f"Historical evidence regarding {p_name} and {c_name} is context-level or incomplete. ({evidence_strength} evidence)"
            )
