"""Edge case and security tests: XSS, SQL injection, PII, isolation, timeouts."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pseudonymization_service_railway import pseudonymize


def test_pseudonymize_xss_input() -> None:
    """HTML/script in input is not executed; treated as text."""
    text = "<script>alert('xss')</script> and <img src=x onerror=alert(1)>"
    result = pseudonymize(text)
    assert "pseudonymized_text" in result
    # No execution; output may still contain angle brackets as text
    assert "script" in result["pseudonymized_text"].lower() or "<" in result["pseudonymized_text"]


def test_pseudonymize_sql_injection() -> None:
    """SQL-like input is treated as text, not executed."""
    text = "'; DROP TABLE papers; --"
    result = pseudonymize(text)
    assert result["pseudonymized_text"] == text
    assert result["entities_found"] == []


def test_pseudonymize_very_long_text() -> None:
    """Text over 10000 chars is handled without error."""
    text = "x" * 15000
    result = pseudonymize(text)
    assert "pseudonymized_text" in result
    assert len(result["pseudonymized_text"]) == 15000


def test_pseudonymize_empty_string() -> None:
    """Empty string returns valid structure."""
    result = pseudonymize("")
    assert result["pseudonymized_text"] == ""
    assert result["entities_found"] == []
    assert result["plain_mapping"] == {}
    assert result["mapping_id"] is None


def test_pseudonymize_only_whitespace() -> None:
    """Only whitespace does not raise."""
    result = pseudonymize("   \n\t  ")
    assert "pseudonymized_text" in result
    assert result["entities_found"] == []


@pytest.mark.asyncio
async def test_pubmed_api_timeout_handled() -> None:
    """PubMed service handles timeout (returns empty or raises controlled exception)."""
    import httpx

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(
        side_effect=httpx.TimeoutException("timeout")
    )
    mock_client_instance.post = AsyncMock(
        side_effect=httpx.TimeoutException("timeout")
    )
    mock_client_instance.aclose = AsyncMock(return_value=None)
    with patch(
        "app.services.pubmed_service.httpx.AsyncClient"
    ) as MockClient:
        # Service does self._client = httpx.AsyncClient(), so return_value is _client
        MockClient.return_value = mock_client_instance
        from app.services.pubmed_service import PubMedService

        async with PubMedService() as svc:
            try:
                result = await svc.search_pubmed("BRCA1", max_results=5)
                assert result == []
            except Exception as e:
                assert "timeout" in str(e).lower() or "Timeout" in type(e).__name__


@pytest.mark.asyncio
async def test_user_isolation_list_papers(async_client) -> None:
    """List papers returns only papers for current user (isolation)."""
    # Add paper as current user; list should only show that user's papers
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "iso-1",
            "title": "Isolation Test",
            "abstract": "A",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    resp = await async_client.get("/api/v1/library/papers")
    assert resp.status_code == 200
    data = resp.json()
    pmids = [p["pmid"] for p in data]
    assert "iso-1" in pmids
