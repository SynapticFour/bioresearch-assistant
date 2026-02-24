"""Change embedding dimension to 768 (multilingual model).

Revision ID: 010
Revises: 009
Create Date: 2025-02-23

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if os.environ.get("TESTING"):
        return
    try:
        from pgvector.sqlalchemy import Vector

        op.drop_column("papers", "embedding")
        op.add_column(
            "papers",
            sa.Column("embedding", Vector(768), nullable=True),
        )
    except Exception:
        pass


def downgrade() -> None:
    if os.environ.get("TESTING"):
        return
    try:
        from pgvector.sqlalchemy import Vector

        op.drop_column("papers", "embedding")
        op.add_column(
            "papers",
            sa.Column("embedding", Vector(384), nullable=True),
        )
    except Exception:
        pass
