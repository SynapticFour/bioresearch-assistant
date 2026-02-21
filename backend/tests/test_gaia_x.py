"""Tests for GAIA-X Self-Description and compliance endpoints."""

import pytest


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
    assert data["gaia_x_ready"] is True
    assert data["principles"]["gdpr_compliant"] is True
    assert data["principles"]["data_sovereignty"] is True
