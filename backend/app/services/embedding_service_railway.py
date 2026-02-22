"""Railway-stub: Embeddings nicht verfügbar (semantic search disabled)."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.schemas.pubmed import PubMedArticle


class EmbeddingServiceError(Exception):
    """Raised when embedding or DB operations fail (not used in stub)."""

    pass


class EmbeddingService:
    """Stub: no sentence-transformers on Railway; returns zeros / empty."""

    def __init__(self, model_name: str = "") -> None:
        self._model_name = model_name
        self._model: Any = None

    def embed_text(self, text: str) -> list[float] | None:
        """No embedding on Railway; return None."""
        return None

    async def embed_text_async(self, text: str) -> list[float] | None:
        """No embedding on Railway; return None (store NULL in DB)."""
        return None

    async def store_paper(
        self,
        db: AsyncSession,
        paper: PubMedArticle,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> Paper:
        """Store paper without embedding on Railway (embedding = NULL in DB)."""
        from sqlalchemy import select

        authors_list = list(paper.authors) if paper.authors else []
        text_to_embed = (paper.abstract or paper.title or "").strip() or " "
        embedding = await self.embed_text_async(text_to_embed)  # None on Railway
        stmt = select(Paper).where(Paper.pmid == paper.pmid)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        if existing:
            existing.title = paper.title or ""
            existing.abstract = paper.abstract or ""
            existing.authors = authors_list
            existing.year = str(paper.year) if paper.year is not None else None
            existing.journal = paper.journal or ""
            existing.doi = paper.doi
            existing.embedding = embedding  # None → NULL in DB
            if user_id is not None:
                existing.user_id = user_id
            if team_id is not None:
                existing.team_id = team_id
            await db.flush()
            await db.refresh(existing)
            return existing
        new_paper = Paper(
            pmid=paper.pmid,
            title=paper.title or "",
            abstract=paper.abstract or "",
            authors=authors_list,
            year=str(paper.year) if paper.year is not None else None,
            journal=paper.journal or "",
            doi=paper.doi,
            embedding=embedding,  # None → NULL in DB
            user_id=user_id,
            team_id=team_id,
        )
        db.add(new_paper)
        await db.flush()
        await db.refresh(new_paper)
        return new_paper

    async def find_similar(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> list[Paper]:
        """Return empty list (semantic search disabled on Railway)."""
        return []
