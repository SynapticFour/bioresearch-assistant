"""Complete initial schema — squashed from 001-011.

Revision ID: 001
Revises: None
Create Date: 2026-02-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 768  # paraphrase-multilingual-mpnet-base-v2

_embedding_type = Vector(EMBEDDING_DIM) if Vector else sa.Text()


def upgrade() -> None:
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        pass

    # ── papers ──────────────────────────────────────
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pmid", sa.String(32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("abstract", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "authors",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("year", sa.String(16), nullable=True),
        sa.Column("journal", sa.Text(), nullable=False, server_default=""),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column("embedding", _embedding_type, nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_language", sa.String(16), nullable=True),
        sa.Column("summary_model", sa.String(128), nullable=True),
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
    op.create_index("ix_papers_pmid", "papers", ["pmid"], unique=True)
    op.create_index("ix_papers_user_id", "papers", ["user_id"])
    op.create_index("ix_papers_team_id", "papers", ["team_id"])
    op.create_index("ix_papers_year", "papers", ["year"])
    op.create_index("ix_papers_journal", "papers", ["journal"])
    op.create_index("ix_papers_user_year", "papers", ["user_id", "year"])
    op.create_index("ix_papers_team_year", "papers", ["team_id", "year"])

    # ── pseudonymization_audit_log ───────────────────
    op.create_table(
        "pseudonymization_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
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
        sa.Column("language", sa.String(8), nullable=True),
        sa.Column("mapping_id", sa.String(64), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_pseudonymization_audit_log_operation_id",
        "pseudonymization_audit_log",
        ["operation_id"],
        unique=True,
    )
    op.create_index(
        "ix_pseudonymization_audit_log_user_id",
        "pseudonymization_audit_log",
        ["user_id"],
    )
    op.create_index(
        "ix_pseudonymization_audit_log_input_hash",
        "pseudonymization_audit_log",
        ["input_hash"],
    )
    op.create_index(
        "ix_pseudonymization_audit_log_operation_type",
        "pseudonymization_audit_log",
        ["operation_type"],
    )
    op.create_index(
        "ix_pseudonymization_audit_log_mapping_id",
        "pseudonymization_audit_log",
        ["mapping_id"],
    )
    op.create_index(
        "ix_pseudonymization_audit_log_team_id",
        "pseudonymization_audit_log",
        ["team_id"],
    )

    # ── pseudonymization_mappings ────────────────────
    op.create_table(
        "pseudonymization_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mapping_id", sa.String(64), nullable=False),
        sa.Column("encrypted_mapping", sa.LargeBinary(), nullable=False),
        sa.Column("pseudonymized_text", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pseudonymization_mappings_mapping_id",
        "pseudonymization_mappings",
        ["mapping_id"],
        unique=True,
    )
    op.create_index(
        "ix_pseudonymization_mappings_user_id",
        "pseudonymization_mappings",
        ["user_id"],
    )
    op.create_index(
        "ix_pseudonymization_mappings_team_id",
        "pseudonymization_mappings",
        ["team_id"],
    )

    # ── patient_records ──────────────────────────────
    op.create_table(
        "patient_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pseudonym_id", sa.String(128), nullable=False),
        sa.Column("phenopacket_json", JSONB(), nullable=False),
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
    op.create_index(
        "ix_patient_records_pseudonym_id",
        "patient_records",
        ["pseudonym_id"],
        unique=True,
    )
    op.create_index("ix_patient_records_user_id", "patient_records", ["user_id"])
    op.create_index("ix_patient_records_team_id", "patient_records", ["team_id"])

    # ── workflow_runs ────────────────────────────────
    op.create_table(
        "workflow_runs",
        sa.Column("run_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("workflow_url", sa.Text(), nullable=False),
        sa.Column("workflow_params", JSONB(), nullable=True),
        sa.Column("workflow_type", sa.String(32), nullable=False),
        sa.Column("workflow_type_version", sa.String(32), nullable=False),
        sa.Column("workflow_engine", sa.String(64), nullable=True),
        sa.Column("workflow_engine_version", sa.String(64), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outputs", JSONB(), nullable=True),
        sa.Column("run_log", JSONB(), nullable=True),
        sa.Column("task_logs", JSONB(), nullable=True),
        sa.Column("request", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_workflow_runs_state", "workflow_runs", ["state"])

    # ── notebooks ────────────────────────────────────
    op.create_table(
        "notebooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "tags",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("user_id", sa.String(128), nullable=True),
        sa.Column("team_id", sa.String(128), nullable=True),
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
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_next_steps", sa.Text(), nullable=True),
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
    op.create_index("ix_notebooks_user_id", "notebooks", ["user_id"])
    op.create_index("ix_notebooks_team_id", "notebooks", ["team_id"])


def downgrade() -> None:
    op.drop_table("notebooks")
    op.drop_index("ix_workflow_runs_state", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index("ix_patient_records_team_id", table_name="patient_records")
    op.drop_index("ix_patient_records_user_id", table_name="patient_records")
    op.drop_index("ix_patient_records_pseudonym_id", table_name="patient_records")
    op.drop_table("patient_records")
    op.drop_index(
        "ix_pseudonymization_mappings_team_id",
        table_name="pseudonymization_mappings",
    )
    op.drop_index(
        "ix_pseudonymization_mappings_user_id",
        table_name="pseudonymization_mappings",
    )
    op.drop_index(
        "ix_pseudonymization_mappings_mapping_id",
        table_name="pseudonymization_mappings",
    )
    op.drop_table("pseudonymization_mappings")
    op.drop_index(
        "ix_pseudonymization_audit_log_team_id",
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        "ix_pseudonymization_audit_log_mapping_id",
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        "ix_pseudonymization_audit_log_operation_type",
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        "ix_pseudonymization_audit_log_input_hash",
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        "ix_pseudonymization_audit_log_user_id",
        table_name="pseudonymization_audit_log",
    )
    op.drop_index(
        "ix_pseudonymization_audit_log_operation_id",
        table_name="pseudonymization_audit_log",
    )
    op.drop_table("pseudonymization_audit_log")
    op.drop_index("ix_papers_team_year", table_name="papers")
    op.drop_index("ix_papers_user_year", table_name="papers")
    op.drop_index("ix_papers_journal", table_name="papers")
    op.drop_index("ix_papers_year", table_name="papers")
    op.drop_index("ix_papers_team_id", table_name="papers")
    op.drop_index("ix_papers_user_id", table_name="papers")
    op.drop_index("ix_papers_pmid", table_name="papers")
    op.drop_table("papers")
