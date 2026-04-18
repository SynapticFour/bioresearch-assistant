"""Locus (curated RAG) API tests."""

import math
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.locus_chunk import LocusChunk
from app.schemas.locus import LocusRAGResponse
from app.services.llm_service import LLMServiceError
from app.services.locus_service import LocusService


def _unit(dim: int = 768) -> list[float]:
    v = [1.0 / math.sqrt(dim)] * dim
    return v


@pytest.mark.asyncio
async def test_locus_rag_403_when_disabled(db_session, mock_current_user):
    from app.core.auth import get_current_user

    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/locus/rag",
                json={"question": "What is a workflow execution service?"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_locus_rag_200_with_mocked_service(db_session, mock_current_user):
    from app.core.auth import get_current_user

    body = LocusRAGResponse(
        answer="Demo",
        sources=[],
        question="Q",
        model_used="m",
        context_chunks=0,
    )

    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        with (
            patch("app.api.v1.endpoints.locus.get_settings") as gs,
            patch("app.api.v1.endpoints.locus.LocusService") as Svc,
        ):
            m = gs.return_value
            m.locus_enabled = True
            m.llm_claude_model = "c"
            m.ollama_model = "m"
            m.anthropic_api_key = None
            Svc.return_value.answer = AsyncMock(return_value=body)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(
                    "/api/v1/locus/rag",
                    json={"question": "What is a WES?"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["answer"] == "Demo"


@pytest.mark.asyncio
async def test_locus_status_disabled(db_session):
    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/v1/locus/status")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    data = r.json()
    assert data["locus_enabled"] is False
    assert data["chunk_count"] == 0


@pytest.mark.asyncio
async def test_locus_service_sqlite_finds_nearest(db_session, monkeypatch):
    monkeypatch.setenv("LOCUS_ENABLED", "1")
    u = _unit(768)
    ch = LocusChunk(
        corpus_id="t",
        source_ref="ref1",
        title="T1",
        content="alpha beta gamma",
        meta={},
        embedding=u,
    )
    db_session.add(ch)
    await db_session.commit()

    svc = LocusService()
    mock_embed = MagicMock()
    mock_embed.embed_text_async = AsyncMock(return_value=u)
    with patch.object(svc, "_embed", mock_embed):
        out = await svc.find_chunks(
            db_session,
            "irrelevant query for sqlite fallback",
            top_k=3,
            threshold=2.0,
            corpus_ids=None,
        )
    assert len(out) == 1
    assert out[0].title == "T1"


@pytest.mark.asyncio
async def test_locus_rag_404_no_chunks(db_session, mock_current_user):
    from app.core.auth import get_current_user

    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        with (
            patch("app.api.v1.endpoints.locus.get_settings") as gs,
            patch("app.api.v1.endpoints.locus.LocusService") as Svc,
        ):
            gs.return_value.locus_enabled = True
            Svc.return_value.answer = AsyncMock(
                side_effect=ValueError(
                    "Keine Locus-Index-Texte passend zu dieser Frage. Füllen zuerst."
                )
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/locus/rag",
                    json={"question": "Explain something that is not in the index?"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_locus_rag_502_llm_error(db_session, mock_current_user):
    from app.core.auth import get_current_user

    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        with (
            patch("app.api.v1.endpoints.locus.get_settings") as gs,
            patch("app.api.v1.endpoints.locus.LocusService") as Svc,
        ):
            gs.return_value.locus_enabled = True
            Svc.return_value.answer = AsyncMock(side_effect=LLMServiceError("ollama down"))
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/locus/rag",
                    json={"question": "Pathogenic vs VUS in general?"},
                )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 502
    assert "LLM" in r.json()["detail"] or "llm" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_locus_status_enabled_shows_count(db_session):
    u = _unit(768)
    db_session.add(
        LocusChunk(
            corpus_id="guidelines",
            source_ref="demo/1",
            title="G",
            content="C",
            meta={},
            embedding=u,
        )
    )
    await db_session.commit()

    async def _db() -> AsyncGenerator[Any, None]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    try:
        with patch("app.api.v1.endpoints.locus.get_settings") as gs:
            gs.return_value.locus_enabled = True
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/v1/locus/status")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    d = r.json()
    assert d["locus_enabled"] is True
    assert d["chunk_count"] == 1
    assert "guidelines" in d.get("corpora", [])
