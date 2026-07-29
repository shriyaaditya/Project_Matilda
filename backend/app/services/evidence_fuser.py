import logging
from typing import Any

from app.domain.unified import UnifiedScoreBreakdown
from app.services.evidence_normalizer import EvidenceNormalizer
from app.services.source_deduplicator import SourceDeduplicator

logger = logging.getLogger(__name__)


class EvidenceFuser:
    """
    Computes bounded evidence fusion scores without artificial strength amplification.
    Rule: At least one qualifying concept-specific evidence item is REQUIRED before a finding
    can receive MODERATE or STRONG evidence strength. Without direct concept evidence, strength is capped at WEAK.
    """

    def __init__(self) -> None:
        self.deduplicator = SourceDeduplicator()
        self.normalizer = EvidenceNormalizer()

    def fuse_evidence(
        self,
        raw_evidence_sources: list[dict[str, Any]],
        base_phase_score: float,
    ) -> tuple[float, str, UnifiedScoreBreakdown]:
        # 1. Deduplicate Sources
        unique_sources, dedup_log = self.deduplicator.deduplicate_evidence_sources(raw_evidence_sources)

        # 2. Evaluate Claim-Aware Quality
        claim_scores: list[float] = []
        has_direct_concept_evid = False

        for src in unique_sources:
            score, is_direct = self.normalizer.evaluate_claim_aware_quality(src)
            claim_scores.append(score)
            if is_direct:
                has_direct_concept_evid = True

        max_claim_score = max(claim_scores) if claim_scores else base_phase_score
        N_unique = len(unique_sources)
        corrob_bonus = round(min(0.20, 0.10 * max(0, N_unique - 1)), 4)

        raw_fused = max_claim_score + corrob_bonus

        # Hard cap rule: if no direct concept evidence, cap fused score at 0.50 (WEAK)
        fused_score = min(0.50, raw_fused) if not has_direct_concept_evid else min(1.0, raw_fused)
        fused_score = round(fused_score, 4)

        # 3. Categorize Qualitative Evidence Strength
        if fused_score >= 0.75 and has_direct_concept_evid:
            strength_category = "STRONG"
        elif fused_score >= 0.55 and has_direct_concept_evid:
            strength_category = "MODERATE"
        elif fused_score >= 0.35:
            strength_category = "WEAK"
        else:
            strength_category = "INSUFFICIENT"

        breakdown = UnifiedScoreBreakdown(
            max_claim_score=round(max_claim_score, 4),
            corroboration_bonus=corrob_bonus,
            deduplicated_source_count=N_unique,
            has_direct_concept_evidence=has_direct_concept_evid,
            fused_score=fused_score,
            deduplication_log=dedup_log,
        )

        return fused_score, strength_category, breakdown
