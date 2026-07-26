import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit import CreditAnalysisModel, CreditAttributionModel
from app.db.session import get_db
from app.domain.credit import CreditAnalysisSummary, CreditAttributionRead, CreditScoreBreakdown
from app.services.credit_engine import CreditEngine

router = APIRouter()


@router.post(
    "/documents/{document_id}/analyze-credit",
    response_model=CreditAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Trigger Credit & Framing Analysis",
    description="Processes document attributions and frames person mentions against evidence-backed historical contribution records to detect credit discrepancy candidates.",
)
async def analyze_document_credit(
    document_id: uuid.UUID,
    force_reanalyze: bool = Query(False, description="If True, forces re-running credit extraction and evidence comparison."),
    db: AsyncSession = Depends(get_db),
) -> CreditAnalysisSummary:
    engine = CreditEngine(db)
    try:
        return await engine.analyze_document_credit(document_id, force_reanalyze=force_reanalyze)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Credit analysis failed for document {document_id}: {err}",
        ) from err


@router.get(
    "/documents/{document_id}/credit",
    response_model=CreditAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Document Credit Analysis Results",
    description="Retrieves the latest credit and framing analysis summary and attribution records for a document.",
)
async def get_document_credit_results(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CreditAnalysisSummary:
    stmt = (
        select(CreditAnalysisModel)
        .where(CreditAnalysisModel.document_id == document_id)
        .order_by(CreditAnalysisModel.created_at.desc())
    )
    res = await db.execute(stmt)
    analysis = res.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credit analysis found for document {document_id}. Trigger analysis first via POST.",
        )

    engine = CreditEngine(db)
    return await engine.get_analysis_summary(analysis.id)


@router.get(
    "/documents/{document_id}/credit/attributions/{attribution_id}",
    response_model=CreditAttributionRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Individual Attribution Details",
    description="Retrieves document text, evidence text, role comparison summary, and score breakdown for a single extracted attribution record.",
)
async def get_credit_attribution_details(
    document_id: uuid.UUID,
    attribution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CreditAttributionRead:
    stmt = select(CreditAttributionModel).where(CreditAttributionModel.id == attribution_id)
    res = await db.execute(stmt)
    attribution = res.scalar_one_or_none()
    if not attribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credit attribution record {attribution_id} not found.",
        )

    return CreditAttributionRead(
        id=attribution.id,
        person_id=attribution.person_id,
        person_label=attribution.person_label,
        concept_label=attribution.concept_label,
        attribution_type=attribution.attribution_type,
        grammatical_role=attribution.grammatical_role,
        attribution_verb=attribution.attribution_verb,
        document_text=attribution.document_text,
        evidence_text=attribution.evidence_text,
        role_comparison_summary=attribution.role_comparison_summary,
        discrepancy_classification=attribution.discrepancy_classification,
        discrepancy_score=attribution.discrepancy_score,
        score_breakdown=CreditScoreBreakdown(**attribution.score_breakdown),
        evidence_sources=attribution.evidence_sources,
    )
