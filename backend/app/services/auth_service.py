"""GA4GH Passport-compatible auth service.

Supports: Keycloak, ELIXIR AAI, Google, Microsoft Entra.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidTokenError

from app.core.claims_map import apply_profile_claims, detect_profile
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
    """Extract a cryptography key from JWKS by the token's kid."""
    unverified = jwt.get_unverified_header(token)
    kid = unverified.get("kid")
    if not kid:
        raise ValueError("Token has no kid in header")
    for key_dict in jwks.get("keys", []):
        if key_dict.get("kid") == kid:
            return PyJWK.from_dict(key_dict).key
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
        except (ValueError, InvalidTokenError) as first:
            if "No matching key" not in str(first) and "kid" not in str(first).lower():
                if isinstance(first, InvalidTokenError):
                    raise ValueError(f"Invalid token: {first}") from first
                raise
            jwks = await self.get_jwks(force_refresh=True)
            try:
                return await _decode(jwks)
            except InvalidTokenError as e:
                raise ValueError(f"Invalid token: {e}") from e

    async def _jwks_for_issuer(self, issuer: str) -> dict[str, Any] | None:
        """JWKS for a visa issuer (often not the OIDC broker)."""
        issuer = issuer.rstrip("/")
        if self.settings.oidc_issuer and issuer == self.settings.oidc_issuer.rstrip("/"):
            return await self.get_jwks()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                discovery = await client.get(f"{issuer}/.well-known/openid-configuration")
                discovery.raise_for_status()
                jwks_uri = discovery.json().get("jwks_uri")
                if not jwks_uri:
                    return None
                keys = await client.get(jwks_uri)
                keys.raise_for_status()
                return keys.json()
        except (httpx.HTTPError, ValueError, TypeError) as e:
            logger.warning("visa issuer JWKS fetch failed for %s: %s", issuer, e)
            return None

    async def verify_visa_jwt(self, visa_jwt: str) -> dict[str, Any] | None:
        """Verify one nested GA4GH visa JWT (same job Ferrum does on DRS/WES).

        Broker JWKS first, then the visa ``iss`` discovery document. Failed
        signatures are dropped, not trusted as claims.
        """
        if visa_jwt.count(".") != 2:
            return None
        try:
            header = jwt.get_unverified_header(visa_jwt)
        except InvalidTokenError:
            return None
        alg = header.get("alg")
        if alg not in ("RS256", "ES256"):
            logger.warning("dropping visa JWT with alg=%s", alg)
            return None

        unverified = jwt.decode(visa_jwt, options={"verify_signature": False})
        jwks_candidates: list[dict[str, Any]] = []
        try:
            jwks_candidates.append(await self.get_jwks())
        except (ValueError, httpx.HTTPError) as e:
            logger.debug("broker JWKS unavailable for visa verify: %s", e)
        iss = unverified.get("iss")
        if isinstance(iss, str) and iss:
            extra = await self._jwks_for_issuer(iss)
            if extra is not None:
                jwks_candidates.append(extra)

        for jwks in jwks_candidates:
            try:
                key = _get_signing_key_from_jwks(visa_jwt, jwks)
                claims = jwt.decode(
                    visa_jwt,
                    key,
                    algorithms=["RS256", "ES256"],
                    options={"verify_aud": False, "verify_iss": False},
                )
                visa = claims.get("ga4gh_visa_v1")
                return visa if isinstance(visa, dict) else None
            except (ValueError, InvalidTokenError):
                continue
        logger.warning("dropping visa JWT that failed signature verification")
        return None

    async def extract_ga4gh_passports(self, token: str) -> dict[str, Any]:
        """Extract GA4GH Passports from token claims.

        Nested ``ga4gh_passport_v1`` visa JWTs are signature-verified (Ferrum
        does the same before enforcing DRS/WES). Embedded ``ga4gh_visa_v1``
        objects on the ID token are kept as-is (already covered by ID-token
        JWKS verify).
        """
        claims = await self.verify_token(token)
        profile = detect_profile(self.settings.oidc_issuer, self.settings.oidc_profile)

        passports = claims.get("ga4gh_passport_v1", [])
        if not isinstance(passports, list):
            passports = [passports] if passports else []

        verified: list[dict[str, Any]] = []
        for item in passports:
            if isinstance(item, str) and item.count(".") == 2:
                visa = await self.verify_visa_jwt(item)
                if visa:
                    verified.append(visa)
            elif isinstance(item, dict):
                verified.append(item)

        embedded = claims.get("ga4gh_visa_v1")
        if isinstance(embedded, dict):
            verified.append(embedded)
        elif isinstance(embedded, list):
            verified.extend(v for v in embedded if isinstance(v, dict))

        mapped = apply_profile_claims(claims, profile)
        email = mapped.get("email") or claims.get("email")
        return {
            "sub": claims.get("sub"),
            "email": email,
            "name": claims.get("name"),
            "passports": passports,
            "visas": verified,
            "roles": extract_roles(claims),
            "organization": mapped.get("organization"),
            "groups": mapped.get("groups") or [],
            "groups_prefix": profile.groups_prefix,
            "idp_profile": profile.name,
            "realm_access": claims.get("realm_access"),
        }
