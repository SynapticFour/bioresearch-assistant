"""Tests for library API: list, add, delete papers."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_papers_empty(async_client: AsyncClient) -> None:
    """GET /library/papers returns 200 and empty list when no papers."""
    response = await async_client.get("/api/v1/library/papers")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_add_paper_manually(async_client: AsyncClient) -> None:
    """POST /library/papers accepts manual paper and returns 201."""
    paper = {
        "pmid": "manual-001",
        "title": "Test Paper Titel",
        "abstract": "Dies ist ein Test Abstract.",
        "authors": ["Mustermann M"],
        "year": "2024",
        "journal": "Nature Genetics",
    }
    response = await async_client.post(
        "/api/v1/library/papers",
        json=paper,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["pmid"] == "manual-001"
    assert data["title"] == "Test Paper Titel"
    assert data["abstract"] == "Dies ist ein Test Abstract."


@pytest.mark.asyncio
async def test_delete_paper(async_client: AsyncClient) -> None:
    """Add a paper then delete it; DELETE returns 204."""
    paper = {
        "pmid": "delete-test-001",
        "title": "Zu löschendes Paper",
        "abstract": "Abstract.",
        "authors": ["Test A"],
        "year": "2024",
        "journal": "Test Journal",
    }
    await async_client.post("/api/v1/library/papers", json=paper)

    response = await async_client.delete("/api/v1/library/papers/delete-test-001")
    assert response.status_code == 204

    get_response = await async_client.get("/api/v1/library/papers")
    papers = get_response.json()
    pmids = [p["pmid"] for p in papers]
    assert "delete-test-001" not in pmids
