import hashlib
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.document_repository import DocumentRepository
from app.domain.document import DocumentHeader, DocumentStructured
from app.services.pdf_parser import PDFParser
from app.services.pdf_validator import PDFValidator


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = DocumentRepository(db)
        self.validator = PDFValidator()
        self.parser = PDFParser()

    async def process_and_store_pdf(
        self, filename: str, pdf_bytes: bytes, content_type: str | None = None
    ) -> tuple[DocumentHeader, bool]:
        file_size = len(pdf_bytes)

        # 1. Validate file metadata and bytes
        self.validator.validate_file_metadata(filename, file_size, content_type)
        doc = self.validator.validate_pdf_bytes(pdf_bytes)

        # 2. SHA-256 Deduplication check
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
        existing_doc = await self.repo.get_by_sha256(sha256_hash)
        if existing_doc:
            # Duplicate upload: return existing record without writing duplicate file to disk
            return self.repo.to_header(existing_doc, is_duplicate=True), True

        # 3. Persist physical PDF file to local upload directory
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        physical_file_path = os.path.join(settings.UPLOAD_DIR, f"{sha256_hash}.pdf")
        if not os.path.exists(physical_file_path):
            with open(physical_file_path, "wb") as f:
                f.write(pdf_bytes)

        # 4. Parse PDF structure via PyMuPDF + pysbd
        pages, status = self.parser.parse_document(doc)
        page_count = doc.page_count

        # 5. Save to PostgreSQL database
        doc_model = await self.repo.save_structured_document(
            filename=filename,
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            file_path=physical_file_path,
            page_count=page_count,
            status=status,
            pages=pages,
        )

        return self.repo.to_header(doc_model, is_duplicate=False), False

    async def get_document_header(self, document_id: uuid.UUID) -> DocumentHeader | None:
        doc = await self.repo.get_by_id(document_id)
        if not doc:
            return None
        return self.repo.to_header(doc)

    async def get_document_structured(self, document_id: uuid.UUID) -> DocumentStructured | None:
        doc = await self.repo.get_structured_by_id(document_id)
        if not doc:
            return None
        return self.repo.to_structured(doc)

    async def list_documents(self, skip: int = 0, limit: int = 20) -> tuple[list[DocumentHeader], int]:
        docs, total = await self.repo.list_documents(skip, limit)
        headers = [self.repo.to_header(d) for d in docs]
        return headers, total
