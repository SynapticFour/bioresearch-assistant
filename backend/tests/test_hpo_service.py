"""Tests for HPOService (keyword extraction)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.hpo_service import HPOService


@pytest.mark.asyncio
async def test_hpo_empty_text() -> None:
    """Leerer Text gibt leere Liste zurück."""
    service = HPOService()
    result = await service.extract_from_text("")
    assert result == []


@pytest.mark.asyncio
async def test_hpo_no_matches() -> None:
    """Text ohne bekannte Phänotypen."""
    service = HPOService()
    result = await service.extract_from_text("Das Wetter ist schön heute")
    assert result == []


@pytest.mark.asyncio
async def test_hpo_keyword_extraction() -> None:
    """extract_from_text finds keywords and returns HPO IDs."""
    service = HPOService()
    text = "Patient zeigt Krampfanfälle und Tumor"
    results = await service.extract_from_text(text)
    assert len(results) > 0
    hpo_ids = [r["hpo_id"] for r in results]
    assert "HP:0001250" in hpo_ids  # Seizures
    assert "HP:0002664" in hpo_ids  # Tumor


@pytest.mark.asyncio
async def test_hpo_search_mocked(async_client) -> None:
    """HPO search endpoint returns mocked results."""

    with patch(
        "app.api.v1.endpoints.phenopackets.HPOService.search_terms",
        new_callable=AsyncMock,
        return_value=[
            {"id": "HP:0001250", "name": "Seizures", "definition": "Test"},
        ],
    ):
        resp = await async_client.get(
            "/api/v1/phenopackets/hpo/search",
            params={"q": "seizure"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["id"] == "HP:0001250"
