import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BOOLEAN, FLOAT, INT, JSON, VARCHAR, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class OmissionAnalysisModel(Base):
    __tablename__ = "omission_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    graph_version: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="1.0.0")
    coverage_score: Mapped[float] = mapped_column(FLOAT, nullable=False)
    triggered_corrective_retrieval: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)
    execution_time_ms: Mapped[int] = mapped_column(INT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    candidates: Mapped[list["OmissionCandidateModel"]] = relationship(
        "OmissionCandidateModel", back_populates="analysis", cascade="all, delete-orphan"
    )


class OmissionCandidateModel(Base):
    __tablename__ = "omission_candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("omission_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_label: Mapped[str] = mapped_column(VARCHAR(256), nullable=False)
    wikidata_qid: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True, index=True)
    classification: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    has_concept_specific_evidence: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)
    relevance_score: Mapped[float] = mapped_column(FLOAT, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    graph_path: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    is_external_discovery: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=False)

    analysis: Mapped[OmissionAnalysisModel] = relationship("OmissionAnalysisModel", back_populates="candidates")
