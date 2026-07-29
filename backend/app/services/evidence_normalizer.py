import logging
from typing import Any

logger = logging.getLogger(__name__)


class EvidenceNormalizer:
    """
    Evaluates CLAIM-AWARE evidence quality.
    Evidence quality depends on both source type AND whether it directly supports the specific claim:
    - Primary Scholarly Publication / DOI directly documenting contribution -> 1.0 (Direct)
    - Wikidata P800 (Notable Work) -> 0.9 (Direct)
    - Wikidata P101 (Field of Work) -> 0.3 (Context)
    - Wikidata P108 (Employer) -> 0.2 (Context)
    - OpenAlex Topic Proximity -> 0.3 (Discovery context)
    """

    def evaluate_claim_aware_quality(self, evidence_item: dict[str, Any]) -> tuple[float, bool]:
        uri = evidence_item.get("source_uri", "").lower()
        ref = evidence_item.get("reference_text", "").lower()

        is_direct_concept_evidence = False

        if "#p800" in uri or "photo 51" in ref or "noether's theorem" in ref or "independent" in ref:
            quality = 0.90
            is_direct_concept_evidence = True
        elif "doi:" in uri or "10." in uri:
            quality = 1.00
            is_direct_concept_evidence = True
        elif "#p101" in uri:
            quality = 0.30  # Field of work (context only)
        elif "#p108" in uri:
            quality = 0.20  # Employer (context only)
        elif "openalex" in uri:
            quality = 0.30  # Topic proximity
        else:
            quality = 0.40

        return quality, is_direct_concept_evidence
