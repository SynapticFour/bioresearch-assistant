"""OIDC/OAuth2 and GA4GH Passport auth endpoints."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.auth import get_auth_service, get_current_user
from app.core.claims_map import detect_profile
from app.core.config import get_settings
from app.core.isolation import extract_team_id, get_scope_filter
from app.core.limiter import limiter
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

_ID_TOKEN_COOKIE = "bra_id_token"
_OAUTH_STATE_COOKIE = "bra_oauth_state"
_OAUTH_VERIFIER_COOKIE = "bra_oauth_verifier"
_OAUTH_STATE_MAX_AGE = 600


def _state_key() -> bytes:
    settings = get_settings()
    secret = settings.jwt_secret or settings.pseudonymization_encryption_key
    return secret.encode("utf-8")


def _sign_oauth_state(provider: str) -> str:
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    payload = f"{provider}:{nonce}:{ts}"
    sig = hmac.new(_state_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _verify_oauth_state(state: str) -> str:
    parts = (state or "").split(":")
    if len(parts) != 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    provider, _nonce, ts, sig = parts
    payload = f"{provider}:{_nonce}:{ts}"
    expected = hmac.new(_state_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    try:
        issued = int(ts)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state"
        ) from e
    if abs(time.time() - issued) > _OAUTH_STATE_MAX_AGE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state expired")
    return provider


def _pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, S256 code_challenge) for OAuth PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@router.get("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    provider: str = "oidc",
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Login with OIDC providers. provider: oidc | google | microsoft."""
    _ = auth_service
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured (development mode)",
        )
    provider_issuers = {
        "google": "https://accounts.google.com",
        "microsoft": f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/v2.0",
        "oidc": settings.oidc_issuer,
    }
    issuer = provider_issuers.get(provider) or settings.oidc_issuer
    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider}",
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
        resp.raise_for_status()
        oidc_config = resp.json()
    state = _sign_oauth_state(provider)
    verifier, challenge = _pkce_pair()
    profile = detect_profile(settings.oidc_issuer, settings.oidc_profile)
    if provider == "microsoft":
        profile = detect_profile(
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/v2.0",
            "entra",
        )
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": profile.login_scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = oidc_config["authorization_endpoint"]
    query = urlencode(params)
    redirect = RedirectResponse(url=f"{auth_url}?{query}")
    cookie_kw = {
        "max_age": _OAUTH_STATE_MAX_AGE,
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.allows_unauthenticated_dev,
        "path": "/",
    }
    redirect.set_cookie(key=_OAUTH_STATE_COOKIE, value=state, **cookie_kw)
    redirect.set_cookie(key=_OAUTH_VERIFIER_COOKIE, value=verifier, **cookie_kw)
    return redirect


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str = Query(default=""),
    auth_service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """OIDC callback — exchange code, set httpOnly cookie, redirect to SPA."""
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth is not configured",
        )
    cookie_state = request.cookies.get(_OAUTH_STATE_COOKIE) or ""
    if not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state mismatch",
        )
    _verify_oauth_state(state)
    code_verifier = request.cookies.get(_OAUTH_VERIFIER_COOKIE) or ""
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing PKCE verifier",
        )
    config = await auth_service.get_oidc_config()
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_response = await client.post(
            config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        tokens = token_response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Identity provider returned no access_token",
        )
    try:
        expires_in = int(tokens.get("expires_in") or 3600)
    except (TypeError, ValueError):
        expires_in = 3600
    frontend = (settings.frontend_base_url or "http://localhost:5173").rstrip("/")
    redirect = RedirectResponse(url=f"{frontend}/auth/callback", status_code=status.HTTP_302_FOUND)
    cookie_kw = {
        "max_age": max(60, min(expires_in, 86400)),
        "httponly": True,
        "samesite": "lax",
        "secure": not settings.allows_unauthenticated_dev,
        "path": "/",
    }
    redirect.set_cookie(key=settings.session_cookie_name, value=str(access_token), **cookie_kw)
    id_token = tokens.get("id_token")
    if id_token:
        redirect.set_cookie(key=_ID_TOKEN_COOKIE, value=str(id_token), **cookie_kw)
    redirect.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    redirect.delete_cookie(_OAUTH_VERIFIER_COOKIE, path="/")
    return redirect


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    """Clear session cookies. When the IdP advertises end_session_endpoint, return it.

    The SPA should redirect the browser there (RP-initiated logout), then land on
    FRONTEND_BASE_URL/login. BRA is not a Passport issuer; this is OIDC logout only.
    """
    settings = get_settings()
    idp_logout_url: str | None = None
    if settings.auth_enabled:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
                )
                resp.raise_for_status()
                end_session = resp.json().get("end_session_endpoint")
            if end_session:
                frontend = (settings.frontend_base_url or "http://localhost:5173").rstrip("/")
                params: dict[str, str] = {
                    "client_id": settings.oidc_client_id,
                    "post_logout_redirect_uri": f"{frontend}/login",
                }
                id_token = request.cookies.get(_ID_TOKEN_COOKIE)
                if id_token:
                    params["id_token_hint"] = id_token
                idp_logout_url = f"{end_session}?{urlencode(params)}"
        except Exception:
            logger.warning("OIDC discovery for logout failed; cookie-only logout", exc_info=True)
    body = {"idp_logout_url": idp_logout_url}
    response = JSONResponse(content=body)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(_ID_TOKEN_COOKIE, path="/")
    response.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    response.delete_cookie(_OAUTH_VERIFIER_COOKIE, path="/")
    return response


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
) -> dict:
    """Current user with GA4GH Passport claims and isolation info."""
    settings = get_settings()
    return {
        **user,
        "isolation_mode": settings.isolation_mode,
        "team_id": extract_team_id(user),
        "scope": get_scope_filter(user),
    }


@router.get("/status")
async def auth_status() -> dict:
    """Auth configuration status."""
    settings = get_settings()
    return {
        "auth_enabled": settings.auth_enabled,
        "oidc_issuer": settings.oidc_issuer if settings.auth_enabled else None,
        "mode": "production" if settings.auth_enabled else "development",
        "ga4gh_passport_support": True,
        "supported_providers": [
            "ga4gh-infra AAI broker",
            "Keycloak",
            "ELIXIR AAI / LS Login",
            "Google",
            "Microsoft Entra",
        ],
        "oidc_profile": settings.oidc_profile,
        "issues_passports": False,
    }
