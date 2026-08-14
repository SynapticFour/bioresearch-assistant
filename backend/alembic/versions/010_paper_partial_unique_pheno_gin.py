"""Partial unique indexes for papers pmid; phenopacket JSONB GIN.

Revision ID: 010
Revises: 009

Postgres UNIQUE (pmid, user_id) treats NULLs as distinct, so multiple rows with
the same pmid and NULL user_id are allowed. Replace with partial unique indexes.
SQLite tests keep the SQLAlchemy UniqueConstraint on the model.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    paper_uniques = {u["name"] for u in inspector.get_unique_constraints("papers")}
    if "uq_papers_pmid_user" in paper_uniques:
        op.drop_constraint("uq_papers_pmid_user", "papers", type_="unique")

    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_papers_pmid_user_not_null "
            "ON papers (pmid, user_id) WHERE user_id IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_papers_pmid_null_user "
            "ON papers (pmid) WHERE user_id IS NULL"
        )
    )

    tables = set(inspector.get_table_names())
    if "patient_records" in tables:
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_patient_records_phenopacket_gin "
                "ON patient_records USING GIN (phenopacket_json)"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(sa.text("DROP INDEX IF EXISTS ix_patient_records_phenopacket_gin"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_papers_pmid_null_user"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_papers_pmid_user_not_null"))
    op.create_unique_constraint("uq_papers_pmid_user", "papers", ["pmid", "user_id"])
