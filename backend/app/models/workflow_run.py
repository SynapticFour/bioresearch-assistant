"""SQLAlchemy model for GA4GH WES workflow runs."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkflowRun(Base):
    """Single workflow run for GA4GH WES v1.1.

    Persists run metadata, state, and logs. Nextflow (or other engine)
    runs are executed via async subprocess; working files under
    /tmp/wes/{run_id}/.

    Attributes:
        run_id: GA4GH run identifier (UUID).
        state: One of QUEUED, RUNNING, COMPLETE, EXECUTOR_ERROR, etc.
        workflow_url: URL or path to workflow file.
        workflow_params: JSON workflow parameters.
        workflow_type: e.g. NEXTFLOW, CWL, WDL.
        workflow_type_version: Version string.
        workflow_engine: e.g. nextflow.
        workflow_engine_version: Optional engine version.
        tags: Optional key-value tags from RunRequest.
        start_time: When execution started (ISO 8601).
        end_time: When execution ended (ISO 8601).
        outputs: JSON outputs from workflow.
        run_log: Main run log (Log schema as JSON).
        task_logs: Array of Log/TaskLog for each step (JSON).
        request: Stored RunRequest for GetRunLog response (JSON).
        created_at: Record creation time.
    """

    __tablename__ = "workflow_runs"

    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    workflow_url: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_params: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    workflow_type: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_type_version: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_engine_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[dict[str, str] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outputs: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    run_log: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    task_logs: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    request: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun run_id={self.run_id!r} state={self.state!r}>"
