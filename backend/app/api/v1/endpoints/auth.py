"""OIDC/OAuth2 and GA4GH Passport auth endpoints."""

import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.auth import get_auth_service, get_current_user
from app.core.config import get_settings
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
async def login(
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Redirect zu OIDC Provider Login."""
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured (development mode)",
        )
    config = await auth_service.get_oidc_config()
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": "openid email profile ga4gh_passport_v1",
    }
    auth_url = config["authorization_endpoint"]
    query = urlencode(params)
    return RedirectResponse(url=f"{auth_url}?{query}")


@router.get("/callback")
async def callback(
    code: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """OIDC Callback — tausche Code gegen Token."""
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured",
        )
    config = await auth_service.get_oidc_config()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        tokens = response.json()
    return {
        "access_token": tokens.get("access_token"),
        "id_token": tokens.get("id_token"),
        "token_type": "Bearer",
    }


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
) -> dict:
    """Aktueller User mit GA4GH Passport Claims."""
    return user


@router.get("/status")
async def auth_status() -> dict:
    """Auth Konfigurationsstatus."""
    settings = get_settings()
    return {
        "auth_enabled": settings.auth_enabled,
        "oidc_issuer": settings.oidc_issuer if settings.auth_enabled else None,
        "mode": "production" if settings.auth_enabled else "development",
        "ga4gh_passport_support": True,
        "supported_providers": [
            "Keycloak",
            "ELIXIR AAI",
            "Google",
            "GitHub",
        ],
    }
