"""002_create_mentions_table

Revision ID: 002_create_mentions_table
Revises: 001_create_document_tables
Create Date: 2026-07-26 08:35:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_create_mentions_table"
down_revision: str | None = "001_create_document_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sentence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sentences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.INT(), nullable=False),
        sa.Column("paragraph_index", sa.INT(), nullable=False),
        sa.Column("sentence_index", sa.INT(), nullable=False),
        sa.Column("mention_type", sa.VARCHAR(length=16), nullable=False),
        sa.Column("raw_text", sa.TEXT(), nullable=False),
        sa.Column("normalized_text", sa.VARCHAR(length=512), nullable=False),
        sa.Column("start_char", sa.INT(), nullable=False),
        sa.Column("end_char", sa.INT(), nullable=False),
        sa.Column("confidence", sa.FLOAT(), nullable=True),
        sa.Column("extraction_method", sa.VARCHAR(length=64), nullable=False),
        sa.Column("model_version", sa.VARCHAR(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_mentions_document_id", "mentions", ["document_id"])
    op.create_index("ix_mentions_sentence_id", "mentions", ["sentence_id"])
    op.create_index("ix_mentions_mention_type", "mentions", ["mention_type"])
    op.create_index("ix_mentions_normalized_text", "mentions", ["normalized_text"])
    op.create_index("idx_mentions_doc_type", "mentions", ["document_id", "mention_type"])


def downgrade() -> None:
    op.drop_index("idx_mentions_doc_type", table_name="mentions")
    op.drop_index("ix_mentions_normalized_text", table_name="mentions")
    op.drop_index("ix_mentions_mention_type", table_name="mentions")
    op.drop_index("ix_mentions_sentence_id", table_name="mentions")
    op.drop_index("ix_mentions_document_id", table_name="mentions")
    op.drop_table("mentions")
