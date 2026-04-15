"""MII-KDS FHIR export jobs and artifacts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MiiExportJob(Base):
    """Tracks MII bundle export requests (async-capable)."""

    __tablename__ = "mii_export_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    requested_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scope_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    input: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    consent_check_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    validator_ig_package_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    validator_ig_package_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validator_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts: Mapped[list["MiiExportArtifact"]] = relationship(
        "MiiExportArtifact",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class MiiExportArtifact(Base):
    """Stored FHIR Bundle JSON for a completed job."""

    __tablename__ = "mii_export_artifacts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("mii_export_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    job: Mapped["MiiExportJob"] = relationship("MiiExportJob", back_populates="artifacts")
