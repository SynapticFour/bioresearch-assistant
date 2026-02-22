"""Add composite indexes for paper list filters (user_id/year, team_id/year, journal).

Revision ID: 007
Revises: 006
Create Date: 2025-02-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_papers_user_year",
        "papers",
        ["user_id", "year"],
        unique=False,
    )
    op.create_index(
        "ix_papers_team_year",
        "papers",
        ["team_id", "year"],
        unique=False,
    )
    op.create_index(
        "ix_papers_journal",
        "papers",
        ["journal"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_papers_journal", table_name="papers")
    op.drop_index("ix_papers_team_year", table_name="papers")
    op.drop_index("ix_papers_user_year", table_name="papers")
