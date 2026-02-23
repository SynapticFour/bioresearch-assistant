"""Add user_id, team_id, pseudonymized_text to pseudonymization_mappings.

Revision ID: 008
Revises: 007
Create Date: 2025-02-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pseudonymization_mappings",
        sa.Column("pseudonymized_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "pseudonymization_mappings",
        sa.Column("user_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "pseudonymization_mappings",
        sa.Column("team_id", sa.String(128), nullable=True),
    )
    op.create_index(
        op.f("ix_pseudonymization_mappings_user_id"),
        "pseudonymization_mappings",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_pseudonymization_mappings_team_id"),
        "pseudonymization_mappings",
        ["team_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pseudonymization_mappings_team_id"),
        table_name="pseudonymization_mappings",
    )
    op.drop_index(
        op.f("ix_pseudonymization_mappings_user_id"),
        table_name="pseudonymization_mappings",
    )
    op.drop_column("pseudonymization_mappings", "team_id")
    op.drop_column("pseudonymization_mappings", "user_id")
    op.drop_column("pseudonymization_mappings", "pseudonymized_text")
