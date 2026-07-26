import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.omission import OmissionAnalysisModel, OmissionCandidateModel
from app.db.session import get_db
from app.domain.omission import OmissionAnalysisSummary, OmissionCandidateRead, ScoreBreakdown
from app.services.omission_engine import OmissionEngine

router = APIRouter()


@router.post(
    "/documents/{document_id}/analyze-omissions",
    response_model=OmissionAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Trigger Omission Analysis",
    description="Processes document concepts and resolved person mentions through historical knowledge graph traversal and corrective retrieval to surface potential omissions with audit provenance.",
)
async def analyze_document_omissions(
    document_id: uuid.UUID,
    force_reanalyze: bool = Query(False, description="If True, forces re-running graph traversal and corrective retrieval."),
    db: AsyncSession = Depends(get_db),
) -> OmissionAnalysisSummary:
    engine = OmissionEngine(db)
    try:
        return await engine.analyze_document_omissions(document_id, force_reanalyze=force_reanalyze)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Omission analysis failed for document {document_id}: {err}",
        ) from err


@router.get(
    "/documents/{document_id}/omissions",
    response_model=OmissionAnalysisSummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Document Omission Results",
    description="Retrieves the latest omission analysis summary and surfaced candidates for a document.",
)
async def get_document_omission_results(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OmissionAnalysisSummary:
    stmt = (
        select(OmissionAnalysisModel)
        .where(OmissionAnalysisModel.document_id == document_id)
        .order_by(OmissionAnalysisModel.created_at.desc())
    )
    res = await db.execute(stmt)
    analysis = res.scalars().first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No omission analysis found for document {document_id}. Trigger analysis first via POST.",
        )

    engine = OmissionEngine(db)
    return await engine.get_analysis_summary(analysis.id)


@router.get(
    "/documents/{document_id}/omissions/candidates/{candidate_id}",
    response_model=OmissionCandidateRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Individual Candidate Explanation",
    description="Retrieves full relevance score breakdown, graph path, and provenance explanation for a single surfaced candidate.",
)
async def get_omission_candidate_details(
    document_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OmissionCandidateRead:
    stmt = select(OmissionCandidateModel).where(OmissionCandidateModel.id == candidate_id)
    res = await db.execute(stmt)
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Omission candidate {candidate_id} not found.",
        )

    return OmissionCandidateRead(
        id=candidate.id,
        person_label=candidate.person_label,
        wikidata_qid=candidate.wikidata_qid,
        classification=candidate.classification,
        has_concept_specific_evidence=candidate.has_concept_specific_evidence,
        relevance_score=candidate.relevance_score,
        score_breakdown=ScoreBreakdown(**candidate.score_breakdown),
        graph_path=candidate.graph_path,
        provenance=candidate.provenance,
        is_external_discovery=candidate.is_external_discovery,
    )
