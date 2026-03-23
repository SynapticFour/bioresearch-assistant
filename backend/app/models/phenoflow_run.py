"""SQLAlchemy model for PhenoFlow orchestration runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PhenoFlowRun(Base):
    """A persisted master record for a PhenoFlow search-to-execution request.

    PhenoFlowRun groups multiple WES submissions (one per matched item) and
    stores the researcher-provided query/workflow specification for provenance.
    """

    __tablename__ = "phenoflow_runs"

    phenoflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    query_spec: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    workflow_spec: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )

    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PhenoFlowRun phenoflow_run_id={self.phenoflow_run_id!r} status={self.status!r}>"
