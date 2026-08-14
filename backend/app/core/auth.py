"""Auth dependencies: Bearer token extraction and optional OIDC verification."""

from __future__ import annotations

from typing import Any, TypedDict

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.auth_service import AuthService, extract_roles

security = HTTPBearer(auto_error=False)


class UserContext(TypedDict, total=False):
    """Authenticated (or explicit dev) user claims used across the API."""

    sub: str
    email: str
    name: str
    roles: list[str]
    passports: list[Any]
    visas: list[Any]
    organization: str


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Process-wide AuthService (JWKS can be refreshed on unknown kid)."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    """Drop cached AuthService (tests / key rotation)."""
    global _auth_service
    _auth_service = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Extract the current user from a Bearer token.

    If auth is not configured and the deployment is an explicit local/test
    target, return a non-production dev user. Otherwise 401 / fail closed.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        if not settings.allows_unauthenticated_dev:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Authentication required. Set OIDC_ISSUER and OIDC_CLIENT_ID, "
                    "or set DEPLOYMENT=local|development|test for unauthenticated dev."
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "sub": "dev-user",
            "email": "contact@synapticfour.com",
            "name": "Developer",
            "roles": ["admin"],
            "passports": [],
            "visas": [],
        }

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_service.extract_ga4gh_passports(credentials.credentials)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_admin(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Only admins may call this endpoint."""
    if "admin" not in extract_roles(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
