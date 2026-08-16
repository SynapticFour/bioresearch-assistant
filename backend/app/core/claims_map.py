"""Operator IdP profiles (claims-map). BRA does not issue GA4GH Passports."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROFILES_DIR = Path(__file__).resolve().parent.parent / "idp_profiles"

KNOWN_PROFILES = ("keycloak", "entra", "ls-login", "broker")


@dataclass(frozen=True)
class IdpProfile:
    name: str
    issuer_contains: str
    groups_claim: str
    groups_prefix: str
    organization_claim: str
    email_claim: str
    login_scope: str


def _load_toml(name: str) -> IdpProfile:
    path = _PROFILES_DIR / f"{name}.toml"
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return IdpProfile(
        name=str(data["name"]),
        issuer_contains=str(data.get("issuer_contains") or ""),
        groups_claim=str(data.get("groups_claim") or "groups"),
        groups_prefix=str(data.get("groups_prefix") or "group:"),
        organization_claim=str(data.get("organization_claim") or "organization"),
        email_claim=str(data.get("email_claim") or "email"),
        login_scope=str(data.get("login_scope") or "openid email profile"),
    )


@lru_cache
def profile_by_name(name: str) -> IdpProfile:
    key = (name or "keycloak").strip().lower()
    if key == "auto":
        key = "keycloak"
    if key not in KNOWN_PROFILES:
        key = "keycloak"
    return _load_toml(key)


def detect_profile(issuer: str, configured: str) -> IdpProfile:
    """Resolve OIDC_PROFILE=auto from the issuer URL; otherwise load the named profile."""
    explicit = (configured or "auto").strip().lower()
    if explicit and explicit != "auto":
        return profile_by_name(explicit)
    iss = (issuer or "").lower()
    if "login.microsoftonline.com" in iss or "sts.windows.net" in iss:
        return profile_by_name("entra")
    if "elixir" in iss or "aai.lifescience" in iss or "login.elixir" in iss:
        return profile_by_name("ls-login")
    if "8180" in iss or "aai-broker" in iss or "/ga4gh" in iss:
        return profile_by_name("broker")
    return profile_by_name("keycloak")


def extract_groups(claims: dict[str, Any], profile: IdpProfile) -> list[str]:
    raw = claims.get(profile.groups_claim)
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if isinstance(raw, list):
        return [str(g).strip() for g in raw if str(g).strip()]
    return []


def apply_profile_claims(claims: dict[str, Any], profile: IdpProfile) -> dict[str, Any]:
    """Copy profile-mapped fields onto the user dict. Does not mint visas."""
    email = claims.get(profile.email_claim) or claims.get("email")
    org = claims.get(profile.organization_claim) or claims.get("organization") or claims.get("org")
    groups = extract_groups(claims, profile)
    return {
        "email": email,
        "organization": org,
        "groups": groups,
        "idp_profile": profile.name,
    }
