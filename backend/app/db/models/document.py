import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    FLOAT,
    INT,
    TEXT,
    VARCHAR,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(
        VARCHAR(64), unique=True, index=True, nullable=False
    )
    file_path: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    page_count: Mapped[int] = mapped_column(INT, nullable=False)
    status: Mapped[str] = mapped_column(
        VARCHAR(32), nullable=False, default="PROCESSING"
    )
    error_message: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    pages: Mapped[list["PageModel"]] = relationship(
        "PageModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="PageModel.page_number",
    )


class PageModel(Base):
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(INT, nullable=False)
    has_extractable_text: Mapped[bool] = mapped_column(
        BOOLEAN, nullable=False, default=True
    )
    raw_text: Mapped[str] = mapped_column(TEXT, nullable=False)

    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="pages")
    paragraphs: Mapped[list["ParagraphModel"]] = relationship(
        "ParagraphModel",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="ParagraphModel.paragraph_index",
    )


class ParagraphModel(Base):
    __tablename__ = "paragraphs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paragraph_index: Mapped[int] = mapped_column(INT, nullable=False)
    text: Mapped[str] = mapped_column(TEXT, nullable=False)
    bbox_x0: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(FLOAT, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(FLOAT, nullable=True)

    page: Mapped["PageModel"] = relationship("PageModel", back_populates="paragraphs")
    sentences: Mapped[list["SentenceModel"]] = relationship(
        "SentenceModel",
        back_populates="paragraph",
        cascade="all, delete-orphan",
        order_by="SentenceModel.sentence_index",
    )


class SentenceModel(Base):
    __tablename__ = "sentences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    paragraph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paragraphs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(INT, nullable=False)
    paragraph_index: Mapped[int] = mapped_column(INT, nullable=False)
    sentence_index: Mapped[int] = mapped_column(INT, nullable=False)
    global_sentence_index: Mapped[int] = mapped_column(INT, nullable=False)
    text: Mapped[str] = mapped_column(TEXT, nullable=False)
    char_count: Mapped[int] = mapped_column(INT, nullable=False)

    paragraph: Mapped["ParagraphModel"] = relationship("ParagraphModel", back_populates="sentences")


__table_args__ = (
    Index("idx_sentences_doc_page", SentenceModel.document_id, SentenceModel.page_number),
)
