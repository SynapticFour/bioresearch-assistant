"""Create papers table with pgvector embedding column.

Revision ID: 001
Revises:
Create Date: 2025-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op
from app.models.paper import EMBEDDING_DIM

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pmid", sa.String(32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=False),
        sa.Column("authors", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("year", sa.String(16), nullable=True),
        sa.Column("journal", sa.Text(), nullable=False),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_papers_pmid"), "papers", ["pmid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_papers_pmid"), table_name="papers")
    op.drop_table("papers")
