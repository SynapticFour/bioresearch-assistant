"""Extended tests for HPOService (search_terms, extract_from_text, API errors)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hpo_service import HPOService


@pytest.mark.asyncio
async def test_search_hpo_terms_success() -> None:
    """search_terms returns list when API returns terms."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "terms": [
            {
                "id": "HP:0001250",
                "name": "Seizure",
                "definition": "A seizure.",
                "synonyms": ["seizures"],
            },
        ],
    }
    with patch("app.services.hpo_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client_instance
        service = HPOService()
        result = await service.search_terms("seizure")
    assert len(result) == 1
    assert result[0]["id"] == "HP:0001250"
    assert result[0]["name"] == "Seizure"


@pytest.mark.asyncio
async def test_search_hpo_terms_empty_result() -> None:
    """search_terms returns empty list when API returns no terms."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"terms": []}
    with patch("app.services.hpo_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client_instance
        service = HPOService()
        result = await service.search_terms("xyznonexistent")
    assert result == []


@pytest.mark.asyncio
async def test_search_hpo_terms_api_error_returns_empty() -> None:
    """search_terms returns empty list on API error."""
    with patch("app.services.hpo_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=Exception("API error"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client_instance
        service = HPOService()
        result = await service.search_terms("seizure")
    assert result == []


@pytest.mark.asyncio
async def test_search_hpo_terms_timeout_returns_empty() -> None:
    """search_terms returns empty list on timeout."""
    import httpx

    with patch("app.services.hpo_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client_instance
        service = HPOService()
        result = await service.search_terms("seizure")
    assert result == []


@pytest.mark.asyncio
async def test_extract_keywords_clinical_text() -> None:
    """extract_from_text finds phenotypes in clinical text."""
    service = HPOService()
    result = await service.extract_from_text("Patient has fever and headache and chest pain.")
    assert len(result) >= 1
    names = [r["name"] for r in result]
    assert any("Fever" in n or "Headache" in n or "Chest" in n for n in names)


@pytest.mark.asyncio
async def test_extract_keywords_empty_text() -> None:
    """extract_from_text returns empty for empty string."""
    service = HPOService()
    result = await service.extract_from_text("")
    assert result == []


@pytest.mark.asyncio
async def test_extract_keywords_german_text() -> None:
    """extract_from_text finds German phenotype keywords."""
    service = HPOService()
    result = await service.extract_from_text(
        "Der Patient hat Fieber und Erschöpfung und Krampfanfälle."
    )
    assert len(result) >= 1
    hpo_ids = [r["hpo_id"] for r in result]
    assert "HP:0001945" in hpo_ids or "HP:0012378" in hpo_ids or "HP:0001250" in hpo_ids


@pytest.mark.asyncio
async def test_search_hpo_terms_non_200_returns_empty() -> None:
    """search_terms returns empty when API returns non-200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("app.services.hpo_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        MockClient.return_value = mock_client_instance
        service = HPOService()
        result = await service.search_terms("seizure")
    assert result == []
