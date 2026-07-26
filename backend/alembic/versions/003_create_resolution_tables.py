"""003_create_resolution_tables

Revision ID: 003_create_resolution_tables
Revises: 002_create_mentions_table
Create Date: 2026-07-26 10:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_create_resolution_tables"
down_revision: str | None = "002_create_mentions_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. canonical_people table
    op.create_table(
        "canonical_people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.VARCHAR(length=512), nullable=False),
        sa.Column("wikidata_qid", sa.VARCHAR(length=32), nullable=True),
        sa.Column("birth_year", sa.INT(), nullable=True),
        sa.Column("death_year", sa.INT(), nullable=True),
        sa.Column("occupations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_canonical_people_canonical_name", "canonical_people", ["canonical_name"])
    op.create_index("ix_canonical_people_wikidata_qid", "canonical_people", ["wikidata_qid"], unique=True)

    # 2. entity_resolutions table
    op.create_table(
        "entity_resolutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "mention_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mentions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_people.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.VARCHAR(length=16), nullable=False),
        sa.Column("resolution_score", sa.FLOAT(), nullable=False),
        sa.Column("matched_qid", sa.VARCHAR(length=32), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_entity_resolutions_mention_id", "entity_resolutions", ["mention_id"])
    op.create_index("ix_entity_resolutions_document_id", "entity_resolutions", ["document_id"])
    op.create_index("ix_entity_resolutions_person_id", "entity_resolutions", ["person_id"])
    op.create_index("ix_entity_resolutions_status", "entity_resolutions", ["status"])
    op.create_index("idx_resolutions_doc_status", "entity_resolutions", ["document_id", "status"])

    # 3. wikidata_cache table
    op.create_table(
        "wikidata_cache",
        sa.Column("query_key", sa.VARCHAR(length=256), primary_key=True),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("wikidata_cache")
    op.drop_table("entity_resolutions")
    op.drop_table("canonical_people")
