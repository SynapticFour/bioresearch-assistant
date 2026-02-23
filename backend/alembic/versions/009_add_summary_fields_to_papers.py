"""Add summary fields to papers.

Revision ID: 009
Revises: 008
Create Date: 2025-02-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("papers", sa.Column("summary_language", sa.String(16), nullable=True))
    op.add_column("papers", sa.Column("summary_model", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("papers", "summary_model")
    op.drop_column("papers", "summary_language")
    op.drop_column("papers", "summary")
