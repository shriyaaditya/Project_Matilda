import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BOOLEAN, FLOAT, INT, JSON, TEXT, VARCHAR, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class UnifiedAnalysisModel(Base):
    __tablename__ = "unified_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_findings_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    omission_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    underattribution_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    overattribution_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    credit_aligns_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    insufficient_evidence_count: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    evidence_attention_score: Mapped[float] = mapped_column(FLOAT, nullable=False, default=0.0)
    corrective_retrieval_used: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)
    execution_time_ms: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    findings: Mapped[list["UnifiedFindingModel"]] = relationship(
        "UnifiedFindingModel", back_populates="analysis", cascade="all, delete-orphan"
    )


class UnifiedFindingModel(Base):
    __tablename__ = "unified_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unified_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    originating_phase: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("canonical_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_label: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    wikidata_qid: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    concept_label: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    finding_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    evidence_strength: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    fused_score: Mapped[float] = mapped_column(FLOAT, nullable=False)
    explanation_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    document_provenance: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    external_evidence: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    graph_paths: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)

    analysis: Mapped[UnifiedAnalysisModel] = relationship("UnifiedAnalysisModel", back_populates="findings")
