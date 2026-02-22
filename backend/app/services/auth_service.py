"""GA4GH Passport-kompatibler Auth Service.

Unterstützt: Keycloak, ELIXIR AAI, Google, GitHub.
"""

import logging
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


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
        """Hole OIDC Discovery Document."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
            )
            response.raise_for_status()
            return response.json()

    async def get_jwks(self) -> dict[str, Any]:
        """Hole JSON Web Key Set für Token Verifikation."""
        if self._jwks is None:
            config = await self.get_oidc_config()
            jwks_uri = config.get("jwks_uri")
            if not jwks_uri:
                raise ValueError("OIDC config has no jwks_uri")
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verifiziere JWT Token und extrahiere Claims."""
        jwks = await self.get_jwks()
        try:
            key = _get_signing_key_from_jwks(token, jwks)
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256", "ES256"],
                audience=self.settings.oidc_client_id,
                options={"verify_aud": bool(self.settings.oidc_client_id)},
            )
            return payload
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}") from e

    async def extract_ga4gh_passports(self, token: str) -> dict[str, Any]:
        """Extrahiere GA4GH Passports aus Token Claims.

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
            "roles": claims.get("roles", []),
        }
