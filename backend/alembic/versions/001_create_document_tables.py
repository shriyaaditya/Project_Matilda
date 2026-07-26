"""001_create_document_tables

Revision ID: 001_create_document_tables
Revises:
Create Date: 2026-07-26 08:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_create_document_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.VARCHAR(length=512), nullable=False),
        sa.Column("file_size_bytes", sa.BIGINT(), nullable=False),
        sa.Column("sha256_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column("file_path", sa.VARCHAR(length=512), nullable=False),
        sa.Column("page_count", sa.INT(), nullable=False),
        sa.Column("status", sa.VARCHAR(length=32), nullable=False),
        sa.Column("error_message", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"], unique=True)

    # 2. pages table
    op.create_table(
        "pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.INT(), nullable=False),
        sa.Column("has_extractable_text", sa.BOOLEAN(), nullable=False),
        sa.Column("raw_text", sa.TEXT(), nullable=False),
    )
    op.create_index("ix_pages_document_id", "pages", ["document_id"])

    # 3. paragraphs table
    op.create_table(
        "paragraphs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("paragraph_index", sa.INT(), nullable=False),
        sa.Column("text", sa.TEXT(), nullable=False),
        sa.Column("bbox_x0", sa.FLOAT(), nullable=True),
        sa.Column("bbox_y0", sa.FLOAT(), nullable=True),
        sa.Column("bbox_x1", sa.FLOAT(), nullable=True),
        sa.Column("bbox_y1", sa.FLOAT(), nullable=True),
    )
    op.create_index("ix_paragraphs_page_id", "paragraphs", ["page_id"])
    op.create_index("ix_paragraphs_document_id", "paragraphs", ["document_id"])

    # 4. sentences table
    op.create_table(
        "sentences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paragraph_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("paragraphs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.INT(), nullable=False),
        sa.Column("paragraph_index", sa.INT(), nullable=False),
        sa.Column("sentence_index", sa.INT(), nullable=False),
        sa.Column("global_sentence_index", sa.INT(), nullable=False),
        sa.Column("text", sa.TEXT(), nullable=False),
        sa.Column("char_count", sa.INT(), nullable=False),
    )
    op.create_index("ix_sentences_paragraph_id", "sentences", ["paragraph_id"])
    op.create_index("ix_sentences_document_id", "sentences", ["document_id"])
    op.create_index("idx_sentences_doc_page", "sentences", ["document_id", "page_number"])


def downgrade() -> None:
    op.drop_table("sentences")
    op.drop_table("paragraphs")
    op.drop_table("pages")
    op.drop_table("documents")
