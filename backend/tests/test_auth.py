"""Tests for auth endpoints (dev mode and status)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_status_returns_dev_mode(async_client: AsyncClient) -> None:
    """Without OIDC config, status returns development mode."""
    response = await async_client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "development"
    assert data["auth_enabled"] is False
    assert data["ga4gh_passport_support"] is True


@pytest.mark.asyncio
async def test_get_me_in_dev_mode(async_client: AsyncClient) -> None:
    """Without auth config, /me returns dev user."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["sub"] == "dev-user"
    assert "admin" in data.get("roles", [])


@pytest.mark.asyncio
async def test_pseudonymize_works_in_dev_mode(async_client: AsyncClient) -> None:
    """Pseudonymize endpoint works without Bearer token in dev mode."""
    response = await async_client.post(
        "/api/v1/pseudonymize",
        json={"text": "Patient Max Mustermann", "language": "de"},
    )
    assert response.status_code == 200
