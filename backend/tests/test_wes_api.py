"""Tests for GA4GH WES v1.1 API endpoints."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def test_wes_list_runs_invalid_state_returns_400(async_client: AsyncClient) -> None:
    """GET /runs?state=invalid returns 400."""
    response = await async_client.get("/ga4gh/wes/v1/runs?state=NOT_A_REAL_STATE")
    assert response.status_code == 400


async def test_wes_service_info_returns_200(async_client: AsyncClient) -> None:
    """GET /ga4gh/wes/v1/service-info returns 200 and ServiceInfo fields."""
    response = await async_client.get("/ga4gh/wes/v1/service-info")
    assert response.status_code == 200
    data = response.json()
    assert data.get("id") == "org.ga4gh.bioresearch.wes"
    # GA4GH official ServiceInfo JSON Schema: these must be strings, not null
    for key in (
        "contactUrl",
        "createdAt",
        "documentationUrl",
        "environment",
        "updatedAt",
    ):
        assert isinstance(data.get(key), str), f"{key} must be string for GA4GH schema"
    assert "supported_wes_versions" in data
    assert "1.1.0" in data["supported_wes_versions"]
    assert "1.1" in data["supported_wes_versions"]
    assert "workflow_type_versions" in data
    assert "system_state_counts" in data


async def test_wes_list_runs_returns_200(async_client: AsyncClient) -> None:
    """GET /ga4gh/wes/v1/runs returns 200 and runs array."""
    response = await async_client.get("/ga4gh/wes/v1/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert "next_page_token" in data
    assert isinstance(data["runs"], list)


async def test_wes_get_run_status_404(async_client: AsyncClient) -> None:
    """GET /ga4gh/wes/v1/runs/{run_id}/status returns 404 for unknown run_id."""
    response = await async_client.get("/ga4gh/wes/v1/runs/nonexistent-id/status")
    assert response.status_code == 404


async def test_wes_get_run_log_404(async_client: AsyncClient) -> None:
    """GET /ga4gh/wes/v1/runs/{run_id} returns 404 for unknown run_id."""
    response = await async_client.get("/ga4gh/wes/v1/runs/nonexistent-id")
    assert response.status_code == 404


async def test_wes_cancel_run_404(async_client: AsyncClient) -> None:
    """POST /ga4gh/wes/v1/runs/{run_id}/cancel returns 404 for unknown run_id."""
    response = await async_client.post("/ga4gh/wes/v1/runs/nonexistent-id/cancel")
    assert response.status_code == 404


async def test_wes_run_workflow_returns_run_id(async_client: AsyncClient) -> None:
    """POST /ga4gh/wes/v1/runs returns 200/201 and run_id."""
    with patch(
        "app.services.wes_service._execute_nextflow",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.post(
            "/ga4gh/wes/v1/runs",
            data={
                "workflow_url": "main.nf",
                "workflow_type": "NEXTFLOW",
                "workflow_type_version": "DSL2",
                "workflow_params": "{}",
            },
        )
    assert response.status_code in (200, 201)
    assert "run_id" in response.json()


async def test_wes_post_runs_accepts_application_json(async_client: AsyncClient) -> None:
    """POST /ga4gh/wes/v1/runs accepts application/json RunRequest (GA4GH / HelixTest style)."""
    with patch(
        "app.services.wes_service._execute_nextflow",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.post(
            "/ga4gh/wes/v1/runs",
            json={
                "workflow_url": "main.nf",
                "workflow_type": "NEXTFLOW",
                "workflow_type_version": "DSL2",
                "workflow_params": {},
            },
        )
    assert response.status_code in (200, 201)
    assert "run_id" in response.json()


async def test_wes_post_runs_rejects_remote_url_by_default(async_client: AsyncClient) -> None:
    """POST /runs with an https workflow_url is rejected unless remote workflows are enabled."""
    response = await async_client.post(
        "/ga4gh/wes/v1/runs",
        json={
            "workflow_url": "https://example.org/workflows/pipeline.nf",
            "workflow_type": "NEXTFLOW",
            "workflow_type_version": "DSL2",
            "workflow_params": {},
        },
    )
    assert response.status_code == 400
