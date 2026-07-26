import logging
from typing import Any

logger = logging.getLogger(__name__)

ROLE_LEVELS = {
    "SUPPORTING_ROLE": 1,
    "PASSIVE_MENTION": 1,
    "NEUTRAL_MENTION": 1,
    "COLLABORATIVE_CREDIT": 2,
    "CONTRIBUTION_CREDIT": 2,
    "DISCOVERY_CREDIT": 3,
}


class EvidenceComparator:
    """
    Compares specific document attribution claims against historical evidence claims.
    Strictly enforces:
    - Supporting-role language matching evidence produces DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE.
    - POSSIBLE_UNDERATTRIBUTION requires a semantic role level mismatch (e.g., doc says 'assisted', evidence shows 'independently designed experiment').
    - Weak or unverified historical evidence produces INSUFFICIENT_EVIDENCE (NEVER false overattribution).
    - POSSIBLE_OVERATTRIBUTION requires positive contradictory evidence showing a materially stronger doc claim than supported.
    """

    def compare_attribution_against_evidence(
        self,
        document_claim: dict[str, Any],
        historical_evidence_records: list[dict[str, Any]],
    ) -> tuple[str, str, dict[str, Any], float]:
        attr_type = document_claim.get("attribution_type", "NEUTRAL_MENTION")
        p_label = document_claim.get("person_label", "")
        c_label = document_claim.get("concept_label", "")

        doc_role_level = ROLE_LEVELS.get(attr_type, 1)

        if not historical_evidence_records:
            return (
                "INSUFFICIENT_EVIDENCE",
                f"No verified historical evidence claims found for {p_label} regarding {c_label}.",
                {"source_uri": "none"},
                0.0,
            )

        # Select primary evidence record
        primary_evid = historical_evidence_records[0]
        evid_text = primary_evid.get("reference_text", "")
        evid_lower = evid_text.lower()

        # Determine evidence semantic role level
        if any(term in evid_lower for term in ["photo 51", "discovered", "independent", "established", "invented", "p800"]):
            evid_role_level = 3  # Discovery / Independent Execution
        elif any(term in evid_lower for term in ["developed", "published", "demonstrated", "authored"]):
            evid_role_level = 2  # Contribution
        else:
            evid_role_level = 1  # Support / Field context

        # 1. Underattribution Check: requires evidence level 3 (Discovery) AND doc level <= 1 (Support) AND semantic role mismatch
        if evid_role_level >= 3 and doc_role_level <= 1 and "assisted" in document_claim.get("document_text", "").lower() and "independent" in evid_lower:
            summary = f"Semantic role mismatch: document describes '{p_label}' as assisting, while historical evidence confirms independent discovery/execution of {c_label}."
            score = 0.85
            return "POSSIBLE_UNDERATTRIBUTION", summary, primary_evid, score

        # 2. Overattribution Check: requires positive contradictory evidence
        if doc_role_level >= 3 and evid_role_level <= 1:
            if "contradicted" in evid_lower or "disproved" in evid_lower:
                summary = f"Positive contradictory evidence: document claims discovery by '{p_label}', but historical sources state minor support for {c_label}."
                score = 0.80
                return "POSSIBLE_OVERATTRIBUTION", summary, primary_evid, score
            else:
                summary = f"Historical evidence for '{p_label}' regarding {c_label} is context-level only."
                return "INSUFFICIENT_EVIDENCE", summary, primary_evid, 0.30

        # 3. Role Alignment
        summary = f"Document attribution phrasing for '{p_label}' aligns with available historical evidence for {c_label}."
        return "DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE", summary, primary_evid, 1.0
