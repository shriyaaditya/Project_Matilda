import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.document import (
    DocumentModel,
    PageModel,
    ParagraphModel,
    SentenceModel,
)
from app.domain.document import BoundingBox, DocumentHeader, DocumentStructured, Page, Paragraph, Sentence


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_sha256(self, sha256_hash: str) -> DocumentModel | None:
        stmt = select(DocumentModel).where(DocumentModel.sha256_hash == sha256_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, document_id: uuid.UUID) -> DocumentModel | None:
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_structured_by_id(self, document_id: uuid.UUID) -> DocumentModel | None:
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.id == document_id)
            .options(
                selectinload(DocumentModel.pages)
                .selectinload(PageModel.paragraphs)
                .selectinload(ParagraphModel.sentences)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(self, skip: int = 0, limit: int = 20) -> tuple[list[DocumentModel], int]:
        stmt = select(DocumentModel).order_by(DocumentModel.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        docs = list(result.scalars().all())

        count_stmt = select(DocumentModel)
        count_result = await self.db.execute(count_stmt)
        total = len(list(count_result.scalars().all()))

        return docs, total

    async def save_structured_document(
        self,
        filename: str,
        file_size_bytes: int,
        sha256_hash: str,
        file_path: str,
        page_count: int,
        status: str,
        pages: list[Page],
        error_message: str | None = None,
    ) -> DocumentModel:
        doc_model = DocumentModel(
            filename=filename,
            file_size_bytes=file_size_bytes,
            sha256_hash=sha256_hash,
            file_path=file_path,
            page_count=page_count,
            status=status,
            error_message=error_message,
        )
        self.db.add(doc_model)
        await self.db.flush()

        for page in pages:
            page_model = PageModel(
                document_id=doc_model.id,
                page_number=page.page_number,
                has_extractable_text=page.has_extractable_text,
                raw_text=page.raw_text,
            )
            self.db.add(page_model)
            await self.db.flush()

            for para in page.paragraphs:
                para_model = ParagraphModel(
                    page_id=page_model.id,
                    document_id=doc_model.id,
                    paragraph_index=para.paragraph_index,
                    text=para.text,
                    bbox_x0=para.bbox.x0 if para.bbox else None,
                    bbox_y0=para.bbox.y0 if para.bbox else None,
                    bbox_x1=para.bbox.x1 if para.bbox else None,
                    bbox_y1=para.bbox.y1 if para.bbox else None,
                )
                self.db.add(para_model)
                await self.db.flush()

                for s in para.sentences:
                    s_model = SentenceModel(
                        paragraph_id=para_model.id,
                        document_id=doc_model.id,
                        page_number=page.page_number,
                        paragraph_index=para.paragraph_index,
                        sentence_index=s.sentence_index,
                        global_sentence_index=s.global_sentence_index,
                        text=s.text,
                        char_count=s.char_count,
                    )
                    self.db.add(s_model)

        await self.db.commit()
        await self.db.refresh(doc_model)
        return doc_model

    @staticmethod
    def to_header(model: DocumentModel, is_duplicate: bool = False) -> DocumentHeader:
        return DocumentHeader(
            id=model.id,
            filename=model.filename,
            file_size_bytes=model.file_size_bytes,
            sha256_hash=model.sha256_hash,
            file_path=model.file_path,
            page_count=model.page_count,
            status=model.status,
            is_duplicate=is_duplicate,
            error_message=model.error_message,
            created_at=model.created_at,
        )

    @staticmethod
    def to_structured(model: DocumentModel, is_duplicate: bool = False) -> DocumentStructured:
        pages_domain: list[Page] = []
        for p in model.pages:
            paragraphs_domain: list[Paragraph] = []
            for para in p.paragraphs:
                sentences_domain: list[Sentence] = [
                    Sentence(
                        id=s.id,
                        sentence_index=s.sentence_index,
                        global_sentence_index=s.global_sentence_index,
                        text=s.text,
                        char_count=s.char_count,
                    )
                    for s in para.sentences
                ]

                bbox_obj = None
                if (
                    para.bbox_x0 is not None
                    and para.bbox_y0 is not None
                    and para.bbox_x1 is not None
                    and para.bbox_y1 is not None
                ):
                    bbox_obj = BoundingBox(
                        x0=para.bbox_x0,
                        y0=para.bbox_y0,
                        x1=para.bbox_x1,
                        y1=para.bbox_y1,
                    )

                paragraphs_domain.append(
                    Paragraph(
                        id=para.id,
                        paragraph_index=para.paragraph_index,
                        text=para.text,
                        bbox=bbox_obj,
                        sentences=sentences_domain,
                    )
                )

            pages_domain.append(
                Page(
                    id=p.id,
                    page_number=p.page_number,
                    has_extractable_text=p.has_extractable_text,
                    raw_text=p.raw_text,
                    paragraphs=paragraphs_domain,
                )
            )

        return DocumentStructured(
            id=model.id,
            filename=model.filename,
            file_size_bytes=model.file_size_bytes,
            sha256_hash=model.sha256_hash,
            file_path=model.file_path,
            page_count=model.page_count,
            status=model.status,
            is_duplicate=is_duplicate,
            error_message=model.error_message,
            created_at=model.created_at,
            pages=pages_domain,
        )
