"""Map BRA Phenopacket ids to Solum subject-link payloads (ADR-0003)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def build_subject_link_payload(
    *,
    phenopacket_id: str,
    actor: str,
    purpose: str,
    capability: list[str] | None = None,
    solum_subject_id: str | None = None,
    ferrum_drs_id: str | None = None,
    ehr_id: str | None = None,
) -> dict[str, Any]:
    """Build Solum `POST /v1/cdr/subject-link` JSON (sidecar SubjectLinkBody).

    Default join: ``solum_subject_id`` equals ``phenopacket_id`` unless overridden
    (e.g. FHIR Patient.id). That string must match Ferrum DRS metadata ``solum_subject``.

    Solum requires ``actor``, ``purpose``, and ``capability`` (typically
    ``solum:cdr:write``). Omitting them yields HTTP 4xx against current sidecars.
    """
    pid = phenopacket_id.strip()
    if not pid:
        raise ValueError("phenopacket_id must be non-empty")
    subject = (solum_subject_id or pid).strip()
    if not subject:
        raise ValueError("solum_subject_id must be non-empty")
    actor_id = actor.strip()
    if not actor_id:
        raise ValueError("actor must be non-empty")
    purpose_id = purpose.strip()
    if not purpose_id:
        raise ValueError("purpose must be non-empty")
    caps = [c.strip() for c in (capability or ["solum:cdr:write"]) if c.strip()]
    if not caps:
        raise ValueError("capability must contain at least one Solum capability")
    payload: dict[str, Any] = {
        "actor": actor_id,
        "capability": caps,
        "purpose": purpose_id,
        "solum_subject_id": subject,
        "phenopacket_id": pid,
    }
    if ferrum_drs_id:
        payload["ferrum_drs_id"] = ferrum_drs_id.strip()
    if ehr_id:
        payload["ehr_id"] = ehr_id.strip()
    return payload


async def upsert_subject_link(
    payload: dict[str, Any],
    *,
    base_url: str,
    token: str,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    """POST subject-link to Solum sidecar. Returns (http_status, body)."""
    url = base_url.rstrip("/") + "/v1/cdr/subject-link"
    actor = str(payload.get("actor") or "").strip()
    caps = payload.get("capability") or []
    cap_header = ",".join(str(c) for c in caps if str(c).strip())
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # Solum-Demo also accepts X-Solum-Sidecar-Token
        "X-Solum-Sidecar-Token": token,
    }
    if actor:
        headers["X-Solum-Actor"] = actor
    if cap_header:
        headers["X-Solum-Capability"] = cap_header
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            body: dict[str, Any] = resp.json() if resp.content else {}
        except ValueError:
            body = {"_raw": resp.text}
        if resp.status_code >= 400:
            logger.warning(
                "Solum subject-link upsert failed status=%s body=%s",
                resp.status_code,
                body,
            )
        return resp.status_code, body
