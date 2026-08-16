"""M2: Microsoft Entra claims-map. BRA consumes groups; it does not issue Passports."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.claims_map import apply_profile_claims, detect_profile, profile_by_name


def test_detect_profile_entra_from_issuer() -> None:
    profile = detect_profile(
        "https://login.microsoftonline.com/11111111-2222-3333-4444-555555555555/v2.0",
        "auto",
    )
    assert profile.name == "entra"
    assert "ga4gh_passport_v1" not in profile.login_scope.split()


def test_detect_profile_ls_login_and_broker() -> None:
    assert detect_profile("https://login.elixir-czech.org/oidc", "auto").name == "ls-login"
    assert detect_profile("http://127.0.0.1:8180", "auto").name == "broker"
    assert detect_profile("https://idp.example/realms/bra", "auto").name == "keycloak"
    assert profile_by_name("unknown").name == "keycloak"
    assert profile_by_name("auto").name == "keycloak"
    profile = detect_profile("https://keycloak.example/realms/bra", "entra")
    assert profile.name == "entra"


def test_entra_login_scope_has_no_passport() -> None:
    profile = profile_by_name("entra")
    assert profile.login_scope == "openid email profile"
    assert "ga4gh_passport_v1" not in profile.login_scope


def test_keycloak_and_ls_login_still_request_passports() -> None:
    assert "ga4gh_passport_v1" in profile_by_name("keycloak").login_scope.split()
    assert "ga4gh_passport_v1" in profile_by_name("ls-login").login_scope.split()


def test_apply_entra_groups_and_tid() -> None:
    profile = profile_by_name("entra")
    mapped = apply_profile_claims(
        {
            "sub": "entra-user",
            "preferred_username": "forscher@ukhd.de",
            "tid": "tenant-ukhd",
            "groups": ["UKHD-Forschung", "BRA-Users"],
        },
        profile,
    )
    assert mapped["email"] == "forscher@ukhd.de"
    assert mapped["organization"] == "tenant-ukhd"
    assert mapped["groups"] == ["UKHD-Forschung", "BRA-Users"]
    assert mapped["idp_profile"] == "entra"


def test_extract_groups_from_string_claim() -> None:
    mapped = apply_profile_claims(
        {"groups": "lab-a", "email": "a@example.org"},
        profile_by_name("keycloak"),
    )
    assert mapped["groups"] == ["lab-a"]


@pytest.mark.asyncio
async def test_extract_passports_attaches_entra_groups_without_minting() -> None:
    from app.services.auth_service import AuthService

    service = AuthService()
    claims = {
        "sub": "entra-user",
        "preferred_username": "forscher@ukhd.de",
        "tid": "tenant-ukhd",
        "groups": ["UKHD-Forschung"],
        "name": "Dr. Schmidt",
    }
    with (
        patch("app.services.auth_service.detect_profile", return_value=profile_by_name("entra")),
        patch.object(service, "verify_token", new_callable=AsyncMock, return_value=claims),
    ):
        result = await service.extract_ga4gh_passports("mock-token")
    assert result["groups"] == ["UKHD-Forschung"]
    assert result["idp_profile"] == "entra"
    assert result["visas"] == []
    assert result["passports"] == []
    assert result["email"] == "forscher@ukhd.de"
    assert result["organization"] == "tenant-ukhd"


@pytest.mark.asyncio
async def test_auth_status_never_issues_passports(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["issues_passports"] is False
    assert data["oidc_profile"] == "auto"
    assert "Microsoft Entra" in data["supported_providers"]


@pytest.mark.asyncio
async def test_logout_returns_json_cookie_clear(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    body = response.json()
    assert "idp_logout_url" in body
    assert body["idp_logout_url"] is None


@pytest.mark.asyncio
async def test_logout_builds_rp_initiated_url() -> None:
    from app.api.v1.endpoints import auth as auth_ep

    discovery = {
        "end_session_endpoint": "https://login.microsoftonline.com/t/oauth2/v2.0/logout",
    }
    mock_settings = MagicMock(
        auth_enabled=True,
        oidc_issuer="https://login.microsoftonline.com/t/v2.0",
        oidc_client_id="bra-client",
        frontend_base_url="https://bra.ukhd.example",
        session_cookie_name="bra_access_token",
        allows_unauthenticated_dev=False,
    )
    mock_response = MagicMock()
    mock_response.json.return_value = discovery
    mock_response.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.get = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=None)

    request = MagicMock()
    request.cookies = {"bra_id_token": "id.token.hint"}

    with (
        patch("app.api.v1.endpoints.auth.get_settings", return_value=mock_settings),
        patch("httpx.AsyncClient", return_value=mock_http),
    ):
        result = await auth_ep.logout(request)

    payload = result.body
    assert b"login.microsoftonline.com" in payload
    assert b"id_token_hint" in payload
    assert b"post_logout_redirect_uri" in payload
