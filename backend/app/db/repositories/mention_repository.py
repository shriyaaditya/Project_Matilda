import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mention import MentionModel
from app.domain.mention import Mention


class MentionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_document_id(
        self,
        document_id: uuid.UUID,
        mention_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[MentionModel], int]:
        stmt = select(MentionModel).where(MentionModel.document_id == document_id)
        if mention_type:
            stmt = stmt.where(MentionModel.mention_type == mention_type.upper())

        stmt = stmt.order_by(
            MentionModel.page_number,
            MentionModel.paragraph_index,
            MentionModel.sentence_index,
            MentionModel.start_char,
        ).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        mentions = list(result.scalars().all())

        count_stmt = select(MentionModel).where(MentionModel.document_id == document_id)
        if mention_type:
            count_stmt = count_stmt.where(MentionModel.mention_type == mention_type.upper())
        count_result = await self.db.execute(count_stmt)
        total = len(list(count_result.scalars().all()))

        return mentions, total

    async def count_by_document_id(self, document_id: uuid.UUID) -> int:
        stmt = select(MentionModel).where(MentionModel.document_id == document_id)
        result = await self.db.execute(stmt)
        return len(list(result.scalars().all()))

    async def delete_by_document_id(self, document_id: uuid.UUID) -> None:
        stmt = delete(MentionModel).where(MentionModel.document_id == document_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def save_mentions_batch(self, mentions_domain: list[Mention]) -> None:
        models = [
            MentionModel(
                id=m.id,
                document_id=m.document_id,
                sentence_id=m.sentence_id,
                page_number=m.page_number,
                paragraph_index=m.paragraph_index,
                sentence_index=m.sentence_index,
                mention_type=m.mention_type,
                raw_text=m.raw_text,
                normalized_text=m.normalized_text,
                start_char=m.start_char,
                end_char=m.end_char,
                confidence=m.confidence,
                extraction_method=m.extraction_method,
                model_version=m.model_version,
                created_at=m.created_at,
            )
            for m in mentions_domain
        ]
        self.db.add_all(models)
        await self.db.commit()

    @staticmethod
    def to_domain(model: MentionModel) -> Mention:
        return Mention(
            id=model.id,
            document_id=model.document_id,
            sentence_id=model.sentence_id,
            page_number=model.page_number,
            paragraph_index=model.paragraph_index,
            sentence_index=model.sentence_index,
            mention_type=model.mention_type,
            raw_text=model.raw_text,
            normalized_text=model.normalized_text,
            start_char=model.start_char,
            end_char=model.end_char,
            confidence=model.confidence,
            extraction_method=model.extraction_method,
            model_version=model.model_version,
            created_at=model.created_at,
        )
