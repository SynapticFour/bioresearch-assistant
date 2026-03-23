"""SQLAlchemy model for PhenoFlow run item-level provenance."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PhenoFlowRunItem(Base):
    """One matched item within a PhenoFlowRun.

    Each item represents the provenance chain for exactly one WES submission:
    which Phenopacket (pseudonym_id) and which DRS object triggered the run.
    """

    __tablename__ = "phenoflow_run_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    phenoflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    pseudonym_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    drs_object_id: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)

    wes_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    state_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            "<PhenoFlowRunItem "
            f"phenoflow_run_id={self.phenoflow_run_id!r} pseudonym_id={self.pseudonym_id!r} "
            f"drs_object_id={self.drs_object_id!r} wes_run_id={self.wes_run_id!r}>"
        )
