"""API tests for pseudonymization endpoints."""

from httpx import AsyncClient


async def test_pseudonymize_returns_200_and_placeholders(
    async_client: AsyncClient,
) -> None:
    """POST /api/v1/pseudonymize returns 200 and pseudonymized text."""
    response = await async_client.post(
        "/api/v1/pseudonymize",
        json={"text": "Patient Max Mustermann, ID: P-12345", "language": "de"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "pseudonymized_text" in data
    assert (
        "MAX" not in data["pseudonymized_text"].upper()
        or "MUSTERMANN" not in data["pseudonymized_text"].upper()
    )


async def test_restore_without_api_key_returns_403(async_client: AsyncClient) -> None:
    """POST /api/v1/pseudonymize/restore without X-Restore-API-Key returns 403 or 503."""
    response = await async_client.post(
        "/api/v1/pseudonymize/restore",
        json={"pseudonymized_text": "<PERSON_1>", "mapping_id": "abc"},
    )
    assert response.status_code in (403, 503)


async def test_audit_log_returns_list(async_client: AsyncClient) -> None:
    """GET /api/v1/pseudonymize/audit-log returns list."""
    response = await async_client.get("/api/v1/pseudonymize/audit-log")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
