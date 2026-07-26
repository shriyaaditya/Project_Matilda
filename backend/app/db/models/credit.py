import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import FLOAT, INT, JSON, TEXT, VARCHAR, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class CreditAnalysisModel(Base):
    __tablename__ = "credit_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    total_attributions_extracted: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    discrepancy_summary: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    attributions: Mapped[list["CreditAttributionModel"]] = relationship(
        "CreditAttributionModel", back_populates="analysis", cascade="all, delete-orphan"
    )


class CreditAttributionModel(Base):
    __tablename__ = "credit_attributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("canonical_people.id", ondelete="SET NULL"), nullable=True, index=True
    )
    person_label: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    concept_label: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    attribution_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    grammatical_role: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    attribution_verb: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    document_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    evidence_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    role_comparison_summary: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    discrepancy_classification: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    discrepancy_score: Mapped[float] = mapped_column(FLOAT, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    evidence_sources: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)

    analysis: Mapped[CreditAnalysisModel] = relationship("CreditAnalysisModel", back_populates="attributions")
