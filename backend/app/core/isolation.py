"""Konfigurierbares Isolation-System.

Modi:
- user:  Jeder Nutzer sieht nur seine eigenen Daten
- team:  Alle Nutzer einer Institution teilen Daten
- open:  Alle sehen alles (nur für Dev/Demo)
"""

from app.core.config import get_settings


def get_scope_filter(current_user: dict) -> dict:
    """Gibt den korrekten Filter für DB-Abfragen zurück.

    Basierend auf dem konfigurierten Isolation-Modus.
    """
    settings = get_settings()

    if settings.isolation_mode == "user":
        return {"user_id": current_user.get("sub")}

    if settings.isolation_mode == "team":
        team_id = _extract_team_id(current_user)
        return {"team_id": team_id}

    # open / dev-modus
    return {}


def get_scope_values(current_user: dict) -> dict:
    """Gibt user_id und team_id zurück für neue Einträge."""
    return {
        "user_id": current_user.get("sub"),
        "team_id": _extract_team_id(current_user),
    }


def _extract_team_id(current_user: dict) -> str:
    """Extrahiere Team ID aus User Claims.

    Priorität:
    1. GA4GH Passport AffiliationAndRole
    2. OIDC organization claim (Azure AD, Keycloak)
    3. Email-Domain (z.B. ukhd.de → domain:ukhd.de)
    4. Fallback: user sub
    """
    # GA4GH Passport AffiliationAndRole
    for visa in current_user.get("visas") or []:
        if isinstance(visa, dict) and visa.get("type") == "AffiliationAndRole":
            return f"org:{visa.get('value', '')}"

    # OIDC organization claim
    if org := current_user.get("organization"):
        return f"org:{org}"

    # Email-Domain
    if email := current_user.get("email"):
        domain = email.split("@")[-1]
        return f"domain:{domain}"

    # Fallback
    return f"user:{current_user.get('sub', 'unknown')}"
