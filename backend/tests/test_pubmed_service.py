"""Tests for PubMedService (NCBI E-utilities)."""

import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.schemas.pubmed import PubMedArticle
from app.services.pubmed_service import (
    PubMedService,
    PubMedServiceError,
    RateLimiter,
    _parse_article,
)

# --- Minimal PubMed XML for one article (efetch response) ---
SAMPLE_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">12345</PMID>
      <Article>
        <ArticleTitle>Test Article Title</ArticleTitle>
        <Abstract>
          <AbstractText>First part. </AbstractText>
          <AbstractText>Second part.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Doe</LastName><ForeName>John</ForeName></Author>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal><Title>Test Journal</Title></Journal>
        <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
        <ELocationID EIdType="doi">10.1234/test.2024</ELocationID>
        <KeywordList>
          <Keyword>cancer</Keyword>
          <Keyword>therapy</Keyword>
        </KeywordList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """HTTP client that does not perform real requests."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def pubmed_service(mock_httpx_client: AsyncMock) -> PubMedService:
    """PubMedService with mocked HTTP client."""
    return PubMedService(client=mock_httpx_client)


@pytest.mark.asyncio
async def test_search_pubmed_empty_query_returns_empty(
    pubmed_service: PubMedService,
) -> None:
    """Empty or whitespace query returns empty list without calling API."""
    result = await pubmed_service.search_pubmed("")
    assert result == []
    result = await pubmed_service.search_pubmed("   ")
    assert result == []
    pubmed_service._client.get.assert_not_called()


@pytest.mark.asyncio
async def test_search_pubmed_zero_max_results_returns_empty(
    pubmed_service: PubMedService,
) -> None:
    """max_results <= 0 returns empty list without calling API."""
    result = await pubmed_service.search_pubmed("cancer", max_results=0)
    assert result == []
    pubmed_service._client.get.assert_not_called()


@pytest.mark.asyncio
async def test_search_pubmed_esearch_returns_no_ids(
    pubmed_service: PubMedService,
) -> None:
    """When esearch returns no IDs, result is empty list."""
    response_esearch = MagicMock()
    response_esearch.json.return_value = {"esearchresult": {"idlist": []}}
    response_esearch.raise_for_status = MagicMock()

    pubmed_service._client.get = AsyncMock(return_value=response_esearch)

    result = await pubmed_service.search_pubmed("nonexistent_query_xyz", max_results=5)
    assert result == []
    assert pubmed_service._client.get.await_count == 1


@pytest.mark.asyncio
async def test_search_pubmed_success(
    pubmed_service: PubMedService,
) -> None:
    """search_pubmed returns list of PubMedArticle when esearch + efetch succeed."""
    response_esearch = MagicMock()
    response_esearch.json.return_value = {
        "esearchresult": {"idlist": ["12345"], "count": "1"},
    }
    response_esearch.raise_for_status = MagicMock()

    response_efetch = MagicMock()
    response_efetch.text = SAMPLE_EFETCH_XML
    response_efetch.raise_for_status = MagicMock()

    pubmed_service._client.get = AsyncMock(
        side_effect=[response_esearch, response_efetch],
    )

    result = await pubmed_service.search_pubmed("cancer", max_results=20)
    assert len(result) == 1
    art = result[0]
    assert art.pmid == "12345"
    assert "Test Article Title" in art.title
    assert "First part" in art.abstract and "Second part" in art.abstract
    assert art.authors == ["Doe John", "Smith J"]
    assert art.journal == "Test Journal"
    assert art.year == "2024"
    assert art.doi == "10.1234/test.2024"
    assert "cancer" in art.keywords and "therapy" in art.keywords

    assert pubmed_service._client.get.await_count == 2


@pytest.mark.asyncio
async def test_search_pubmed_http_error_raises(
    pubmed_service: PubMedService,
) -> None:
    """HTTP errors from NCBI raise PubMedServiceError."""
    pubmed_service._client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        ),
    )
    with pytest.raises(PubMedServiceError) as exc_info:
        await pubmed_service.search_pubmed("cancer", max_results=5)
    assert "NCBI" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_article_success(
    pubmed_service: PubMedService,
) -> None:
    """fetch_article returns single PubMedArticle for valid PMID."""
    response_efetch = MagicMock()
    response_efetch.text = SAMPLE_EFETCH_XML
    response_efetch.raise_for_status = MagicMock()
    pubmed_service._client.get = AsyncMock(return_value=response_efetch)

    result = await pubmed_service.fetch_article("12345")
    assert isinstance(result, PubMedArticle)
    assert result.pmid == "12345"
    assert result.title == "Test Article Title"


@pytest.mark.asyncio
async def test_fetch_article_empty_pmid_raises(
    pubmed_service: PubMedService,
) -> None:
    """Empty PMID raises PubMedServiceError."""
    with pytest.raises(PubMedServiceError) as exc_info:
        await pubmed_service.fetch_article("")
    assert "Empty PMID" in str(exc_info.value)

    with pytest.raises(PubMedServiceError):
        await pubmed_service.fetch_article("   ")
    pubmed_service._client.get.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_article_not_found_raises(
    pubmed_service: PubMedService,
) -> None:
    """Empty efetch result (no article) raises PubMedServiceError."""
    empty_xml = '<?xml version="1.0"?><PubmedArticleSet></PubmedArticleSet>'
    response = MagicMock()
    response.text = empty_xml
    response.raise_for_status = MagicMock()
    pubmed_service._client.get = AsyncMock(return_value=response)

    with pytest.raises(PubMedServiceError) as exc_info:
        await pubmed_service.fetch_article("99999999")
    assert "No article found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_article_request_error_raises(
    pubmed_service: PubMedService,
) -> None:
    """Network/request errors raise PubMedServiceError."""
    pubmed_service._client.get = AsyncMock(
        side_effect=httpx.RequestError("Connection failed"),
    )
    with pytest.raises(PubMedServiceError):
        await pubmed_service.fetch_article("12345")


def test_parse_article_minimal_xml() -> None:
    """_parse_article extracts fields from minimal PubmedArticle XML."""
    root = ET.fromstring(SAMPLE_EFETCH_XML)
    article_elem = root.find(".//PubmedArticle")  # type: ignore[union-attr]
    assert article_elem is not None
    art = _parse_article(article_elem)
    assert art.pmid == "12345"
    assert art.title == "Test Article Title"
    assert "First part" in art.abstract
    assert art.authors == ["Doe John", "Smith J"]
    assert art.journal == "Test Journal"
    assert art.year == "2024"
    assert art.doi == "10.1234/test.2024"
    assert set(art.keywords) == {"cancer", "therapy"}


def test_pubmed_article_schema() -> None:
    """PubMedArticle accepts required and optional fields."""
    a = PubMedArticle(
        pmid="123",
        title="T",
        abstract="A",
        authors=["A1"],
        journal="J",
        year="2024",
        doi="10.0/xyz",
        keywords=["k"],
    )
    assert a.pmid == "123"
    assert a.doi == "10.0/xyz"
    a_min = PubMedArticle(pmid="456")
    assert a_min.title == ""
    assert a_min.authors == []
    assert a_min.year is None
    assert a_min.doi is None


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests() -> None:
    """RateLimiter does not block when under limit."""
    limiter = RateLimiter()
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    # Should not raise; 4th would wait if we had strict timing
    await limiter.acquire()
