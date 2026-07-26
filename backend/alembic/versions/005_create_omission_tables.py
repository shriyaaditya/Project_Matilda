"""create omission tables

Revision ID: 005_create_omission_tables
Revises: 004_create_graph_tables
Create Date: 2026-07-26 15:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_create_omission_tables"
down_revision: str | None = "004_create_graph_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. omission_analyses table
    op.create_table(
        "omission_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("graph_version", sa.VARCHAR(length=32), nullable=False),
        sa.Column("coverage_score", sa.FLOAT(), nullable=False),
        sa.Column("triggered_corrective_retrieval", sa.BOOLEAN(), nullable=False),
        sa.Column("execution_time_ms", sa.INT(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_omission_analyses_document_id", "omission_analyses", ["document_id"])

    # 2. omission_candidates table
    op.create_table(
        "omission_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omission_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("person_label", sa.VARCHAR(length=256), nullable=False),
        sa.Column("wikidata_qid", sa.VARCHAR(length=64), nullable=True),
        sa.Column("classification", sa.VARCHAR(length=32), nullable=False),
        sa.Column("has_concept_specific_evidence", sa.BOOLEAN(), nullable=False),
        sa.Column("relevance_score", sa.FLOAT(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("graph_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_external_discovery", sa.BOOLEAN(), nullable=False),
    )
    op.create_index("ix_omission_candidates_analysis_id", "omission_candidates", ["analysis_id"])
    op.create_index("ix_omission_candidates_wikidata_qid", "omission_candidates", ["wikidata_qid"])


def downgrade() -> None:
    op.drop_index("ix_omission_candidates_wikidata_qid", table_name="omission_candidates")
    op.drop_index("ix_omission_candidates_analysis_id", table_name="omission_candidates")
    op.drop_table("omission_candidates")
    op.drop_index("ix_omission_analyses_document_id", table_name="omission_analyses")
    op.drop_table("omission_analyses")
