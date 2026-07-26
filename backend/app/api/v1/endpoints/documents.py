import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.document import DocumentHeader, DocumentStructured
from app.services.document_service import DocumentService

router = APIRouter()


@router.post(
    "/documents/upload",
    response_model=DocumentHeader,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Parse PDF Document",
    description="Validates PDF file, computes SHA-256 hash for deduplication, parses page/paragraph/sentence structure using PyMuPDF, and persists to database.",
)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentHeader:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    pdf_bytes = await file.read()
    service = DocumentService(db)

    header, is_duplicate = await service.process_and_store_pdf(
        filename=file.filename,
        pdf_bytes=pdf_bytes,
        content_type=file.content_type,
    )

    if is_duplicate:
        response.status_code = status.HTTP_200_OK

    return header


@router.get(
    "/documents",
    response_model=list[DocumentHeader],
    summary="List Document Headers",
    description="Returns paginated list of uploaded document headers.",
)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentHeader]:
    service = DocumentService(db)
    headers, _ = await service.list_documents(skip=skip, limit=limit)
    return headers


@router.get(
    "/documents/{document_id}",
    response_model=DocumentHeader,
    summary="Get Document Header",
    description="Returns metadata header for a single uploaded document.",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentHeader:
    service = DocumentService(db)
    header = await service.get_document_header(document_id)
    if not header:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    return header


@router.get(
    "/documents/{document_id}/structure",
    response_model=DocumentStructured,
    summary="Get Structured Document Representation",
    description="Returns complete nested document hierarchy (Document -> Page -> Paragraph -> Sentence) with spatial bounding box provenance.",
)
async def get_document_structure(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentStructured:
    service = DocumentService(db)
    structured = await service.get_document_structured(document_id)
    if not structured:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    return structured
