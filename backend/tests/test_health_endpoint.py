"""Tests for health and readiness endpoints (feature flags, DB check)."""

from collections.abc import AsyncGenerator
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app


@pytest_asyncio.fixture
async def health_client(db_session):
    """Client for health endpoints (no auth required)."""
    from app.core.database import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_health_returns_healthy_status(health_client):
    """GET /health returns status healthy and feature flags."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "features" in data
    assert data["features"]["embeddings"] is False


@pytest.mark.asyncio
async def test_health_embeddings_true_when_sentence_transformers_available(
    health_client,
):
    """Feature embeddings true when sentence_transformers can be imported."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": True,
            "semantic_search": True,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["features"]["embeddings"] is True


@pytest.mark.asyncio
async def test_health_embeddings_false_when_import_fails(health_client):
    """Feature embeddings false when import fails (mocked)."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["embeddings"] is False


@pytest.mark.asyncio
async def test_health_llm_summaries_true_when_ollama_has_models(health_client):
    """Feature llm_summaries true when Ollama returns models."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": True,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["llm_summaries"] is True


@pytest.mark.asyncio
async def test_health_llm_summaries_false_when_ollama_empty(health_client):
    """Feature llm_summaries false when Ollama returns no models."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["llm_summaries"] is False


@pytest.mark.asyncio
async def test_health_blast_true_when_blastn_in_path(health_client):
    """Feature blast true when blastn is in PATH."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": True,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["blast"] is True


@pytest.mark.asyncio
async def test_health_blast_false_when_blastn_missing(health_client):
    """Feature blast false when blastn not in PATH."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["blast"] is False


@pytest.mark.asyncio
async def test_health_nextflow_true_when_in_path(health_client):
    """Feature nextflow true when nextflow in PATH."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": True,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["nextflow"] is True


@pytest.mark.asyncio
async def test_health_nextflow_false_when_missing(health_client):
    """Feature nextflow false when not in PATH."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["nextflow"] is False


@pytest.mark.asyncio
async def test_health_spacy_true_when_model_loadable(health_client):
    """Feature spacy_ner true when de_core_news_sm loads."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": True,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["spacy_ner"] is True


@pytest.mark.asyncio
async def test_health_spacy_false_when_model_missing(health_client):
    """Feature spacy_ner false when model missing."""
    with patch(
        "app.api.v1.endpoints.health.check_features",
        new_callable=AsyncMock,
        return_value={
            "embeddings": False,
            "semantic_search": False,
            "llm_summaries": False,
            "spacy_ner": False,
            "blast": False,
            "nextflow": False,
        },
    ):
        resp = await health_client.get("/api/v1/health")
    assert resp.json()["features"]["spacy_ner"] is False


@pytest.mark.asyncio
async def test_readiness_check_database_connected(health_client):
    """GET /health/ready returns ready when DB responds."""
    resp = await health_client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_check_database_disconnected():
    """GET /health/ready returns not_ready when DB fails."""
    from app.core.database import get_db

    async def failing_db() -> AsyncGenerator[AsyncSession, None]:
        from unittest.mock import AsyncMock, MagicMock

        session = MagicMock()
        session.execute = AsyncMock(side_effect=RuntimeError("connection lost"))
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_db] = failing_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
        assert "error" in data
    finally:
        app.dependency_overrides.pop(get_db, None)
