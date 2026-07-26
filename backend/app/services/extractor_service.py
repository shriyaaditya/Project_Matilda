import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import SentenceModel
from app.db.repositories.mention_repository import MentionRepository
from app.domain.mention import ExtractionSummary, Mention
from app.services.concept_extractor import ConceptExtractor
from app.services.person_extractor import PersonExtractor


class ExtractorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MentionRepository(db)
        self.person_extractor = PersonExtractor()
        self.concept_extractor = ConceptExtractor()

    async def extract_and_store_mentions(
        self, document_id: uuid.UUID, force_reextract: bool = False
    ) -> ExtractionSummary:
        # 1. Idempotency Check: if mentions exist and force_reextract=False, return existing counts
        existing_count = await self.repo.count_by_document_id(document_id)
        if existing_count > 0 and not force_reextract:
            persons, _ = await self.repo.get_by_document_id(document_id, mention_type="PERSON", limit=10000)
            concepts, _ = await self.repo.get_by_document_id(document_id, mention_type="CONCEPT", limit=10000)
            return ExtractionSummary(
                document_id=document_id,
                total_sentences_processed=0,
                person_mentions_count=len(persons),
                concept_mentions_count=len(concepts),
                is_already_extracted=True,
            )

        if force_reextract and existing_count > 0:
            await self.repo.delete_by_document_id(document_id)

        # 2. Fetch all sentences belonging to document
        stmt = (
            select(SentenceModel)
            .where(SentenceModel.document_id == document_id)
            .order_by(SentenceModel.page_number, SentenceModel.paragraph_index, SentenceModel.sentence_index)
        )
        result = await self.db.execute(stmt)
        sentences_models = list(result.scalars().all())

        mentions_to_save: list[Mention] = []
        person_count = 0
        concept_count = 0

        # 3. Extract mentions for each sentence
        for s_model in sentences_models:
            sentence_text = s_model.text

            # 3a. Extract PERSON mentions
            person_raw = self.person_extractor.extract_person_mentions(sentence_text)
            person_spans: list[tuple[int, int]] = []

            for raw_text, norm_text, start_c, end_c, conf in person_raw:
                person_spans.append((start_c, end_c))
                person_count += 1
                mentions_to_save.append(
                    Mention(
                        document_id=document_id,
                        sentence_id=s_model.id,
                        page_number=s_model.page_number,
                        paragraph_index=s_model.paragraph_index,
                        sentence_index=s_model.sentence_index,
                        mention_type="PERSON",
                        raw_text=raw_text,
                        normalized_text=norm_text,
                        start_char=start_c,
                        end_char=end_c,
                        confidence=conf,  # NULL per Rule 1
                        extraction_method="SPACY_NER",
                        model_version=self.person_extractor.model_name,
                    )
                )

            # 3b. Extract CONCEPT mentions (passing person_spans to prevent PERSON/CONCEPT span collisions)
            concept_raw = self.concept_extractor.extract_concept_mentions(
                sentence_text, person_spans=person_spans
            )

            for raw_text, norm_text, start_c, end_c, conf in concept_raw:
                concept_count += 1
                mentions_to_save.append(
                    Mention(
                        document_id=document_id,
                        sentence_id=s_model.id,
                        page_number=s_model.page_number,
                        paragraph_index=s_model.paragraph_index,
                        sentence_index=s_model.sentence_index,
                        mention_type="CONCEPT",
                        raw_text=raw_text,
                        normalized_text=norm_text,
                        start_char=start_c,
                        end_char=end_c,
                        confidence=conf,  # NULL per Rule 1
                        extraction_method="NOUN_CHUNK_FILTER",
                        model_version=self.concept_extractor.model_name,
                    )
                )

        # 4. Save mentions batch to database
        if mentions_to_save:
            await self.repo.save_mentions_batch(mentions_to_save)

        return ExtractionSummary(
            document_id=document_id,
            total_sentences_processed=len(sentences_models),
            person_mentions_count=person_count,
            concept_mentions_count=concept_count,
            is_already_extracted=False,
        )

    async def get_document_mentions(
        self,
        document_id: uuid.UUID,
        mention_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Mention], int]:
        models, total = await self.repo.get_by_document_id(
            document_id=document_id, mention_type=mention_type, skip=skip, limit=limit
        )
        domain_mentions = [self.repo.to_domain(m) for m in models]
        return domain_mentions, total
