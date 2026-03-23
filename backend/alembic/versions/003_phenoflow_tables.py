"""Create PhenoFlow v0.1 tables.

Revision ID: 003
Revises: 002
Create Date: 2026-03-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Uuid

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    json_type = JSONB() if is_postgresql else sa.JSON()
    uuid_type = PG_UUID(as_uuid=True) if is_postgresql else Uuid(as_uuid=True)

    # ── phenopacket_assets ─────────────────────────────────────────────
    op.create_table(
        "phenopacket_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pseudonym_id", sa.String(128), nullable=False),
        sa.Column("drs_object_id", sa.String(2048), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "pseudonym_id",
            "drs_object_id",
            name="uq_phenopacket_asset_pair",
        ),
    )
    op.create_index("ix_phenopacket_assets_pseudonym_id", "phenopacket_assets", ["pseudonym_id"])
    op.create_index("ix_phenopacket_assets_drs_object_id", "phenopacket_assets", ["drs_object_id"])
    op.create_index("ix_phenopacket_assets_user_id", "phenopacket_assets", ["user_id"])
    op.create_index("ix_phenopacket_assets_team_id", "phenopacket_assets", ["team_id"])

    # ── phenoflow_runs ─────────────────────────────────────────────────
    op.create_table(
        "phenoflow_runs",
        sa.Column("phenoflow_run_id", uuid_type, primary_key=True, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("query_spec", json_type, nullable=False),
        sa.Column("workflow_spec", json_type, nullable=False),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_phenoflow_runs_status", "phenoflow_runs", ["status"])
    op.create_index("ix_phenoflow_runs_user_id", "phenoflow_runs", ["user_id"])
    op.create_index("ix_phenoflow_runs_team_id", "phenoflow_runs", ["team_id"])

    # ── phenoflow_run_items ─────────────────────────────────────────────
    op.create_table(
        "phenoflow_run_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phenoflow_run_id", uuid_type, nullable=False, index=True),
        sa.Column("pseudonym_id", sa.String(128), nullable=False),
        sa.Column("drs_object_id", sa.String(2048), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("wes_run_id", uuid_type, nullable=True),
        sa.Column("state_snapshot", sa.String(32), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_phenoflow_run_items_phenoflow_run_id", "phenoflow_run_items", ["phenoflow_run_id"])
    op.create_index("ix_phenoflow_run_items_pseudonym_id", "phenoflow_run_items", ["pseudonym_id"])
    op.create_index("ix_phenoflow_run_items_wes_run_id", "phenoflow_run_items", ["wes_run_id"])


def downgrade() -> None:
    op.drop_index("ix_phenoflow_run_items_wes_run_id", table_name="phenoflow_run_items")
    op.drop_index(
        "ix_phenoflow_run_items_pseudonym_id",
        table_name="phenoflow_run_items",
    )
    op.drop_index(
        "ix_phenoflow_run_items_phenoflow_run_id",
        table_name="phenoflow_run_items",
    )
    op.drop_table("phenoflow_run_items")

    op.drop_index("ix_phenoflow_runs_team_id", table_name="phenoflow_runs")
    op.drop_index("ix_phenoflow_runs_user_id", table_name="phenoflow_runs")
    op.drop_index("ix_phenoflow_runs_status", table_name="phenoflow_runs")
    op.drop_table("phenoflow_runs")

    op.drop_index("ix_phenopacket_assets_team_id", table_name="phenopacket_assets")
    op.drop_index("ix_phenopacket_assets_user_id", table_name="phenopacket_assets")
    op.drop_index("ix_phenopacket_assets_drs_object_id", table_name="phenopacket_assets")
    op.drop_index("ix_phenopacket_assets_pseudonym_id", table_name="phenopacket_assets")
    op.drop_table("phenopacket_assets")

