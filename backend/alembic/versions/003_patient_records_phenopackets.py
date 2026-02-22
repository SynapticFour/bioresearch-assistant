"""Patient records table for GA4GH Phenopackets (keyed by pseudonym_id).

Revision ID: 003
Revises: 002
Create Date: 2025-02-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pseudonym_id", sa.String(128), nullable=False),
        sa.Column("phenopacket_json", JSONB, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_patient_records_pseudonym_id"),
        "patient_records",
        ["pseudonym_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_patient_records_pseudonym_id"),
        table_name="patient_records",
    )
    op.drop_table("patient_records")
