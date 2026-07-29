import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UnifiedScoreBreakdown(BaseModel):
    max_claim_score: float = Field(..., description="Max base claim score across deduplicated evidence items [0.0, 1.0]")
    corroboration_bonus: float = Field(..., description="Corroboration bonus for independent sources [0.0, 1.0]")
    deduplicated_source_count: int = Field(..., description="Number of unique deduplicated evidence sources")
    has_direct_concept_evidence: bool = Field(..., description="True if at least one concept-specific evidence item is present")
    fused_score: float = Field(..., description="Final fused evidence score [0.0, 1.0]")
    deduplication_log: list[str] = Field(default_factory=list, description="Audit log of normalized source deduplications")


class UnifiedFindingRead(BaseModel):
    id: uuid.UUID
    originating_phase: str = Field(..., description="Originating phase: PHASE_5_OMISSION | PHASE_6_CREDIT")
    person_id: uuid.UUID | None = None
    person_label: str
    wikidata_qid: str | None = None
    concept_label: str
    finding_type: str = Field(
        ..., description="Finding type: POTENTIAL_OMISSION | POSSIBLE_UNDERATTRIBUTION | POSSIBLE_OVERATTRIBUTION | CREDIT_ALIGNS | INSUFFICIENT_EVIDENCE"
    )
    evidence_strength: str = Field(..., description="Qualitative category: STRONG | MODERATE | WEAK | INSUFFICIENT")
    fused_score: float
    explanation_text: str
    score_breakdown: UnifiedScoreBreakdown
    document_provenance: dict[str, Any]
    external_evidence: dict[str, Any]
    graph_paths: list[dict[str, Any]]


class UnifiedAnalysisSummary(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    total_findings_count: int
    omission_count: int
    underattribution_count: int
    overattribution_count: int
    credit_aligns_count: int
    insufficient_evidence_count: int
    evidence_attention_score: float = Field(..., description="Neutral coverage indicator measuring recognized historical links [0.0, 1.0]")
    corrective_retrieval_used: bool
    execution_time_ms: int
    created_at: datetime
    findings: list[UnifiedFindingRead]


class UnifiedEvalMetrics(BaseModel):
    omission_precision: float
    omission_recall: float
    omission_f1: float
    credit_precision: float
    credit_recall: float
    credit_f1: float
    overall_evidence_coverage: float
