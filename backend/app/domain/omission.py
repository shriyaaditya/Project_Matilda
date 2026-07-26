import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    concept_evidence_score: float = Field(..., description="Score for direct concept evidence [0.0, 1.0]")
    relationship_spec_score: float = Field(..., description="Score for relationship specificity [0.0, 1.0]")
    distance_score: float = Field(..., description="Score for graph path distance [0.0, 1.0]")
    provenance_quality_score: float = Field(..., description="Score for provenance completeness [0.0, 1.0]")
    total_score: float = Field(..., description="Weighted total relevance score [0.0, 1.0]")


class OmissionCandidateRead(BaseModel):
    id: uuid.UUID
    person_label: str
    wikidata_qid: str | None = None
    classification: str = Field(
        ..., description="Classification: POTENTIAL_OMISSION | PRESENT_RELEVANT_CONTRIBUTOR | INSUFFICIENT_EVIDENCE"
    )
    has_concept_specific_evidence: bool
    relevance_score: float
    score_breakdown: ScoreBreakdown
    graph_path: list[dict[str, Any]]
    provenance: dict[str, Any]
    is_external_discovery: bool


class OmissionAnalysisSummary(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    graph_version: str
    coverage_score: float
    triggered_corrective_retrieval: bool
    execution_time_ms: int
    created_at: datetime
    candidates: list[OmissionCandidateRead]


class EvalMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    total_candidates: int
    true_positives: int
    false_positives: int
    false_negatives: int
