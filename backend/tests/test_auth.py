"""Tests for auth endpoints and GA4GH Passport (dev mode and production)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user

# ─── Auth Status Tests ──


@pytest.mark.asyncio
async def test_auth_status_dev_mode(async_client: AsyncClient) -> None:
    """Auth Status im Dev-Modus."""
    response = await async_client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["auth_enabled"] is False
    assert data["mode"] == "development"
    assert data["ga4gh_passport_support"] is True
    assert "Keycloak" in data["supported_providers"]
    assert "ELIXIR AAI" in " ".join(data["supported_providers"])
    assert "ga4gh-infra AAI broker" in data["supported_providers"]
    assert data["issues_passports"] is False


@pytest.mark.asyncio
async def test_get_me_dev_mode(async_client: AsyncClient) -> None:
    """GET /auth/me im Dev-Modus gibt dev-user zurück."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["sub"] == "dev-user"
    assert data["email"] == "contact@synapticfour.com"
    assert "admin" in data["roles"]


@pytest.mark.asyncio
async def test_get_me_with_valid_token(async_client: AsyncClient) -> None:
    """GET /auth/me mit gültigem Token (mock)."""
    mock_user = {
        "sub": "user-123",
        "email": "forscher@ukhd.de",
        "name": "Dr. Schmidt",
        "roles": ["researcher"],
        "passports": [],
        "visas": [],
    }

    async def override_get_current_user() -> dict:
        return mock_user

    from app.main import app

    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        assert response.json()["sub"] == "user-123"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_me_invalid_token_401(unauthed_client: AsyncClient) -> None:
    """GET /auth/me mit ungültigem Token → 401 (wenn Auth aktiv)."""
    with patch("app.core.auth.get_settings") as mock_get_settings:
        mock_get_settings.return_value = MagicMock(auth_enabled=True)
        with patch(
            "app.core.auth.AuthService.extract_ga4gh_passports",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid token"),
        ):
            response = await unauthed_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"},
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_no_token_when_auth_enabled_401(
    unauthed_client: AsyncClient,
) -> None:
    """GET /auth/me ohne Token wenn Auth aktiv → 401."""
    with patch("app.core.auth.get_settings") as mock_get_settings:
        mock_get_settings.return_value = MagicMock(auth_enabled=True)
        response = await unauthed_client.get("/api/v1/auth/me")
        assert response.status_code == 401


# ─── GA4GH Passport Tests ──


@pytest.mark.asyncio
async def test_passport_extraction() -> None:
    """GA4GH Passport Visas werden korrekt extrahiert."""
    from app.services.auth_service import AuthService

    service = AuthService()
    mock_claims = {
        "sub": "user-123",
        "email": "forscher@ukhd.de",
        "name": "Dr. Schmidt",
        "ga4gh_passport_v1": ["visa1", "visa2"],
        "ga4gh_visa_v1": {
            "type": "ResearcherStatus",
            "value": "https://doi.org/10.1038/s41431-018-0219-y",
        },
        "roles": ["researcher"],
    }

    with patch.object(
        service,
        "verify_token",
        new_callable=AsyncMock,
        return_value=mock_claims,
    ):
        result = await service.extract_ga4gh_passports("mock-token")
        assert result["sub"] == "user-123"
        assert len(result["passports"]) == 2
        assert result["visas"][0]["type"] == "ResearcherStatus"


@pytest.mark.asyncio
async def test_nested_visa_jwt_is_verified() -> None:
    """ga4gh_passport_v1 visa JWTs are signature-checked, not copied as strings."""
    from app.services.auth_service import AuthService

    service = AuthService()
    visa_obj = {
        "type": "AffiliationAndRole",
        "value": "faculty@ukhd.de",
    }
    with (
        patch.object(
            service,
            "verify_token",
            new_callable=AsyncMock,
            return_value={
                "sub": "user-123",
                "ga4gh_passport_v1": ["aaa.bbb.ccc"],
            },
        ),
        patch.object(
            service,
            "verify_visa_jwt",
            new_callable=AsyncMock,
            return_value=visa_obj,
        ),
    ):
        result = await service.extract_ga4gh_passports("mock-token")
        assert result["visas"] == [visa_obj]


@pytest.mark.asyncio
async def test_nested_visa_jwt_dropped_on_verify_failure() -> None:
    from app.services.auth_service import AuthService

    service = AuthService()
    with (
        patch.object(
            service,
            "verify_token",
            new_callable=AsyncMock,
            return_value={
                "sub": "user-123",
                "ga4gh_passport_v1": ["not-a.jwt.token"],
            },
        ),
        patch.object(
            service,
            "verify_visa_jwt",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        result = await service.extract_ga4gh_passports("mock-token")
        assert result["visas"] == []


# ─── Protected Endpoint Tests ──


@pytest.mark.asyncio
async def test_pseudonymize_works_in_dev_mode(async_client: AsyncClient) -> None:
    """Pseudonymisierung funktioniert ohne Auth im Dev-Modus."""
    response = await async_client.post(
        "/api/v1/pseudonymize",
        json={"text": "Patient Max Mustermann", "language": "de"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_literature_search_works_in_dev_mode(
    async_client: AsyncClient,
) -> None:
    """Literature Search funktioniert ohne Auth im Dev-Modus."""
    with patch("app.api.v1.endpoints.literature.PubMedService") as mock_pubmed_class:
        mock_instance = MagicMock()
        mock_instance.search_pubmed = AsyncMock(return_value=[])
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_pubmed_class.return_value = mock_instance
        response = await async_client.post(
            "/api/v1/literature/search",
            json={"query": "BRCA1", "max_results": 5},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_wes_service_info_works_in_dev_mode(
    async_client: AsyncClient,
) -> None:
    """WES Service Info funktioniert ohne Auth im Dev-Modus."""
    response = await async_client.get("/ga4gh/wes/v1/service-info")
    assert response.status_code == 200


# ─── Auth Service Unit Tests ──


@pytest.mark.asyncio
async def test_auth_service_get_jwks() -> None:
    """JWKS werden korrekt abgerufen."""
    from app.services.auth_service import AuthService

    service = AuthService()
    mock_config = {"jwks_uri": "https://example.com/.well-known/jwks.json"}
    mock_jwks = {"keys": [{"kty": "RSA", "kid": "key1"}]}

    with patch.object(
        service,
        "get_oidc_config",
        new_callable=AsyncMock,
        return_value=mock_config,
    ):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_jwks
            mock_response.raise_for_status = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_client = MagicMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            jwks = await service.get_jwks()
            assert jwks == mock_jwks
