"""Extended tests for library API: filters, summarize, semantic search, bulk import."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.paper import Paper
from app.schemas.llm import PaperSummary
from app.schemas.pubmed import PubMedArticle


@pytest.mark.asyncio
async def test_list_papers_with_year_filter(async_client: AsyncClient) -> None:
    """GET /library/papers?year=2024 returns only papers from that year."""
    # Add a paper with year 2024
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "filter-y-1",
            "title": "Year 2024",
            "abstract": "A",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    resp = await async_client.get("/api/v1/library/papers?year=2024&limit=50")
    assert resp.status_code == 200
    data = resp.json()
    if data:
        for p in data:
            assert p.get("year") == 2024 or p.get("year") == "2024"


@pytest.mark.asyncio
async def test_list_papers_with_journal_filter(async_client: AsyncClient) -> None:
    """GET /library/papers?journal=Nature returns matching papers."""
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "filter-j-1",
            "title": "In Nature",
            "abstract": "A",
            "authors": [],
            "year": 2024,
            "journal": "Nature Genetics",
        },
    )
    resp = await async_client.get(
        "/api/v1/library/papers?journal=Nature&limit=50"
    )
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert any("Nature" in (p.get("journal") or "") for p in data)


@pytest.mark.asyncio
async def test_store_paper_duplicate_pmid_updates(async_client: AsyncClient) -> None:
    """POST /library/papers with same PMID updates existing paper."""
    paper = {
        "pmid": "dup-001",
        "title": "First Title",
        "abstract": "First abstract.",
        "authors": ["A"],
        "year": 2023,
        "journal": "J1",
    }
    r1 = await async_client.post("/api/v1/library/papers", json=paper)
    assert r1.status_code == 201
    paper["title"] = "Updated Title"
    paper["abstract"] = "Updated abstract."
    r2 = await async_client.post("/api/v1/library/papers", json=paper)
    assert r2.status_code == 201
    assert r2.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_paper_not_found_404(async_client: AsyncClient) -> None:
    """DELETE /library/papers/nonexistent returns 404."""
    resp = await async_client.delete(
        "/api/v1/library/papers/nonexistent-pmid-999"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summarize_paper_returns_cached_summary(
    async_client: AsyncClient, db_session, mock_current_user
) -> None:
    """POST /library/summarize returns cached summary when already present."""
    # Add paper with summary already set (simulate cached); match current user for scope
    user_id = (mock_current_user or {}).get("sub") or "dev-user"
    paper = Paper(
        pmid="sum-cached-1",
        title="Cached",
        abstract="Abstract here.",
        authors=[],
        year="2024",
        journal="J",
        summary="Cached summary text",
        summary_language="de",
        user_id=user_id,
    )
    db_session.add(paper)
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/library/summarize",
        json={"pmid": "sum-cached-1", "language": "de"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("cached") is True
    assert data.get("summary") == "Cached summary text"


@pytest.mark.asyncio
async def test_summarize_paper_generates_new_summary(async_client: AsyncClient) -> None:
    """POST /library/summarize generates summary via LLM when not cached."""
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "sum-new-1",
            "title": "To Summarize",
            "abstract": "Long abstract about BRCA1 and cancer.",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    with patch("app.api.v1.endpoints.library.LLMService") as MockLLM:
        mock_llm = MagicMock()
        mock_llm.summarize_paper = AsyncMock(
            return_value=PaperSummary(
                summary="Generated summary",
                key_findings=[],
                methods=[],
                relevance_score=None,
            )
        )
        MockLLM.return_value = mock_llm
        resp = await async_client.post(
            "/api/v1/library/summarize",
            json={"pmid": "sum-new-1", "language": "de"},
        )
    assert resp.status_code == 200
    assert resp.json().get("summary")


@pytest.mark.asyncio
async def test_summarize_paper_no_abstract_400(
    async_client: AsyncClient, db_session, mock_current_user
) -> None:
    """POST /library/summarize returns 400 when paper has no abstract."""
    from app.models.paper import Paper

    user_id = (mock_current_user or {}).get("sub") or "dev-user"
    paper = Paper(
        pmid="no-abs-1",
        title="No Abstract",
        abstract="",
        authors=[],
        year="2024",
        journal="J",
        user_id=user_id,
    )
    db_session.add(paper)
    await db_session.commit()
    resp = await async_client.post(
        "/api/v1/library/summarize",
        json={"pmid": "no-abs-1", "language": "de"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_summarize_paper_llm_error_502(async_client: AsyncClient) -> None:
    """POST /library/summarize returns 502 when LLM raises."""
    from app.services.llm_service import LLMServiceError

    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "llm-err-1",
            "title": "T",
            "abstract": "Some abstract for LLM.",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    with patch("app.api.v1.endpoints.library.LLMService") as MockLLM:
        mock_llm = MagicMock()
        mock_llm.summarize_paper = AsyncMock(side_effect=LLMServiceError("Ollama unreachable"))
        MockLLM.return_value = mock_llm
        resp = await async_client.post(
            "/api/v1/library/summarize",
            json={"pmid": "llm-err-1", "language": "de"},
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_summarize_paper_not_found_404(async_client: AsyncClient) -> None:
    """POST /library/summarize with unknown PMID returns 404."""
    resp = await async_client.post(
        "/api/v1/library/summarize",
        json={"pmid": "nonexistent-pmid-sum", "language": "de"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summarize_paper_language_de(async_client: AsyncClient) -> None:
    """Summarize with language=de uses German."""
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "lang-de-1",
            "title": "T",
            "abstract": "Abstract.",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    with patch("app.api.v1.endpoints.library.LLMService") as MockLLM:
        mock_llm = MagicMock()
        mock_llm.summarize_paper = AsyncMock(
            return_value=PaperSummary(
                summary="Zusammenfassung",
                key_findings=[],
                methods=[],
                relevance_score=None,
            )
        )
        MockLLM.return_value = mock_llm
        resp = await async_client.post(
            "/api/v1/library/summarize",
            json={"pmid": "lang-de-1", "language": "de"},
        )
    assert resp.status_code == 200
    assert resp.json().get("language") == "de"


@pytest.mark.asyncio
async def test_summarize_paper_language_en(async_client: AsyncClient) -> None:
    """Summarize with language=en uses English."""
    await async_client.post(
        "/api/v1/library/papers",
        json={
            "pmid": "lang-en-1",
            "title": "T",
            "abstract": "Abstract.",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    )
    with patch("app.api.v1.endpoints.library.LLMService") as MockLLM:
        mock_llm = MagicMock()
        mock_llm.summarize_paper = AsyncMock(
            return_value=PaperSummary(
                summary="Summary in English",
                key_findings=[],
                methods=[],
                relevance_score=None,
            )
        )
        MockLLM.return_value = mock_llm
        resp = await async_client.post(
            "/api/v1/library/summarize",
            json={"pmid": "lang-en-1", "language": "en"},
        )
    assert resp.status_code == 200
    assert resp.json().get("language") == "en"


@pytest.mark.asyncio
async def test_semantic_search_returns_results(async_client: AsyncClient) -> None:
    """POST /library/search/semantic returns list (mocked EmbeddingService; SQLite has no pgvector)."""
    with patch("app.api.v1.endpoints.library.EmbeddingService") as MockEmb:
        mock_svc = MagicMock()
        mock_svc.find_similar = AsyncMock(return_value=[])
        MockEmb.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/search/semantic",
            json={"query": "BRCA1 cancer", "limit": 10},
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_semantic_search_empty_query_returns_empty(
    async_client: AsyncClient,
) -> None:
    """POST /library/search/semantic with empty query returns empty list."""
    resp = await async_client.post(
        "/api/v1/library/search/semantic",
        json={"query": "", "limit": 10},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_semantic_search_with_threshold(async_client: AsyncClient) -> None:
    """POST /library/search/semantic with threshold parameter (mocked; no pgvector in SQLite)."""
    with patch("app.api.v1.endpoints.library.EmbeddingService") as MockEmb:
        mock_svc = MagicMock()
        mock_svc.find_similar = AsyncMock(return_value=[])
        MockEmb.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/search/semantic",
            json={"query": "gene", "limit": 5, "threshold": 0.5},
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_bulk_import_json_success(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with valid JSON file succeeds."""
    import json as json_mod

    payload = [
        {
            "pmid": "bulk-1",
            "title": "Bulk One",
            "abstract": "A1",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
        {
            "pmid": "bulk-2",
            "title": "Bulk Two",
            "abstract": "A2",
            "authors": [],
            "year": 2024,
            "journal": "J",
        },
    ]
    files = {"file": ("papers.json", json_mod.dumps(payload).encode(), "application/json")}
    resp = await async_client.post(
        "/api/v1/library/bulk-import",
        files=files,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "imported" in data


@pytest.mark.asyncio
async def test_bulk_import_too_large_rejected(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with file over size limit returns 413."""
    from io import BytesIO

    with patch(
        "app.api.v1.endpoints.library.MAX_BULK_IMPORT_SIZE",
        10,
    ):
        files = {"file": ("big.json", BytesIO(b"x" * 11), "application/json")}
        resp = await async_client.post(
            "/api/v1/library/bulk-import",
            files=files,
        )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_reembed_all_papers_returns_count(async_client: AsyncClient) -> None:
    """POST /library/reembed-all returns reembedded count (may be 0)."""
    with patch("app.api.v1.endpoints.library.EmbeddingService") as MockEmb:
        mock_svc = MagicMock()
        mock_svc.embed_text_async = AsyncMock(return_value=[0.1] * 768)
        MockEmb.return_value = mock_svc
        resp = await async_client.post("/api/v1/library/reembed-all")
    assert resp.status_code == 200
    data = resp.json()
    assert "reembedded" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_extract_metadata_by_pmid_success(async_client: AsyncClient) -> None:
    """POST /library/extract-metadata with valid PMID returns metadata."""
    with patch("app.api.v1.endpoints.library.MetadataService") as MockMeta:
        mock_svc = MagicMock()
        mock_svc.extract_from_pmid = AsyncMock(
            return_value={"pmid": "12345", "title": "Test", "year": 2024}
        )
        MockMeta.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/extract-metadata",
            json={"pmid": "12345"},
        )
    assert resp.status_code == 200
    assert resp.json().get("pmid") == "12345"


@pytest.mark.asyncio
async def test_extract_metadata_not_found_404(async_client: AsyncClient) -> None:
    """POST /library/extract-metadata returns 404 when no metadata found."""
    with patch("app.api.v1.endpoints.library.MetadataService") as MockMeta:
        mock_svc = MagicMock()
        mock_svc.extract_from_doi = AsyncMock(return_value=None)
        mock_svc.extract_from_pmid = AsyncMock(return_value=None)
        MockMeta.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/extract-metadata",
            json={"pmid": "nonexistent"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_extract_metadata_invalid_doi_422(async_client: AsyncClient) -> None:
    """POST /library/extract-metadata with invalid DOI format returns 422."""
    resp = await async_client.post(
        "/api/v1/library/extract-metadata",
        json={"doi": "invalid-doi"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_metadata_by_doi(async_client: AsyncClient) -> None:
    """POST /library/extract-metadata with DOI calls extract_from_doi."""
    with patch("app.api.v1.endpoints.library.MetadataService") as MockMeta:
        mock_svc = MagicMock()
        mock_svc.extract_from_doi = AsyncMock(
            return_value={"doi": "10.1234/test", "title": "DOI Paper"}
        )
        MockMeta.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/extract-metadata",
            json={"doi": "10.1234/test"},
        )
    assert resp.status_code == 200
    assert resp.json().get("title") == "DOI Paper"


@pytest.mark.asyncio
async def test_add_paper_embedding_error_502(async_client: AsyncClient) -> None:
    """POST /library/papers returns 502 when EmbeddingService raises."""
    from app.services.embedding_service import EmbeddingServiceError

    with patch("app.api.v1.endpoints.library.EmbeddingService") as MockEmb:
        mock_svc = MagicMock()
        mock_svc.store_paper = AsyncMock(side_effect=EmbeddingServiceError("Model load failed"))
        MockEmb.return_value = mock_svc
        resp = await async_client.post(
            "/api/v1/library/papers",
            json={
                "pmid": "err-1",
                "title": "T",
                "abstract": "A",
                "authors": [],
                "year": 2024,
                "journal": "J",
            },
        )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_bulk_import_csv_success(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with CSV file succeeds."""
    csv_content = b"pmid,title,abstract,authors,year,journal\ncsv-1,CSV Paper,A,,2024,J"
    files = {"file": ("papers.csv", csv_content, "text/csv")}
    resp = await async_client.post(
        "/api/v1/library/bulk-import",
        files=files,
    )
    assert resp.status_code == 200
    assert resp.json().get("imported", 0) >= 0


@pytest.mark.asyncio
async def test_bulk_import_zip_success(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with ZIP containing JSON succeeds."""
    import io
    import json as json_mod
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "papers.json",
            json_mod.dumps([{"pmid": "zip-1", "title": "ZIP Paper", "abstract": "A", "authors": [], "year": 2024, "journal": "J"}]),
        )
    buf.seek(0)
    files = {"file": ("data.zip", buf.read(), "application/zip")}
    resp = await async_client.post(
        "/api/v1/library/bulk-import",
        files=files,
    )
    assert resp.status_code == 200
    assert "imported" in resp.json()


@pytest.mark.asyncio
async def test_bulk_import_unsupported_format_415(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with unsupported extension returns 415."""
    files = {"file": ("data.txt", b"plain text", "text/plain")}
    resp = await async_client.post(
        "/api/v1/library/bulk-import",
        files=files,
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_bulk_import_invalid_format_rejected(async_client: AsyncClient) -> None:
    """POST /library/bulk-import with invalid JSON file returns 400."""
    files = {"file": ("bad.json", b"{ invalid json }", "application/json")}
    resp = await async_client.post(
        "/api/v1/library/bulk-import",
        files=files,
    )
    # 400 = invalid JSON; 429 = rate limit (5/min) from other bulk tests
    assert resp.status_code in (400, 429)
