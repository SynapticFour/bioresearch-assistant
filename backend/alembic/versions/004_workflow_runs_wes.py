"""Workflow runs table for GA4GH WES v1.1.

Revision ID: 004
Revises: 003
Create Date: 2025-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("run_id", UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("workflow_url", sa.Text(), nullable=False),
        sa.Column("workflow_params", JSONB, nullable=True),
        sa.Column("workflow_type", sa.String(32), nullable=False),
        sa.Column("workflow_type_version", sa.String(32), nullable=False),
        sa.Column("workflow_engine", sa.String(64), nullable=True),
        sa.Column("workflow_engine_version", sa.String(64), nullable=True),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outputs", JSONB, nullable=True),
        sa.Column("run_log", JSONB, nullable=True),
        sa.Column("task_logs", JSONB, nullable=True),
        sa.Column("request", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_workflow_runs_state"), "workflow_runs", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_runs_state"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
