import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.openalex_service import OpenAlexService
from app.services.wikidata_service import WikidataService

logger = logging.getLogger(__name__)


class CorrectiveRetriever:
    """
    Performs external corrective retrieval when local KG coverage confidence is low.
    Excludes P101 field-only matches; strictly requires concept/discovery level matches.
    Discovered candidates are saved exclusively in analysis-time candidate layer.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self.wikidata_service = WikidataService(db)
        self.openalex_service = OpenAlexService(db)

    async def search_external_candidates(
        self, document_concepts: list[str]
    ) -> list[dict[str, Any]]:
        external_candidates: list[dict[str, Any]] = []
        seen_qids: set[str] = set()

        # Limit to top 3 longest document concepts to maintain high precision
        top_concepts = sorted(document_concepts, key=len, reverse=True)[:3]

        for concept in top_concepts:
            clean_concept = concept.strip()
            if len(clean_concept) < 4:
                continue

            try:
                # Search Wikidata for scientists linked to the specific concept/work
                search_results = await self.wikidata_service.search_entities(clean_concept, limit=3)
                for item in search_results:
                    qid = item.get("qid")
                    lbl = item.get("canonical_name", clean_concept)
                    desc = item.get("description", "").lower()

                    if (
                        qid
                        and qid not in seen_qids
                        and any(
                            term in desc
                            for term in ["scientist", "chemist", "physicist", "mathematician", "biologist", "astronomer"]
                        )
                    ):
                        seen_qids.add(qid)
                        prov = {
                            "source_uri": f"wikidata:{qid}",
                            "reference_text": f"Wikidata corrective search match for concept '{clean_concept}': {desc}.",
                            "retrieved_at": datetime.now(UTC).isoformat(),
                        }
                        external_candidates.append({
                            "person_label": lbl,
                            "wikidata_qid": qid,
                            "has_concept_specific_evidence": True,
                            "matched_concepts": [clean_concept],
                            "graph_paths": [{
                                "source": lbl,
                                "edge_type": "CORRECTIVE_CONCEPT_MATCH",
                                "target": clean_concept,
                                "provenance": prov,
                            }],
                            "provenance_records": [prov],
                            "relationship_types": ["CORRECTIVE_CONCEPT_MATCH"],
                            "min_distance": 1,
                            "is_external_discovery": True,
                        })
            except Exception as err:
                logger.warning("Corrective retrieval error for concept '%s': %s", clean_concept, err)

        return external_candidates
