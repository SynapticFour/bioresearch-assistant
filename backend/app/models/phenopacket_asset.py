"""SQLAlchemy model for linking phenopackets to DRS objects.

PhenoFlow needs a canonical mapping from a stored Phenopacket (keyed by
``patient_records.pseudonym_id``) to one or more genomics assets stored in DRS
(``drs_object_id``). This table is the minimal building block for
Search-to-Execution provenance.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PhenopacketAsset(Base):
    """Mapping from a phenopacket pseudonym_id to a DRS object.

    Notes:
        * We store only DRS identifiers (relative object_id under ``drs_storage_path``).
        * ``drs_object_id`` can include path separators and "~" and follows the
          same character policy as DRS internal object IDs.
        * Isolation scoping is handled by application-level filters
          (``user_id``/``team_id``), mirroring existing patterns.
    """

    __tablename__ = "phenopacket_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pseudonym_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("patient_records.pseudonym_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drs_object_id: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
    )
    # Keep file_type as a constrained free-string; enforced in schema/service.
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)

    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("pseudonym_id", "drs_object_id", name="uq_phenopacket_asset_pair"),
    )

    def __repr__(self) -> str:
        return (
            "<PhenopacketAsset "
            f"pseudonym_id={self.pseudonym_id!r} drs_object_id={self.drs_object_id!r} "
            f"file_type={self.file_type!r}>"
        )
