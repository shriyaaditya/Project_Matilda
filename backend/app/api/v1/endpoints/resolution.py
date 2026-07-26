import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.resolution import CanonicalPerson, EntityResolution, ResolutionSummary
from app.services.resolution_service import ResolutionService

router = APIRouter()


@router.post(
    "/documents/{document_id}/resolve",
    response_model=ResolutionSummary,
    status_code=status.HTTP_200_OK,
    summary="Resolve Document Entities",
    description="Resolves surface PERSON mentions into canonical historical identities using multi-signal graded context scoring.",
)
async def resolve_document_entities(
    document_id: uuid.UUID,
    force_reprocess: bool = Query(False, description="If True, re-runs resolution and overwrites existing records."),
    db: AsyncSession = Depends(get_db),
) -> ResolutionSummary:
    service = ResolutionService(db)
    try:
        summary = await service.resolve_document_entities(
            document_id=document_id, force_reprocess=force_reprocess
        )
        return summary
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity resolution failed for document {document_id}: {str(err)}",
        ) from err


@router.get(
    "/documents/{document_id}/people",
    response_model=list[CanonicalPerson],
    summary="Get Resolved Canonical People",
    description="Returns distinct canonical historical people resolved for a document.",
)
async def get_document_people(
    document_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[CanonicalPerson]:
    service = ResolutionService(db)
    people, _ = await service.get_document_people(document_id=document_id, skip=skip, limit=limit)
    return people


@router.get(
    "/documents/{document_id}/resolutions",
    response_model=list[EntityResolution],
    summary="Get Entity Resolution Records",
    description="Returns paginated resolution records with evidence audit breakdowns. Supports filtering by status ('RESOLVED', 'AMBIGUOUS', 'UNRESOLVED').",
)
async def get_document_resolutions(
    document_id: uuid.UUID,
    status: str | None = Query(None, description="Filter by status: RESOLVED, AMBIGUOUS, UNRESOLVED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[EntityResolution]:
    service = ResolutionService(db)
    resolutions, _ = await service.get_document_resolutions(
        document_id=document_id, status=status, skip=skip, limit=limit
    )
    return resolutions


@router.get(
    "/resolutions/{resolution_id}/explanation",
    response_model=EntityResolution,
    summary="Get Resolution Explanation Audit Trail",
    description="Returns full resolution record with evidence breakdown and competing candidate scores.",
)
async def get_resolution_explanation(
    resolution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EntityResolution:
    service = ResolutionService(db)
    resolution = await service.get_resolution_explanation(resolution_id)
    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resolution record {resolution_id} not found",
        )
    return resolution
