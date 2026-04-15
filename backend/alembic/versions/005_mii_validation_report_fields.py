"""Add dedicated validation report fields to mii_export_jobs.

Revision ID: 005
Revises: 004
Create Date: 2026-04-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    json_type = JSONB() if is_postgresql else sa.JSON()

    op.add_column("mii_export_jobs", sa.Column("validation_summary", json_type, nullable=True))
    op.add_column(
        "mii_export_jobs",
        sa.Column("validator_ig_package_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "mii_export_jobs",
        sa.Column("validator_ig_package_version", sa.String(64), nullable=True),
    )
    op.add_column("mii_export_jobs", sa.Column("validator_mode", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("mii_export_jobs", "validator_mode")
    op.drop_column("mii_export_jobs", "validator_ig_package_version")
    op.drop_column("mii_export_jobs", "validator_ig_package_id")
    op.drop_column("mii_export_jobs", "validation_summary")
