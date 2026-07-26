import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import SentenceModel
from app.db.models.mention import MentionModel
from app.db.repositories.person_repository import PersonRepository
from app.domain.resolution import CanonicalPerson, EntityResolution, ResolutionSummary
from app.services.candidate_generator import CandidateGenerator
from app.services.resolution_matcher import ResolutionMatcher
from app.services.wikidata_service import WikidataService


class ResolutionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PersonRepository(db)
        self.wikidata_service = WikidataService(db)
        self.candidate_generator = CandidateGenerator(db, self.wikidata_service)
        self.matcher = ResolutionMatcher()

    async def resolve_document_entities(
        self, document_id: uuid.UUID, force_reprocess: bool = False
    ) -> ResolutionSummary:
        # 1. Idempotency check: if resolutions exist and force_reprocess=False, return summary
        existing_count = await self.repo.count_resolutions_by_document(document_id)
        if existing_count > 0 and not force_reprocess:
            resolved, _ = await self.repo.get_resolutions_by_document(document_id, status="RESOLVED", limit=10000)
            ambiguous, _ = await self.repo.get_resolutions_by_document(document_id, status="AMBIGUOUS", limit=10000)
            unresolved, _ = await self.repo.get_resolutions_by_document(document_id, status="UNRESOLVED", limit=10000)
            return ResolutionSummary(
                document_id=document_id,
                total_person_mentions=existing_count,
                resolved_count=len(resolved),
                ambiguous_count=len(ambiguous),
                unresolved_count=len(unresolved),
                is_already_resolved=True,
            )

        if force_reprocess and existing_count > 0:
            await self.repo.delete_resolutions_by_document(document_id)

        # 2. Fetch all PERSON mentions for document
        person_mentions_stmt = (
            select(MentionModel)
            .where(MentionModel.document_id == document_id, MentionModel.mention_type == "PERSON")
            .order_by(MentionModel.page_number, MentionModel.paragraph_index, MentionModel.sentence_index)
        )
        res = await self.db.execute(person_mentions_stmt)
        person_mentions = list(res.scalars().all())

        resolutions_to_save: list[EntityResolution] = []
        resolved_cnt = 0
        ambiguous_cnt = 0
        unresolved_cnt = 0

        # 3. Process each PERSON mention
        for mention in person_mentions:
            # Fetch nearby CONCEPT mentions from same page and surrounding paragraph window
            concepts_stmt = select(MentionModel.raw_text).where(
                MentionModel.document_id == document_id,
                MentionModel.mention_type == "CONCEPT",
                MentionModel.page_number == mention.page_number,
                MentionModel.paragraph_index >= mention.paragraph_index - 1,
                MentionModel.paragraph_index <= mention.paragraph_index + 1,
            )
            c_res = await self.db.execute(concepts_stmt)
            nearby_concepts = list(c_res.scalars().all())

            # Fetch parent & adjacent sentence text for temporal date extraction
            sentence_stmt = select(SentenceModel.text).where(
                SentenceModel.document_id == document_id,
                SentenceModel.page_number == mention.page_number,
                SentenceModel.paragraph_index >= mention.paragraph_index - 1,
                SentenceModel.paragraph_index <= mention.paragraph_index + 1,
            )
            s_res = await self.db.execute(sentence_stmt)
            sentence_texts = list(s_res.scalars().all())
            nearby_text = " ".join(sentence_texts)

            # Generate candidate identities (Local DB + Wikidata API)
            candidates = await self.candidate_generator.get_candidates(mention.raw_text, limit=5)

            # Evaluate multi-signal resolution score
            status, score, matched_cand, evidence = self.matcher.evaluate_candidates(
                mention_raw=mention.raw_text,
                nearby_concepts=nearby_concepts,
                nearby_text=nearby_text,
                candidates=candidates,
            )

            person_id = None
            matched_qid = None

            if status == "RESOLVED" and matched_cand:
                matched_qid = matched_cand.get("qid")
                # Save or get CanonicalPerson record in database
                person_model = await self.repo.save_canonical_person(
                    canonical_name=matched_cand.get("canonical_name", mention.raw_text),
                    wikidata_qid=matched_qid,
                    birth_year=matched_cand.get("birth_year"),
                    death_year=matched_cand.get("death_year"),
                    occupations=matched_cand.get("occupations", []),
                    aliases=matched_cand.get("aliases", []),
                    description=matched_cand.get("description"),
                )
                person_id = person_model.id
                resolved_cnt += 1
            elif status == "AMBIGUOUS":
                ambiguous_cnt += 1
            else:
                unresolved_cnt += 1

            resolutions_to_save.append(
                EntityResolution(
                    mention_id=mention.id,
                    document_id=document_id,
                    person_id=person_id,
                    status=status,
                    resolution_score=score,
                    matched_qid=matched_qid,
                    evidence=evidence,
                )
            )

        # 4. Save resolutions batch to database
        if resolutions_to_save:
            await self.repo.save_resolutions_batch(resolutions_to_save)

        return ResolutionSummary(
            document_id=document_id,
            total_person_mentions=len(person_mentions),
            resolved_count=resolved_cnt,
            ambiguous_count=ambiguous_cnt,
            unresolved_count=unresolved_cnt,
            is_already_resolved=False,
        )

    async def get_document_people(
        self, document_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[CanonicalPerson], int]:
        models, total = await self.repo.get_people_by_document(document_id, skip=skip, limit=limit)
        return [self.repo.to_person_domain(p) for p in models], total

    async def get_document_resolutions(
        self, document_id: uuid.UUID, status: str | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[list[EntityResolution], int]:
        models, total = await self.repo.get_resolutions_by_document(
            document_id=document_id, status=status, skip=skip, limit=limit
        )
        return [self.repo.to_resolution_domain(r) for r in models], total

    async def get_resolution_explanation(self, resolution_id: uuid.UUID) -> EntityResolution | None:
        model = await self.repo.get_resolution_by_id(resolution_id)
        if not model:
            return None
        return self.repo.to_resolution_domain(model)
