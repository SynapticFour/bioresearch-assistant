"""Add notebooks.format for markdown vs ipynb (JupyterLite-class).

Revision ID: 011
Revises: 010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notebooks",
        sa.Column("format", sa.String(length=16), nullable=False, server_default="markdown"),
    )


def downgrade() -> None:
    op.drop_column("notebooks", "format")
