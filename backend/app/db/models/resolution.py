import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import FLOAT, JSON, VARCHAR, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.person import CanonicalPersonModel

JSONType = JSONB().with_variant(JSON(), "sqlite")


class EntityResolutionModel(Base):
    __tablename__ = "entity_resolutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_people.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(16), nullable=False, index=True
    )  # 'RESOLVED', 'AMBIGUOUS', 'UNRESOLVED'
    resolution_score: Mapped[float] = mapped_column(FLOAT, nullable=False)
    matched_qid: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    person: Mapped[Optional["CanonicalPersonModel"]] = relationship(
        "CanonicalPersonModel", back_populates="resolutions"
    )


__table_args__ = (
    Index("idx_resolutions_doc_status", EntityResolutionModel.document_id, EntityResolutionModel.status),
)
