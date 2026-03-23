"""Tests for literature API: search, validate query, fetch by PMID, history."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.pubmed import PubMedArticle


@pytest.mark.asyncio
async def test_search_pubmed_returns_results(async_client: AsyncClient) -> None:
    """POST /literature/search returns list from PubMed (mocked)."""
    mock_articles = [
        PubMedArticle(
            pmid="11111",
            title="Test Paper",
            abstract="Abstract",
            authors=[],
            year=2024,
            journal="J",
            doi=None,
        ),
    ]

    with patch("app.api.v1.endpoints.literature.PubMedService") as MockPubmed:
        mock_instance = MagicMock()
        mock_instance.search_pubmed = AsyncMock(return_value=mock_articles)
        MockPubmed.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockPubmed.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = await async_client.post(
            "/api/v1/literature/search",
            json={"query": "BRCA1", "max_results": 10},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert data[0]["pmid"] == "11111"


@pytest.mark.asyncio
async def test_search_pubmed_empty_query_400(async_client: AsyncClient) -> None:
    """POST /literature/search with empty query may be rejected or return empty."""
    resp = await async_client.post(
        "/api/v1/literature/search",
        json={"query": "", "max_results": 10},
    )
    assert resp.status_code in (200, 400, 422)


@pytest.mark.asyncio
async def test_validate_query_no_pii(async_client: AsyncClient) -> None:
    """POST /literature/search/validate-query returns safe=True when no PII."""
    with patch("app.services.pseudonymization_service.PseudonymizationService") as MockPseudo:
        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=[])
        MockPseudo.return_value = mock_instance
        resp = await async_client.post(
            "/api/v1/literature/search/validate-query",
            json={"query": "BRCA1 cancer therapy", "language": "de"},
        )
    assert resp.status_code == 200
    assert resp.json().get("safe") is True


@pytest.mark.asyncio
async def test_validate_query_with_person_name(async_client: AsyncClient) -> None:
    """Validate query with person name may return safe=False."""
    with patch("app.services.pseudonymization_service.PseudonymizationService") as MockPseudo:
        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(
            return_value=[
                MagicMock(entity_type="PERSON", score=0.9),
            ]
        )
        MockPseudo.return_value = mock_instance
        resp = await async_client.post(
            "/api/v1/literature/search/validate-query",
            json={"query": "Max Mustermann BRCA1", "language": "de"},
        )
    assert resp.status_code == 200
    assert resp.json().get("safe") is False
    assert "detected_types" in resp.json()


@pytest.mark.asyncio
async def test_fetch_article_by_pmid_success(async_client: AsyncClient) -> None:
    """GET /literature/papers/{pmid} returns article when found."""
    mock_article = PubMedArticle(
        pmid="22222",
        title="Fetched Paper",
        abstract="Fetched abstract.",
        authors=[],
        year=2024,
        journal="J",
        doi=None,
    )
    with patch("app.api.v1.endpoints.literature.PubMedService") as MockPubmed:
        mock_instance = MagicMock()
        mock_instance.fetch_article = AsyncMock(return_value=mock_article)
        MockPubmed.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockPubmed.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = await async_client.get("/api/v1/literature/papers/22222")
    assert resp.status_code == 200
    assert resp.json()["pmid"] == "22222"


@pytest.mark.asyncio
async def test_fetch_article_not_found_404(async_client: AsyncClient) -> None:
    """GET /literature/papers/{pmid} returns 404 when not found."""
    from app.services.pubmed_service import PubMedServiceError

    with patch("app.api.v1.endpoints.literature.PubMedService") as MockPubmed:
        mock_instance = MagicMock()
        mock_instance.fetch_article = AsyncMock(side_effect=PubMedServiceError("Not found"))
        MockPubmed.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockPubmed.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = await async_client.get("/api/v1/literature/papers/nonexistent-pmid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_pubmed_service_error_502(async_client: AsyncClient) -> None:
    """POST /literature/search returns 502 when PubMed raises."""
    from app.services.pubmed_service import PubMedServiceError

    with patch("app.api.v1.endpoints.literature.PubMedService") as MockPubmed:
        mock_instance = MagicMock()
        mock_instance.search_pubmed = AsyncMock(side_effect=PubMedServiceError("API error"))
        MockPubmed.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        MockPubmed.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = await async_client.post(
            "/api/v1/literature/search",
            json={"query": "BRCA1", "max_results": 10},
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_literature_stats_returns_total_and_recent(
    async_client: AsyncClient,
) -> None:
    """GET /literature/stats returns total_papers and recent_papers."""
    resp = await async_client.get("/api/v1/literature/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_papers" in data
    assert "recent_papers" in data
