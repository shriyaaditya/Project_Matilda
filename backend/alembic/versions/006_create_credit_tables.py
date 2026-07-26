"""create credit tables

Revision ID: 006_create_credit_tables
Revises: 005_create_omission_tables
Create Date: 2026-07-26 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_create_credit_tables"
down_revision: str | None = "005_create_omission_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. credit_analyses table
    op.create_table(
        "credit_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_attributions_extracted", sa.INT(), nullable=False),
        sa.Column("discrepancy_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_time_ms", sa.INT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credit_analyses_document_id", "credit_analyses", ["document_id"])

    # 2. credit_attributions table
    op.create_table(
        "credit_attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("credit_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("person_label", sa.VARCHAR(length=256), nullable=False),
        sa.Column("concept_label", sa.VARCHAR(length=256), nullable=False),
        sa.Column("attribution_type", sa.VARCHAR(length=32), nullable=False),
        sa.Column("grammatical_role", sa.VARCHAR(length=32), nullable=False),
        sa.Column("attribution_verb", sa.VARCHAR(length=64), nullable=False),
        sa.Column("document_text", sa.TEXT(), nullable=False),
        sa.Column("evidence_text", sa.TEXT(), nullable=False),
        sa.Column("role_comparison_summary", sa.VARCHAR(length=512), nullable=False),
        sa.Column("discrepancy_classification", sa.VARCHAR(length=32), nullable=False),
        sa.Column("discrepancy_score", sa.FLOAT(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_credit_attributions_analysis_id", "credit_attributions", ["analysis_id"])
    op.create_index("ix_credit_attributions_person_id", "credit_attributions", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_credit_attributions_person_id", table_name="credit_attributions")
    op.drop_index("ix_credit_attributions_analysis_id", table_name="credit_attributions")
    op.drop_table("credit_attributions")
    op.drop_index("ix_credit_analyses_document_id", table_name="credit_analyses")
    op.drop_table("credit_analyses")
