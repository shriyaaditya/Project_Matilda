from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.person import CanonicalPersonModel
from app.services.wikidata_service import WikidataService


class CandidateGenerator:
    def __init__(self, db: AsyncSession, wikidata_service: WikidataService) -> None:
        self.db = db
        self.wikidata = wikidata_service

    async def get_candidates(self, mention_raw_text: str, limit: int = 5) -> list[dict[str, Any]]:
        clean_text = mention_raw_text.strip().lower()
        candidates_map: dict[str, dict[str, Any]] = {}

        # 1. Local Database Candidates (existing CanonicalPersonModel records)
        stmt = (
            select(CanonicalPersonModel)
            .where(
                CanonicalPersonModel.canonical_name.ilike(f"%{clean_text}%")
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        local_persons = list(result.scalars().all())

        for p in local_persons:
            key = p.wikidata_qid if p.wikidata_qid else str(p.id)
            candidates_map[key] = {
                "id": str(p.id),
                "qid": p.wikidata_qid,
                "canonical_name": p.canonical_name,
                "description": p.description or "",
                "aliases": p.aliases or [],
                "birth_year": p.birth_year,
                "death_year": p.death_year,
                "occupations": p.occupations or [],
                "source": "LOCAL_DB",
            }

        # 2. External Wikidata Candidates
        wikidata_candidates = await self.wikidata.search_entities(mention_raw_text, limit=limit)
        for w_cand in wikidata_candidates:
            qid = w_cand.get("qid")
            if qid and qid not in candidates_map:
                candidates_map[qid] = {
                    "id": None,
                    "qid": qid,
                    "canonical_name": w_cand.get("canonical_name", mention_raw_text),
                    "description": w_cand.get("description", ""),
                    "aliases": w_cand.get("aliases", []),
                    "birth_year": w_cand.get("birth_year"),
                    "death_year": w_cand.get("death_year"),
                    "occupations": w_cand.get("occupations", []),
                    "source": "WIKIDATA",
                }

        return list(candidates_map.values())[:limit]
