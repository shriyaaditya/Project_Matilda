import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreditScoreBreakdown(BaseModel):
    role_mismatch_score: float = Field(..., description="Score for semantic role level mismatch [0.0, 1.0]")
    evidence_strength_score: float = Field(..., description="Score for historical evidence strength [0.0, 1.0]")
    concept_match_score: float = Field(..., description="Score for concept match quality [0.0, 1.0]")
    provenance_quality_score: float = Field(..., description="Score for provenance completeness [0.0, 1.0]")
    total_score: float = Field(..., description="Weighted total discrepancy score [0.0, 1.0]")


class CreditAttributionRead(BaseModel):
    id: uuid.UUID
    person_id: uuid.UUID | None = None
    person_label: str
    concept_label: str
    attribution_type: str = Field(
        ..., description="Attribution type: DISCOVERY_CREDIT | CONTRIBUTION_CREDIT | SUPPORTING_ROLE | COLLABORATIVE_CREDIT | PASSIVE_MENTION | NEUTRAL_MENTION"
    )
    grammatical_role: str = Field(
        ..., description="Grammatical role: ACTIVE_SUBJECT | PASSIVE_BY_AGENT | PREPOSITIONAL_OBJECT | CO_SUBJECT"
    )
    attribution_verb: str
    document_text: str
    evidence_text: str
    role_comparison_summary: str
    discrepancy_classification: str = Field(
        ..., description="Classification: DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE | POSSIBLE_UNDERATTRIBUTION | POSSIBLE_OVERATTRIBUTION | INSUFFICIENT_EVIDENCE"
    )
    discrepancy_score: float
    score_breakdown: CreditScoreBreakdown
    evidence_sources: dict[str, Any]


class CreditAnalysisSummary(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    total_attributions_extracted: int
    discrepancy_summary: dict[str, int]
    execution_time_ms: int
    created_at: datetime
    attributions: list[CreditAttributionRead]


class CreditEvalMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    total_attributions_evaluated: int
    true_positives: int
    false_positives: int
    false_negatives: int
