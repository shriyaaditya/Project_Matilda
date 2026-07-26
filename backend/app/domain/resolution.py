from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CanonicalPerson(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    canonical_name: str = Field(..., description="Standard primary name (e.g. 'Rosalind Franklin')")
    wikidata_qid: str | None = Field(None, description="Wikidata QID (e.g. 'Q7474')")
    birth_year: int | None = None
    death_year: int | None = None
    occupations: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResolutionEvidence(BaseModel):
    name_score: float
    context_score: float
    field_score: float
    matched_concepts: list[str] = Field(default_factory=list)
    evidence_summary: str
    competing_candidates: list[dict[str, Any]] = Field(default_factory=list)


class EntityResolution(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    mention_id: UUID
    document_id: UUID
    person_id: UUID | None = None  # NULL if UNRESOLVED or AMBIGUOUS
    status: str  # 'RESOLVED', 'AMBIGUOUS', 'UNRESOLVED'
    resolution_score: float = Field(..., description="Deterministic score [0.0 - 1.0]")
    matched_qid: str | None = None
    evidence: ResolutionEvidence
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResolutionSummary(BaseModel):
    document_id: UUID
    total_person_mentions: int
    resolved_count: int
    ambiguous_count: int
    unresolved_count: int
    is_already_resolved: bool
