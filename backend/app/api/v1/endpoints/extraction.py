import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.mention import ExtractionSummary, Mention
from app.services.extractor_service import ExtractorService

router = APIRouter()


@router.post(
    "/documents/{document_id}/extract",
    response_model=ExtractionSummary,
    status_code=status.HTTP_200_OK,
    summary="Extract Person & Concept Mentions",
    description="Processes document sentences through spaCy NER (PERSON) and dynamic noun-chunk filtering (CONCEPT). Saves provenance-linked mentions to PostgreSQL.",
)
async def extract_document_mentions(
    document_id: uuid.UUID,
    force_reextract: bool = Query(False, description="If True, re-runs extraction and overwrites existing mentions."),
    db: AsyncSession = Depends(get_db),
) -> ExtractionSummary:
    service = ExtractorService(db)
    try:
        summary = await service.extract_and_store_mentions(
            document_id=document_id, force_reextract=force_reextract
        )
        return summary
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed for document {document_id}: {str(err)}",
        ) from err


@router.get(
    "/documents/{document_id}/mentions",
    response_model=list[Mention],
    summary="Get Extracted Mentions",
    description="Returns paginated list of extracted mentions for a document, with optional type filter ('PERSON' or 'CONCEPT').",
)
async def get_document_mentions(
    document_id: uuid.UUID,
    type: str | None = Query(None, description="Filter by mention type: PERSON or CONCEPT"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[Mention]:
    service = ExtractorService(db)
    mentions, _ = await service.get_document_mentions(
        document_id=document_id, mention_type=type, skip=skip, limit=limit
    )
    return mentions
