import logging
from typing import Any

from app.domain.omission import ScoreBreakdown

logger = logging.getLogger(__name__)


class CandidateRanker:
    """
    Computes deterministic relevance scores S_total in [0.0, 1.0].
    S_total = w1 * S_concept_evidence + w2 * S_rel_spec + w3 * S_distance + w4 * S_prov_quality

    Guarantees:
    - Citation count / popularity metrics are strictly excluded to avoid fame bias.
    - WORKED_AT relationships provide 0.0 concept relevance evidence.
    - ASSOCIATED_WITH field edges alone provide 0.0 concept evidence score.
    """

    def __init__(
        self,
        w_concept_evidence: float = 0.40,
        w_rel_spec: float = 0.25,
        w_distance: float = 0.20,
        w_prov_quality: float = 0.15,
    ) -> None:
        self.w_concept_evidence = w_concept_evidence
        self.w_rel_spec = w_rel_spec
        self.w_distance = w_distance
        self.w_prov_quality = w_prov_quality

    def calculate_score(
        self, candidate: dict[str, Any], total_doc_concepts: int
    ) -> tuple[float, ScoreBreakdown]:
        has_concept_evidence = candidate.get("has_concept_specific_evidence", False)
        rel_types = candidate.get("relationship_types", [])
        min_dist = candidate.get("min_distance", 1)
        prov_records = candidate.get("provenance_records", [])

        # 1. Concept Evidence Score
        if has_concept_evidence:
            matched_cnt = len(candidate.get("matched_concepts", []))
            doc_cnt = max(1, total_doc_concepts)
            s_concept = min(1.0, 0.70 + 0.30 * (matched_cnt / doc_cnt))
        else:
            s_concept = 0.0  # Context-only edges provide 0.0 concept evidence

        # 2. Relationship Specificity Score
        if "CONTRIBUTED_TO" in rel_types or "CORRECTIVE_CONCEPT_MATCH" in rel_types:
            s_rel = 1.0
        elif "ASSOCIATED_WITH" in rel_types:
            s_rel = 0.3
        else:
            s_rel = 0.0  # WORKED_AT provides 0.0 relationship relevance for concepts

        # 3. Distance Score
        if min_dist == 1:
            s_dist = 1.0
        elif min_dist == 2:
            s_dist = 0.50
        else:
            s_dist = 0.25

        # 4. Provenance Quality Score
        valid_prov_cnt = sum(
            1 for p in prov_records if isinstance(p, dict) and p.get("source_uri") and p.get("reference_text")
        )
        if prov_records and valid_prov_cnt == len(prov_records):
            s_prov = 1.0
        elif valid_prov_cnt > 0:
            s_prov = 0.70
        else:
            s_prov = 0.40

        total_score = round(
            self.w_concept_evidence * s_concept
            + self.w_rel_spec * s_rel
            + self.w_distance * s_dist
            + self.w_prov_quality * s_prov,
            4,
        )

        breakdown = ScoreBreakdown(
            concept_evidence_score=round(s_concept, 4),
            relationship_spec_score=round(s_rel, 4),
            distance_score=round(s_dist, 4),
            provenance_quality_score=round(s_prov, 4),
            total_score=total_score,
        )

        return total_score, breakdown
