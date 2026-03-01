"""Tests for BLAST API endpoints: db-status, search, results."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.blast import BLASTParams, BLASTResults, BLASTStatistics
from app.schemas.wes import State


@pytest.mark.asyncio
async def test_blast_db_status_not_installed(async_client: AsyncClient) -> None:
    """GET /blast/db-status returns available: false when blastn not in PATH."""
    with patch("app.api.v1.endpoints.blast.shutil.which", return_value=None):
        resp = await async_client.get("/api/v1/blast/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert "BLAST" in data.get("reason", "")


@pytest.mark.asyncio
async def test_blast_db_status_available_when_blastdbcmd_ok(async_client: AsyncClient) -> None:
    """GET /blast/db-status returns available: true when blastdbcmd -info succeeds."""
    with patch("app.api.v1.endpoints.blast.shutil.which", return_value="/usr/bin/blastn"):
        with patch("app.api.v1.endpoints.blast.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="BLAST database info...")
            resp = await async_client.get("/api/v1/blast/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True


@pytest.mark.asyncio
async def test_blast_db_status_fallback_when_db_dir_exists(async_client: AsyncClient) -> None:
    """GET /blast/db-status returns available from db dir when blastdbcmd fails."""
    with patch("app.api.v1.endpoints.blast.shutil.which", return_value="/usr/bin/blastn"):
        with patch("app.api.v1.endpoints.blast.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            with patch("app.api.v1.endpoints.blast.os.path.exists") as mock_exists:
                mock_exists.return_value = True
                with patch("app.api.v1.endpoints.blast.os.listdir") as mock_listdir:
                    mock_listdir.return_value = ["nt.nsi", "nr.nsi"]
                    resp = await async_client.get("/api/v1/blast/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert "databases" in data


@pytest.mark.asyncio
async def test_blast_search_success(async_client: AsyncClient) -> None:
    """POST /blast/search returns 202 and run_id."""
    with patch("app.api.v1.endpoints.blast.run_blast_search", new_callable=AsyncMock, return_value="run-abc-123"):
        resp = await async_client.post(
            "/api/v1/blast/search",
            json={"query": "ATCGATCG", "database": "nt", "max_results": 10},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["run_id"] == "run-abc-123"


@pytest.mark.asyncio
async def test_blast_search_file_not_found_503(async_client: AsyncClient) -> None:
    """POST /blast/search returns 503 when workflow not available."""
    with patch("app.api.v1.endpoints.blast.run_blast_search", new_callable=AsyncMock, side_effect=FileNotFoundError("BLAST workflow not found")):
        resp = await async_client.post(
            "/api/v1/blast/search",
            json={"query": "ATCG", "database": "nt"},
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_blast_results_not_found_404(async_client: AsyncClient) -> None:
    """GET /blast/results/{run_id} returns 404 when run not found."""
    with patch("app.api.v1.endpoints.blast.get_blast_results", new_callable=AsyncMock, side_effect=ValueError("Run not found: xyz")):
        resp = await async_client.get("/api/v1/blast/results/xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_blast_results_file_not_found_404(async_client: AsyncClient) -> None:
    """GET /blast/results/{run_id} returns 404 when results file missing."""
    with patch("app.api.v1.endpoints.blast.get_blast_results", new_callable=AsyncMock, side_effect=FileNotFoundError("results.xml not found")):
        resp = await async_client.get("/api/v1/blast/results/run-1")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_blast_results_success_without_papers(async_client: AsyncClient) -> None:
    """GET /blast/results/{run_id} returns 200 with results, papers null when papers=false."""
    mock_results = BLASTResults(run_id="run-1", hits=[], statistics=BLASTStatistics())
    with patch("app.api.v1.endpoints.blast.get_blast_results", new_callable=AsyncMock, return_value=mock_results):
        resp = await async_client.get("/api/v1/blast/results/run-1")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["results"]["run_id"] == "run-1"
    assert data.get("papers") is None


@pytest.mark.asyncio
async def test_blast_results_value_error_400(async_client: AsyncClient) -> None:
    """GET /blast/results/{run_id} returns 400 for ValueError without 'not found'."""
    with patch("app.api.v1.endpoints.blast.get_blast_results", new_callable=AsyncMock, side_effect=ValueError("Run not complete")):
        resp = await async_client.get("/api/v1/blast/results/run-1")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_blast_results_with_papers_true(async_client: AsyncClient) -> None:
    """GET /blast/results/{run_id}?papers=true includes papers from find_papers_for_hits."""
    from app.models.paper import Paper

    mock_results = BLASTResults(run_id="run-1", hits=[], statistics=BLASTStatistics())
    mock_paper = Paper(pmid="123", title="T", abstract="A", authors=[], year="2024", journal="J", doi=None)
    with patch("app.api.v1.endpoints.blast.get_blast_results", new_callable=AsyncMock, return_value=mock_results):
        with patch("app.api.v1.endpoints.blast.find_papers_for_hits", new_callable=AsyncMock, return_value=[mock_paper]):
            resp = await async_client.get("/api/v1/blast/results/run-1?papers=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("papers") is not None
    assert len(data["papers"]) == 1
    assert data["papers"][0]["pmid"] == "123"
