"""Terminology mapping overrides (governance / operational corrections).

Revision ID: 007
Revises: 006
Create Date: 2026-04-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    uuid_type = PG_UUID(as_uuid=True) if is_postgresql else Uuid(as_uuid=True)
    bool_default = sa.text("true") if is_postgresql else sa.text("1")

    op.create_table(
        "terminology_mapping_overrides",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("module", sa.String(length=32), nullable=False),
        sa.Column("raw_id", sa.String(length=512), nullable=False),
        sa.Column("target_system", sa.String(length=512), nullable=False),
        sa.Column("target_code", sa.String(length=256), nullable=False),
        sa.Column("target_display", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=bool_default),
        sa.Column("created_by_user_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module", "raw_id", name="uq_terminology_override_module_raw"),
    )
    op.create_index(
        "ix_terminology_mapping_overrides_module",
        "terminology_mapping_overrides",
        ["module"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_terminology_mapping_overrides_module", table_name="terminology_mapping_overrides")
    op.drop_table("terminology_mapping_overrides")
