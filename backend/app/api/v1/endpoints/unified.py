import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.unified import UnifiedAnalysisModel, UnifiedFindingModel
from app.db.session import get_db
from app.domain.unified import UnifiedAnalysisSummary, UnifiedFindingRead, UnifiedScoreBreakdown
from app.services.unified_engine import UnifiedEngine

router = APIRouter()


@router.post(
    "/documents/{document_id}/analyze-unified",
    response_model=UnifiedAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Trigger Unified Evidence Fusion & Analysis",
    description="Fuses Phase 5 omission detection and Phase 6 credit & framing results into a unified, evidence-strength classified document report.",
)
@router.post(
    "/unified/documents/{document_id}/analyze-unified",
    response_model=UnifiedAnalysisSummary,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def analyze_document_unified(
    document_id: uuid.UUID,
    force_reanalyze: bool = Query(False, description="If True, forces re-running unified evidence fusion."),
    reasoning_enabled: bool = Query(False, description="If True, enables Phase 9 LLM evidence reasoning."),
    explanation_enabled: bool = Query(False, description="If True, enables Phase 9 LLM grounded explanation."),
    db: AsyncSession = Depends(get_db),
) -> UnifiedAnalysisSummary:
    engine = UnifiedEngine(db)
    try:
        return await engine.analyze_document_unified(
            document_id,
            force_reanalyze=force_reanalyze,
            reasoning_enabled=reasoning_enabled,
            explanation_enabled=explanation_enabled,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified analysis failed for document {document_id}: {err}",
        ) from err


@router.get(
    "/documents/{document_id}/unified",
    response_model=UnifiedAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Unified Document Analysis Summary",
    description="Retrieves the latest unified analysis summary, neutral evidence attention score, and merged findings for a document.",
)
@router.get(
    "/unified/documents/{document_id}/unified",
    response_model=UnifiedAnalysisSummary,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_document_unified_results(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UnifiedAnalysisSummary:
    stmt = (
        select(UnifiedAnalysisModel)
        .where(UnifiedAnalysisModel.document_id == document_id)
        .order_by(UnifiedAnalysisModel.created_at.desc())
    )
    res = await db.execute(stmt)
    analysis = res.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No unified analysis found for document {document_id}. Trigger analysis first via POST.",
        )

    engine = UnifiedEngine(db)
    return await engine.get_analysis_summary(analysis.id)


@router.get(
    "/documents/{document_id}/unified/findings/{finding_id}",
    response_model=UnifiedFindingRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Individual Unified Finding Details",
    description="Retrieves detailed evidence sources, qualitative strength category, deterministic explanation, and score breakdown for a single finding.",
)
async def get_unified_finding_details(
    document_id: uuid.UUID,
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UnifiedFindingRead:
    stmt = select(UnifiedFindingModel).where(UnifiedFindingModel.id == finding_id)
    res = await db.execute(stmt)
    finding = res.scalar_one_or_none()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unified finding {finding_id} not found.",
        )

    return UnifiedFindingRead(
        id=finding.id,
        originating_phase=finding.originating_phase,
        person_id=finding.person_id,
        person_label=finding.person_label,
        wikidata_qid=finding.wikidata_qid,
        concept_label=finding.concept_label,
        finding_type=finding.finding_type,
        evidence_strength=finding.evidence_strength,
        fused_score=finding.fused_score,
        explanation_text=finding.explanation_text,
        score_breakdown=UnifiedScoreBreakdown(**finding.score_breakdown),
        document_provenance=finding.document_provenance,
        external_evidence=finding.external_evidence,
        graph_paths=finding.graph_paths,
    )
