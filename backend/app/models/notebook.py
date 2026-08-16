"""SQLAlchemy model for Research Notebook / ELN entries."""

import os
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# SQLite (tests) has no native UUID — use String(36)
if os.environ.get("TESTING"):
    _json_type = JSON()
    _id_type = String(36)
else:
    _json_type = JSONB().with_variant(JSON(), "sqlite")
    _id_type = PG_UUID(as_uuid=False)


class Notebook(Base):
    """Markdown-based research notebook with links to papers, DRS, phenopackets.

    Attributes:
        id: UUID primary key.
        title: Notebook title.
        content: Markdown or nbformat v4 JSON (see format).
        tags: List of tags (JSON array).
        user_id: Owner (isolation).
        team_id: Team scope (isolation).
        linked_pmids: PubMed IDs of linked papers.
        linked_drs_ids: DRS object IDs.
        linked_phenopacket_ids: Phenopacket pseudonym_ids.
        ai_summary: KI-generated summary (optional).
        ai_next_steps: KI-generated next steps (optional).
        created_at: Insert timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "notebooks"

    id: Mapped[str] = mapped_column(
        _id_type,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_format: Mapped[str] = mapped_column(
        "format", String(16), nullable=False, default="markdown"
    )
    tags: Mapped[list[str]] = mapped_column(_json_type, nullable=False, default=list)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    linked_pmids: Mapped[list[str]] = mapped_column(_json_type, nullable=False, default=list)
    linked_drs_ids: Mapped[list[str]] = mapped_column(_json_type, nullable=False, default=list)
    linked_phenopacket_ids: Mapped[list[str]] = mapped_column(
        _json_type, nullable=False, default=list
    )
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        return f"<Notebook id={self.id!r} title={self.title[:30]!r}...>"
