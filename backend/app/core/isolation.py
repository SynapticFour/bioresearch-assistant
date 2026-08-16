"""Configurable data isolation.

Modes:
- user:  each caller sees only their own rows
- team:  callers share data by institution/team
- open:  everyone sees everything (dev/demo only)
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from sqlalchemy.sql import Select

from app.core.config import get_settings
from app.core.database import Base

IsolationMode = Literal["user", "team", "open"]


class ScopeFilter(TypedDict, total=False):
    """DB filter produced by get_scope_filter. Empty dict = no filter (open)."""

    user_id: str
    team_id: str


class ScopeValues(TypedDict):
    """Owner fields to persist on new rows."""

    user_id: str | None
    team_id: str | None


def _normalized_mode() -> IsolationMode:
    raw = (get_settings().isolation_mode or "user").strip().lower()
    if raw in ("user", "team", "open"):
        return raw  # type: ignore[return-value]
    return "user"


def current_isolation_mode() -> IsolationMode:
    """Public alias for the configured isolation mode (fail-closed to user)."""
    return _normalized_mode()


def get_scope_filter(current_user: dict[str, Any]) -> ScopeFilter:
    """Return the correct filter dict for DB queries.

    Based on the configured isolation mode.
    """
    mode = _normalized_mode()

    if mode == "user":
        sub = current_user.get("sub")
        return {"user_id": sub if sub else "__missing_sub__"}

    if mode == "team":
        return {"team_id": _extract_team_id(current_user)}

    return {}


def get_scope_values(current_user: dict[str, Any]) -> ScopeValues:
    """Return user_id and team_id for new rows."""
    return {
        "user_id": current_user.get("sub"),
        "team_id": _extract_team_id(current_user),
    }


def apply_scope(stmt: Select[Any], model: type[Base], scope: dict[str, Any]) -> Select[Any]:
    """Apply user/team isolation to a SQLAlchemy select.

    Uses truthy values only (empty string does not match all rows).
    """
    user_id = scope.get("user_id")
    if user_id:
        return stmt.where(model.user_id == user_id)
    team_id = scope.get("team_id")
    if team_id:
        return stmt.where(model.team_id == team_id)
    return stmt


def apply_scope_for_user(
    stmt: Select[Any],
    model: type[Base],
    current_user: dict[str, Any],
) -> Select[Any]:
    """apply_scope using get_scope_filter(current_user)."""
    return apply_scope(stmt, model, get_scope_filter(current_user))


def object_visible_to_scope(
    owner_user_id: str | None,
    owner_team_id: str | None,
    scope: dict[str, Any],
) -> bool:
    """True if an owned artifact is visible under the given scope filter."""
    if not scope:
        return True
    user_id = scope.get("user_id")
    if user_id:
        return owner_user_id == user_id
    team_id = scope.get("team_id")
    if team_id:
        return owner_team_id == team_id
    return True


def _extract_team_id(current_user: dict[str, Any]) -> str:
    """Extract team ID from user claims.

    Priority:
    1. GA4GH Passport AffiliationAndRole (consumed visa, not issued here)
    2. IdP groups from the operator claims-map (Keycloak / Entra / LS Login)
    3. OIDC organization claim (Azure AD tid, Keycloak organization)
    4. Email domain (e.g. ukhd.de → domain:ukhd.de)
    5. Fallback: user sub
    """
    for visa in current_user.get("visas") or []:
        if isinstance(visa, dict) and visa.get("type") == "AffiliationAndRole":
            return f"org:{visa.get('value', '')}"

    groups = current_user.get("groups")
    if isinstance(groups, list) and groups:
        first = str(groups[0]).strip()
        if first:
            prefix = str(current_user.get("groups_prefix") or "group:")
            if first.startswith(prefix):
                return first
            return f"{prefix}{first}"
    if isinstance(groups, str) and groups.strip():
        return f"group:{groups.strip()}"

    if org := current_user.get("organization"):
        return f"org:{org}"

    if email := current_user.get("email"):
        domain = email.split("@")[-1]
        return f"domain:{domain}"

    return f"user:{current_user.get('sub', 'unknown')}"


extract_team_id = _extract_team_id
