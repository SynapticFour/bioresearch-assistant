"""Add user_id and team_id for configurable isolation (user/team/open).

Revision ID: 006
Revises: 005
Create Date: 2025-02-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ["papers", "patient_records"]:
        op.add_column(
            table,
            sa.Column("user_id", sa.String(128), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("team_id", sa.String(128), nullable=True),
        )

    op.add_column(
        "pseudonymization_audit_log",
        sa.Column("team_id", sa.String(128), nullable=True),
    )

    op.create_index("ix_papers_user_id", "papers", ["user_id"])
    op.create_index("ix_papers_team_id", "papers", ["team_id"])
    op.create_index("ix_patient_records_user_id", "patient_records", ["user_id"])
    op.create_index("ix_patient_records_team_id", "patient_records", ["team_id"])
    op.create_index(
        "ix_pseudonymization_audit_log_team_id",
        "pseudonymization_audit_log",
        ["team_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pseudonymization_audit_log_team_id", "pseudonymization_audit_log")
    op.drop_index("ix_patient_records_team_id", "patient_records")
    op.drop_index("ix_patient_records_user_id", "patient_records")
    op.drop_index("ix_papers_team_id", "papers")
    op.drop_index("ix_papers_user_id", "papers")

    op.drop_column("pseudonymization_audit_log", "team_id")

    for table in ["papers", "patient_records"]:
        op.drop_column(table, "team_id")
        op.drop_column(table, "user_id")
