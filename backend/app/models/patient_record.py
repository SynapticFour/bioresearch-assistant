"""SQLAlchemy model for storing phenopackets by pseudonym_id (GA4GH Phenopackets v2)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PatientRecordModel(Base):
    """Stored phenopacket keyed by pseudonym_id only (no real PII)."""

    __tablename__ = "patient_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pseudonym_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    phenopacket_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
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
        return f"<PatientRecordModel pseudonym_id={self.pseudonym_id!r}>"
