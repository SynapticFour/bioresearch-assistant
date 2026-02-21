"""Encrypted pseudonymization mapping storage (AES-256)."""

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PseudonymizationMapping(Base):
    """Stores AES-256 encrypted reversible mapping (placeholder -> original PII).

    Only the mapping_id is exposed to clients; decryption requires the app key.
    """

    __tablename__ = "pseudonymization_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mapping_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    encrypted_mapping: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PseudonymizationMapping mapping_id={self.mapping_id!r}>"
