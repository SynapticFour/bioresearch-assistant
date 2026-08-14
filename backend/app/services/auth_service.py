"""GA4GH Passport-compatible auth service.

Supports: Keycloak, ELIXIR AAI, Google, Microsoft Entra.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def extract_roles(claims: dict[str, Any]) -> list[str]:
    """Roles from a JWT payload or our user dict.

    Keycloak uses realm_access.roles; Entra often uses a top-level roles list.
    """
    raw = claims.get("roles")
    if isinstance(raw, list) and raw:
        return [str(r) for r in raw if r]
    realm = claims.get("realm_access")
    if isinstance(realm, dict):
        realm_roles = realm.get("roles")
        if isinstance(realm_roles, list) and realm_roles:
            return [str(r) for r in realm_roles if r]
    resource = claims.get("resource_access")
    if isinstance(resource, dict):
        collected: list[str] = []
        for entry in resource.values():
            if isinstance(entry, dict) and isinstance(entry.get("roles"), list):
                collected.extend(str(r) for r in entry["roles"] if r)
        if collected:
            return collected
    return []


def _get_signing_key_from_jwks(token: str, jwks: dict[str, Any]) -> object:
    """Extract signing key from JWKS by token's kid."""
    unverified = jwt.get_unverified_headers(token)
    kid = unverified.get("kid")
    if not kid:
        raise ValueError("Token has no kid in header")
    for key_dict in jwks.get("keys", []):
        if key_dict.get("kid") == kid:
            return jwk.construct(key_dict)
    raise ValueError("No matching key found in JWKS")


class AuthService:
    """OIDC token verification and GA4GH Passport extraction."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._jwks: dict[str, Any] | None = None

    async def get_oidc_config(self) -> dict[str, Any]:
        """Fetch OIDC discovery document."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
            )
            response.raise_for_status()
            return response.json()

    async def get_jwks(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch JSON Web Key Set for token verification. Refetch on rotation."""
        if self._jwks is None or force_refresh:
            config = await self.get_oidc_config()
            jwks_uri = config.get("jwks_uri")
            if not jwks_uri:
                raise ValueError("OIDC config has no jwks_uri")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT and extract claims. Refresh JWKS once on unknown kid."""
        algorithms = ["RS256", "ES256"]
        if (self.settings.jwt_algorithm or "").upper() not in ("", "RS256", "ES256"):
            logger.warning(
                "Ignoring JWT_ALGORITHM=%s for OIDC; using RS256/ES256 only",
                self.settings.jwt_algorithm,
            )

        async def _decode(jwks: dict[str, Any]) -> dict[str, Any]:
            key = _get_signing_key_from_jwks(token, jwks)
            kwargs: dict[str, Any] = {
                "algorithms": algorithms,
                "audience": self.settings.oidc_client_id,
                "options": {"verify_aud": bool(self.settings.oidc_client_id)},
            }
            if self.settings.oidc_issuer:
                kwargs["issuer"] = self.settings.oidc_issuer
            return jwt.decode(token, key, **kwargs)

        jwks = await self.get_jwks()
        try:
            return await _decode(jwks)
        except (ValueError, JWTError) as first:
            if "No matching key" not in str(first) and "kid" not in str(first).lower():
                if isinstance(first, JWTError):
                    raise ValueError(f"Invalid token: {first}") from first
                raise
            jwks = await self.get_jwks(force_refresh=True)
            try:
                return await _decode(jwks)
            except JWTError as e:
                raise ValueError(f"Invalid token: {e}") from e

    async def extract_ga4gh_passports(self, token: str) -> dict[str, Any]:
        """Extract GA4GH Passports from token claims.

        GA4GH Passport Spec: https://github.com/ga4gh/data-security
        """
        claims = await self.verify_token(token)

        passports = claims.get("ga4gh_passport_v1", [])
        visas = claims.get("ga4gh_visa_v1", [])

        return {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
            "passports": passports,
            "visas": visas,
            "roles": extract_roles(claims),
            "organization": claims.get("organization") or claims.get("org"),
            "realm_access": claims.get("realm_access"),
        }
