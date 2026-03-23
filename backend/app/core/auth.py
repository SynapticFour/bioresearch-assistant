"""Auth dependencies: Bearer token extraction and optional OIDC verification."""

from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


@lru_cache
def get_auth_service() -> AuthService:
    """Cached AuthService instance."""
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Extrahiere aktuellen User aus Bearer Token.

    Falls Auth nicht konfiguriert → gibt Dev-User zurück (Dev-Modus).
    Falls Auth konfiguriert aber kein Token → 401.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        if settings.deployment and settings.deployment not in ("local", "development", ""):
            raise RuntimeError(
                "Auth must be enabled in production. Set OIDC_ISSUER and OIDC_CLIENT_ID in .env"
            )
        return {
            "sub": "dev-user",
            "email": "dev@synapticfour.com",
            "name": "Developer",
            "roles": ["admin"],
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
    user: dict = Depends(get_current_user),
) -> dict:
    """Nur Admins dürfen diese Funktion aufrufen."""
    if "admin" not in user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
