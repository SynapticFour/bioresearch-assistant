"""Tests for GAIA-X Self-Description and compliance endpoints."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_gaia_x_self_description_not_found_503(async_client):
    """GET /gaia-x/self-description returns 503 when file missing."""
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    with patch("app.api.v1.endpoints.gaia_x._SELF_DESCRIPTION_CANDIDATES", (mock_path,)):
        resp = await async_client.get("/api/v1/gaia-x/self-description")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_gaia_x_self_description_returns_200(async_client):
    """GET /api/v1/gaia-x/self-description returns 200 and JSON with ServiceOffering."""
    response = await async_client.get("/api/v1/gaia-x/self-description")
    assert response.status_code == 200
    data = response.json()
    assert "gx:ServiceOffering" in data


@pytest.mark.asyncio
async def test_gaia_x_compliance_shows_ready(async_client):
    """GET /api/v1/gaia-x/compliance returns gaia_x_ready and principles."""
    response = await async_client.get("/api/v1/gaia-x/compliance")
    assert response.status_code == 200
    data = response.json()
    assert data["gaia_x_ready"] is False
    assert data["gaia_x_certified"] is False
    assert data["principles"]["gdpr_alignment"] is True
    assert data["principles"]["data_sovereignty"] is True
