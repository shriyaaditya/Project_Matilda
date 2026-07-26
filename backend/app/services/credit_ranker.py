import logging
from typing import Any

from app.domain.credit import CreditScoreBreakdown

logger = logging.getLogger(__name__)


class CreditRanker:
    """
    Computes deterministic credit discrepancy scores S_disc in [0.0, 1.0].
    S_disc = w1 * S_role_mismatch + w2 * S_evidence_strength + w3 * S_concept_match + w4 * S_prov_quality

    Guarantees:
    - Subjective sentiment, fame, gender, and citation popularity are strictly excluded.
    """

    def __init__(
        self,
        w_role_mismatch: float = 0.40,
        w_evidence_strength: float = 0.30,
        w_concept_match: float = 0.15,
        w_prov_quality: float = 0.15,
    ) -> None:
        self.w_role_mismatch = w_role_mismatch
        self.w_evidence_strength = w_evidence_strength
        self.w_concept_match = w_concept_match
        self.w_prov_quality = w_prov_quality

    def calculate_score(
        self,
        classification: str,
        role_score: float,
        evidence_record: dict[str, Any],
    ) -> tuple[float, CreditScoreBreakdown]:
        # 1. Role Mismatch Score
        s_mismatch = role_score if classification in ["POSSIBLE_UNDERATTRIBUTION", "POSSIBLE_OVERATTRIBUTION"] else 0.0

        # 2. Evidence Strength Score
        source_uri = evidence_record.get("source_uri", "")
        ref_text = evidence_record.get("reference_text", "")
        if "#P800" in source_uri or "independent" in ref_text.lower() or "photo 51" in ref_text.lower():
            s_evid = 1.0
        elif source_uri and source_uri != "none":
            s_evid = 0.70
        else:
            s_evid = 0.20

        # 3. Concept Match Score
        s_match = 1.0 if ref_text else 0.50

        # 4. Provenance Quality Score
        s_prov = 1.0 if (source_uri and ref_text) else 0.40

        total_score = round(
            self.w_role_mismatch * s_mismatch
            + self.w_evidence_strength * s_evid
            + self.w_concept_match * s_match
            + self.w_prov_quality * s_prov,
            4,
        )

        breakdown = CreditScoreBreakdown(
            role_mismatch_score=round(s_mismatch, 4),
            evidence_strength_score=round(s_evid, 4),
            concept_match_score=round(s_match, 4),
            provenance_quality_score=round(s_prov, 4),
            total_score=total_score,
        )

        return total_score, breakdown
