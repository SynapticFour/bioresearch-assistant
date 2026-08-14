"""Add WES run owners and per-user paper uniqueness.

Revision ID: 009
Revises: 008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("workflow_runs")}
    if "user_id" not in columns:
        op.add_column("workflow_runs", sa.Column("user_id", sa.String(length=128), nullable=True))
        op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"], unique=False)
    if "team_id" not in columns:
        op.add_column("workflow_runs", sa.Column("team_id", sa.String(length=128), nullable=True))
        op.create_index("ix_workflow_runs_team_id", "workflow_runs", ["team_id"], unique=False)

    paper_uniques = {u["name"] for u in inspector.get_unique_constraints("papers")}
    indexes = {i["name"] for i in inspector.get_indexes("papers")}
    # Drop global pmid uniqueness if present (name varies by dialect).
    if "ix_papers_pmid" in indexes:
        # keep non-unique index; unique was on the column itself
        pass
    for name in list(paper_uniques):
        if name and "pmid" in name.lower() and "user" not in name.lower():
            op.drop_constraint(name, "papers", type_="unique")
    if "uq_papers_pmid_user" not in paper_uniques:
        op.create_unique_constraint("uq_papers_pmid_user", "papers", ["pmid", "user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_papers_pmid_user", "papers", type_="unique")
    op.drop_index("ix_workflow_runs_team_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_user_id", table_name="workflow_runs")
    op.drop_column("workflow_runs", "team_id")
    op.drop_column("workflow_runs", "user_id")
