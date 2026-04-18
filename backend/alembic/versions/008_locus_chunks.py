"""Locus curated RAG index chunks (pgvector, shared corpus).

Revision ID: 008
Revises: 007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 768


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    json_type = JSONB() if is_postgresql else sa.JSON()
    embedding_type = (
        Vector(EMBEDDING_DIM) if (is_postgresql and Vector) else sa.Text()
    )
    default_meta = sa.text("'{}'::jsonb") if is_postgresql else sa.text("'{}'")

    op.create_table(
        "locus_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("corpus_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("source_ref", sa.String(512), nullable=False, server_default=""),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", json_type, nullable=False, server_default=default_meta),
        sa.Column("embedding", embedding_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locus_chunks_corpus_id", "locus_chunks", ["corpus_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_locus_chunks_corpus_id", table_name="locus_chunks")
    op.drop_table("locus_chunks")
