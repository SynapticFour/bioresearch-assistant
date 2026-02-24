"""Add notebooks table

Revision ID: 011
Revises: 010
Create Date: 2026-02-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.has_table(conn, "notebooks"):
        return
    op.create_table(
        "notebooks",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "title",
            sa.String(512),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "tags",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "user_id",
            sa.String(128),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            sa.String(128),
            nullable=True,
        ),
        sa.Column(
            "linked_pmids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "linked_drs_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "linked_phenopacket_ids",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "ai_summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "ai_next_steps",
            sa.Text(),
            nullable=True,
        ),
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
    op.create_index(op.f("ix_notebooks_user_id"), "notebooks", ["user_id"], unique=False)
    op.create_index(op.f("ix_notebooks_team_id"), "notebooks", ["team_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if not conn.dialect.has_table(conn, "notebooks"):
        return
    op.drop_index(op.f("ix_notebooks_team_id"), table_name="notebooks")
    op.drop_index(op.f("ix_notebooks_user_id"), table_name="notebooks")
    op.drop_table("notebooks")
