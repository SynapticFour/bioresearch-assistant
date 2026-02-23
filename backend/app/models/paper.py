"""SQLAlchemy model for papers with vector embeddings (pgvector)."""

import os
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# all-MiniLM-L6-v2 produces 384-dim embeddings; use 1536 for OpenAI-compatible backends if needed
EMBEDDING_DIM = 384

# SQLite (tests) does not support pgvector/ARRAY — use JSON when TESTING=1
if os.environ.get("TESTING"):
    from sqlalchemy import JSON

    _authors_type = JSON()
    _embedding_type = JSON()
else:
    from pgvector.sqlalchemy import Vector
    from sqlalchemy.dialects.postgresql import ARRAY

    _authors_type = ARRAY(String)
    _embedding_type = Vector(EMBEDDING_DIM)


class Paper(Base):
    """Stored paper with abstract and embedding for semantic search.

    Attributes:
        id: Primary key.
        pmid: PubMed ID (unique).
        title: Article title.
        abstract: Full abstract text.
        authors: List of author names (stored as PostgreSQL array).
        year: Publication year (nullable).
        journal: Journal title.
        doi: Digital Object Identifier (nullable).
        embedding: Dense vector for semantic similarity (cosine); dimension EMBEDDING_DIM.
        created_at: Insert timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pmid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    abstract: Mapped[str] = mapped_column(Text, nullable=False, default="")
    authors: Mapped[list[str]] = mapped_column(_authors_type, nullable=False, default=list)
    year: Mapped[str | None] = mapped_column(String(16), nullable=True)
    journal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        _embedding_type,
        nullable=True,
    )
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    team_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
        return f"<Paper pmid={self.pmid!r} title={self.title[:50]!r}...>"
