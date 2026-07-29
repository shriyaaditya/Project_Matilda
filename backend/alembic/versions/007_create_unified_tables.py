"""create unified tables

Revision ID: 007_create_unified_tables
Revises: 006_create_credit_tables
Create Date: 2026-07-26 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_create_unified_tables"
down_revision: str | None = "006_create_credit_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. unified_analyses table
    op.create_table(
        "unified_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_findings_count", sa.INT(), nullable=False),
        sa.Column("omission_count", sa.INT(), nullable=False),
        sa.Column("underattribution_count", sa.INT(), nullable=False),
        sa.Column("overattribution_count", sa.INT(), nullable=False),
        sa.Column("credit_aligns_count", sa.INT(), nullable=False),
        sa.Column("insufficient_evidence_count", sa.INT(), nullable=False),
        sa.Column("evidence_attention_score", sa.FLOAT(), nullable=False),
        sa.Column("corrective_retrieval_used", sa.BOOLEAN(), nullable=False, default=False),
        sa.Column("execution_time_ms", sa.INT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_unified_analyses_document_id", "unified_analyses", ["document_id"])

    # 2. unified_findings table
    op.create_table(
        "unified_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("unified_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("originating_phase", sa.VARCHAR(length=16), nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("person_label", sa.VARCHAR(length=256), nullable=False),
        sa.Column("wikidata_qid", sa.VARCHAR(length=64), nullable=True),
        sa.Column("concept_label", sa.VARCHAR(length=256), nullable=False),
        sa.Column("finding_type", sa.VARCHAR(length=32), nullable=False),
        sa.Column("evidence_strength", sa.VARCHAR(length=16), nullable=False),
        sa.Column("fused_score", sa.FLOAT(), nullable=False),
        sa.Column("explanation_text", sa.TEXT(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("external_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("graph_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_unified_findings_analysis_id", "unified_findings", ["analysis_id"])
    op.create_index("ix_unified_findings_person_id", "unified_findings", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_unified_findings_person_id", table_name="unified_findings")
    op.drop_index("ix_unified_findings_analysis_id", table_name="unified_findings")
    op.drop_table("unified_findings")
    op.drop_index("ix_unified_analyses_document_id", table_name="unified_analyses")
    op.drop_table("unified_analyses")
