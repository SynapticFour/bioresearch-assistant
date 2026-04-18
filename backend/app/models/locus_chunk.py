"""Locus: curated RAG index chunks (shared; not per-user). Same embedding dim as Paper."""

import os
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.paper import EMBEDDING_DIM


def _default_meta() -> dict:
    return {}


_json_type = JSONB().with_variant(JSON(), "sqlite") if not os.environ.get("TESTING") else JSON()
if os.environ.get("TESTING"):
    _embedding_type = JSON()
else:
    from pgvector.sqlalchemy import Vector

    _embedding_type = Vector(EMBEDDING_DIM)


class LocusChunk(Base):
    """One searchable segment from a Locus index (e.g. guideline excerpt, KDS blurb, GA4GH spec).

    Rows are **institution-shared** (no user_id) — the opposite of the personal Paper library.
    Ingestion from subscription / admin tooling is a separate process.
    """

    __tablename__ = "locus_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    corpus_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
        default="default",
    )
    source_ref: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default="",
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[dict] = mapped_column(
        _json_type,
        nullable=False,
        default=_default_meta,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        _embedding_type,
        nullable=True,
    )
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
        return f"<LocusChunk id={self.id!r} corpus_id={self.corpus_id!r} title={self.title[:40]!r}...>"
