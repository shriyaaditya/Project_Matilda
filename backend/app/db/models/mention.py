import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    FLOAT,
    INT,
    TEXT,
    VARCHAR,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MentionModel(Base):
    __tablename__ = "mentions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sentence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sentences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(INT, nullable=False)
    paragraph_index: Mapped[int] = mapped_column(INT, nullable=False)
    sentence_index: Mapped[int] = mapped_column(INT, nullable=False)
    mention_type: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, index=True)  # 'PERSON', 'CONCEPT'
    raw_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    normalized_text: Mapped[str] = mapped_column(VARCHAR(512), nullable=False, index=True)
    start_char: Mapped[int] = mapped_column(INT, nullable=False)
    end_char: Mapped[int] = mapped_column(INT, nullable=False)
    confidence: Mapped[float | None] = mapped_column(FLOAT, nullable=True)  # NULL if unexposed
    extraction_method: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    model_version: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


__table_args__ = (
    Index("idx_mentions_doc_type", MentionModel.document_id, MentionModel.mention_type),
)
