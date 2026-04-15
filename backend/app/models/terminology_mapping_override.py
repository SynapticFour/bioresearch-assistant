"""Admin-configurable terminology mapping overrides for MII export."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TerminologyMappingOverride(Base):
    """Override default Phenopacket id → FHIR Coding mapping (per module + raw id)."""

    __tablename__ = "terminology_mapping_overrides"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    module: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    raw_id: Mapped[str] = mapped_column(String(512), nullable=False)
    target_system: Mapped[str] = mapped_column(String(512), nullable=False)
    target_code: Mapped[str] = mapped_column(String(256), nullable=False)
    target_display: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
