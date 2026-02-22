"""Add language and mapping_id to pseudonymization_audit_log.

Revision ID: 005
Revises: 004
Create Date: 2025-02-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pseudonymization_audit_log",
        sa.Column("language", sa.String(8), nullable=True),
    )
    op.add_column(
        "pseudonymization_audit_log",
        sa.Column("mapping_id", sa.String(64), nullable=True),
    )
    op.create_index(
        op.f("ix_pseudonymization_audit_log_mapping_id"),
        "pseudonymization_audit_log",
        ["mapping_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pseudonymization_audit_log_mapping_id"),
        table_name="pseudonymization_audit_log",
    )
    op.drop_column("pseudonymization_audit_log", "mapping_id")
    op.drop_column("pseudonymization_audit_log", "language")
