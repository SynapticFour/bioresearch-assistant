"""MII export + research consent tables.

Revision ID: 004
Revises: 003
Create Date: 2026-04-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    json_type = JSONB() if is_postgresql else sa.JSON()
    uuid_type = PG_UUID(as_uuid=True) if is_postgresql else Uuid(as_uuid=True)
    json_empty_array = sa.text("'[]'::jsonb") if is_postgresql else sa.text("'[]'")
    json_empty_object = sa.text("'{}'::jsonb") if is_postgresql else sa.text("'{}'")

    op.create_table(
        "research_consents",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("pseudonym_id", sa.String(128), nullable=False),
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "covered_project_ids",
            json_type,
            nullable=False,
            server_default=json_empty_array,
        ),
        sa.Column("purpose_codes", json_type, nullable=False, server_default=json_empty_array),
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("meta_json", json_type, nullable=False, server_default=json_empty_object),
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
    )
    op.create_index("ix_research_consents_pseudonym_id", "research_consents", ["pseudonym_id"])
    op.create_index("ix_research_consents_status", "research_consents", ["status"])
    op.create_index("ix_research_consents_user_id", "research_consents", ["user_id"])
    op.create_index("ix_research_consents_team_id", "research_consents", ["team_id"])
    op.create_index(
        "ix_research_consents_policy",
        "research_consents",
        ["pseudonym_id", "policy_id"],
    )

    op.create_table(
        "research_consent_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("consent_id", uuid_type, nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("actor_user_id", sa.String(128), nullable=True),
        sa.Column("payload", json_type, nullable=False, server_default=json_empty_object),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["research_consents.id"],
            name="fk_consent_events_consent",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_research_consent_events_consent_id",
        "research_consent_events",
        ["consent_id"],
    )

    op.create_table(
        "mii_export_jobs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("requested_by_user_id", sa.String(128), nullable=False),
        sa.Column("scope_snapshot", json_type, nullable=False),
        sa.Column("input", json_type, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("consent_check_summary", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mii_export_jobs_status", "mii_export_jobs", ["status"])

    op.create_table(
        "mii_export_artifacts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("job_id", uuid_type, nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("bundle_json", json_type, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("profile_set_version", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["mii_export_jobs.id"],
            name="fk_mii_artifact_job",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_mii_export_artifacts_job_id", "mii_export_artifacts", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_mii_export_artifacts_job_id", table_name="mii_export_artifacts")
    op.drop_table("mii_export_artifacts")
    op.drop_index("ix_mii_export_jobs_status", table_name="mii_export_jobs")
    op.drop_table("mii_export_jobs")
    op.drop_index("ix_research_consent_events_consent_id", table_name="research_consent_events")
    op.drop_table("research_consent_events")
    op.drop_index("ix_research_consents_policy", table_name="research_consents")
    op.drop_index("ix_research_consents_team_id", table_name="research_consents")
    op.drop_index("ix_research_consents_user_id", table_name="research_consents")
    op.drop_index("ix_research_consents_status", table_name="research_consents")
    op.drop_index("ix_research_consents_pseudonym_id", table_name="research_consents")
    op.drop_table("research_consents")
