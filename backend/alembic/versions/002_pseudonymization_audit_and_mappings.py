"""Pseudonymization audit log and encrypted mappings.

Revision ID: 002
Revises: 001
Create Date: 2025-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pseudonymization_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("entities_count", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pseudonymization_audit_log_operation_id"),
        "pseudonymization_audit_log",
        ["operation_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_pseudonymization_audit_log_user_id"),
        "pseudonymization_audit_log",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_pseudonymization_audit_log_input_hash"),
        "pseudonymization_audit_log",
        ["input_hash"],
    )
    op.create_index(
        op.f("ix_pseudonymization_audit_log_operation_type"),
        "pseudonymization_audit_log",
        ["operation_type"],
    )

    op.create_table(
        "pseudonymization_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mapping_id", sa.String(64), nullable=False),
        sa.Column("encrypted_mapping", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pseudonymization_mappings_mapping_id"),
        "pseudonymization_mappings",
        ["mapping_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pseudonymization_mappings_mapping_id"),
        table_name="pseudonymization_mappings",
    )
    op.drop_table("pseudonymization_mappings")
    op.drop_index(
        op.f("ix_pseudonymization_audit_log_operation_type"),
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        op.f("ix_pseudonymization_audit_log_input_hash"),
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        op.f("ix_pseudonymization_audit_log_user_id"),
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        op.f("ix_pseudonymization_audit_log_operation_id"),
        table_name="pseudonymization_audit_log",
    )
    op.drop_table("pseudonymization_audit_log")
