#!/usr/bin/env python3
"""Optional demo rows for the Locus curated index (run after `alembic upgrade head`).

  cd backend && python scripts/seed_locus_demo.py

Requires sentence-transformers (same as the rest of BRA). Set LOCUS_ENABLED=1 to expose /locus/rag.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PSEUDONYMIZATION_ENCRYPTION_KEY", "a" * 64)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.models.locus_chunk import LocusChunk
from app.services.embedding_service import EmbeddingService

DEMO: list[dict] = [
    {
        "corpus_id": "ga4gh_concepts",
        "source_ref": "academic/ga4gh-terminology-demo",
        "title": "GA4GH: DRS and WES (summary)",
        "content": (
            "The GA4GH Data Repository Service (DRS) provides HTTP access to data by stable id. "
            "WES runs workflows. This is synthetic demo text for RAG tests only."
        ),
    },
    {
        "corpus_id": "mii_kds",
        "source_ref": "internal/mii-kds-terminology-demo",
        "title": "MII KDS: Forschung und Interoperabilität (Demo-Text)",
        "content": (
            "Der MII Kerndatensatz bündelt strukturierte klinische Informationen, oft in FHIR. "
            "Dieser Text ist bewusst allgemein gehalten; nutzen Sie verbindliche Quellen in Ihrem Hause."
        ),
    },
]


async def run() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    embed = EmbeddingService()
    async with factory() as session:
        for row in DEMO:
            text = f"{row['title']}\n{row['content']}"[:8000]
            vector = embed.embed_text(text)
            st = select(LocusChunk).where(
                LocusChunk.corpus_id == row["corpus_id"],
                LocusChunk.source_ref == row["source_ref"],
            )
            r = await session.execute(st)
            ex = r.scalars().first()
            if ex:
                ex.title = row["title"]
                ex.content = row["content"]
                ex.embedding = vector
                ex.meta = {"kind": "demo-seed", "v": 1}
            else:
                session.add(
                    LocusChunk(
                        corpus_id=row["corpus_id"],
                        source_ref=row["source_ref"],
                        title=row["title"],
                        content=row["content"],
                        meta={"kind": "demo-seed", "v": 1},
                        embedding=vector,
                    )
                )
        await session.commit()
    await engine.dispose()
    print(
        f"Seeded {len(DEMO)} Locus chunks. Set LOCUS_ENABLED=1, restart API, then POST /api/v1/locus/rag"
    )


if __name__ == "__main__":
    asyncio.run(run())
