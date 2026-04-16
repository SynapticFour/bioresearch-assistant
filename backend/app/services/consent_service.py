"""Research consent business logic and FHIR Consent serialization."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.interoperability.mii import constants as mii_c
from app.models.patient_record import PatientRecordModel
from app.models.research_consent import ResearchConsent, ResearchConsentEvent
from app.schemas.consent import ResearchConsentCreate, ResearchConsentUpdate

logger = logging.getLogger(__name__)


def _apply_scope_consent(stmt: Select, scope: dict) -> Select:
    if "user_id" in scope and scope["user_id"]:
        return stmt.where(ResearchConsent.user_id == scope["user_id"])
    if "team_id" in scope and scope["team_id"]:
        return stmt.where(ResearchConsent.team_id == scope["team_id"])
    return stmt


def _apply_scope_patient(stmt: Select, scope: dict) -> Select:
    if "user_id" in scope and scope["user_id"]:
        return stmt.where(PatientRecordModel.user_id == scope["user_id"])
    if "team_id" in scope and scope["team_id"]:
        return stmt.where(PatientRecordModel.team_id == scope["team_id"])
    return stmt


async def _get_patient_for_scope(
    db: AsyncSession,
    pseudonym_id: str,
    scope: dict,
) -> PatientRecordModel | None:
    stmt = select(PatientRecordModel).where(PatientRecordModel.pseudonym_id == pseudonym_id)
    stmt = _apply_scope_patient(stmt, scope)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _supersede_active_same_policy(
    db: AsyncSession,
    pseudonym_id: str,
    policy_id: str,
    except_id: UUID | None,
) -> None:
    """Mark other active consents for same pseudonym+policy as inactive."""
    q = (
        update(ResearchConsent)
        .where(
            ResearchConsent.pseudonym_id == pseudonym_id,
            ResearchConsent.policy_id == policy_id,
            ResearchConsent.status == "active",
        )
        .values(status="inactive", updated_at=datetime.now(UTC))
    )
    if except_id is not None:
        q = q.where(ResearchConsent.id != except_id)
    await db.execute(q)


async def create_consent(
    db: AsyncSession,
    body: ResearchConsentCreate,
    scope: dict,
    scope_values: dict,
    actor_user_id: str | None,
) -> ResearchConsent:
    """Create consent record; optionally supersede prior active same policy."""
    patient = await _get_patient_for_scope(db, body.pseudonym_id, scope)
    if not patient:
        raise ValueError("pseudonym_not_found_or_out_of_scope")

    purpose = [p.model_dump() for p in body.purpose_codes]
    if not purpose:
        purpose = [{"system": mii_c.ACT_REASON_SYSTEM, "code": mii_c.ACT_REASON_RESEARCH_CODE}]

    cid = uuid4()
    consent = ResearchConsent(
        id=cid,
        pseudonym_id=body.pseudonym_id,
        policy_id=body.policy_id,
        policy_version=body.policy_version,
        status=body.status,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        covered_project_ids=list(body.covered_project_ids),
        purpose_codes=purpose,
        source=body.source,
        meta_json=body.meta_json,
        user_id=scope_values.get("user_id"),
        team_id=scope_values.get("team_id"),
    )
    db.add(consent)
    await db.flush()
    db.add(
        ResearchConsentEvent(
            consent_id=cid,
            event_type="created",
            actor_user_id=actor_user_id,
            payload={"policy_version": body.policy_version},
        )
    )

    if body.status == "active":
        await _supersede_active_same_policy(db, body.pseudonym_id, body.policy_id, except_id=cid)
        db.add(
            ResearchConsentEvent(
                consent_id=cid,
                event_type="activated",
                actor_user_id=actor_user_id,
                payload={},
            )
        )

    await db.commit()
    await db.refresh(consent)
    return consent


async def get_consent(
    db: AsyncSession,
    consent_id: UUID,
    scope: dict,
) -> ResearchConsent | None:
    stmt = select(ResearchConsent).where(ResearchConsent.id == consent_id)
    stmt = _apply_scope_consent(stmt, scope)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_consents_for_pseudonym(
    db: AsyncSession,
    pseudonym_id: str,
    scope: dict,
) -> list[ResearchConsent]:
    stmt = select(ResearchConsent).where(ResearchConsent.pseudonym_id == pseudonym_id)
    stmt = _apply_scope_consent(stmt, scope)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_consents(
    db: AsyncSession,
    scope: dict,
    pseudonym_id: str | None = None,
) -> list[ResearchConsent]:
    stmt = select(ResearchConsent)
    stmt = _apply_scope_consent(stmt, scope)
    if pseudonym_id:
        stmt = stmt.where(ResearchConsent.pseudonym_id == pseudonym_id)
    stmt = stmt.order_by(ResearchConsent.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_consent(
    db: AsyncSession,
    consent_id: UUID,
    body: ResearchConsentUpdate,
    scope: dict,
    actor_user_id: str | None,
) -> ResearchConsent | None:
    consent = await get_consent(db, consent_id, scope)
    if not consent:
        return None
    if body.covered_project_ids is not None:
        consent.covered_project_ids = list(body.covered_project_ids)
    if body.valid_to is not None:
        consent.valid_to = body.valid_to
    if body.meta_json is not None:
        consent.meta_json = body.meta_json
    if body.status is not None:
        consent.status = body.status
        if body.status == "active":
            await _supersede_active_same_policy(
                db,
                consent.pseudonym_id,
                consent.policy_id,
                except_id=consent.id,
            )
    patch_payload = body.model_dump(exclude_unset=True)
    if patch_payload:
        db.add(
            ResearchConsentEvent(
                consent_id=consent.id,
                event_type="updated",
                actor_user_id=actor_user_id,
                payload=patch_payload,
            )
        )
    consent.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(consent)
    return consent


async def withdraw_consent(
    db: AsyncSession,
    consent_id: UUID,
    scope: dict,
    actor_user_id: str | None,
    reason: str | None,
) -> ResearchConsent | None:
    consent = await get_consent(db, consent_id, scope)
    if not consent:
        return None
    consent.status = "withdrawn"
    consent.updated_at = datetime.now(UTC)
    db.add(
        ResearchConsentEvent(
            consent_id=consent.id,
            event_type="withdrawn",
            actor_user_id=actor_user_id,
            payload={"reason": reason},
        )
    )
    await db.commit()
    await db.refresh(consent)
    return consent


def _patient_fhir_id(pseudonym_id: str) -> str:
    from app.interoperability.mii.phenopacket_to_fhir import _slug

    return f"patient-{_slug(pseudonym_id)}"


def consent_to_fhir_dict(consent: ResearchConsent) -> dict:
    """FHIR R4 Consent for export (minimal valid structure)."""
    patient_ref = f"Patient/{_patient_fhir_id(consent.pseudonym_id)}"
    purpose: list[dict] = []
    for p in consent.purpose_codes or []:
        if isinstance(p, dict):
            coding = []
            if p.get("system"):
                coding.append(
                    {
                        "system": p["system"],
                        "code": p["code"],
                        "display": p.get("display"),
                    }
                )
            else:
                coding.append({"code": p.get("code", "")})
            purpose.append({"coding": coding})

    return {
        "resourceType": "Consent",
        "id": str(consent.id),
        "status": "active"
        if consent.status == "active"
        else ("inactive" if consent.status in ("inactive", "withdrawn") else "draft"),
        "scope": {
            "coding": [
                {
                    "system": mii_c.CONSENT_SCOPE_SYSTEM,
                    "code": mii_c.CONSENT_SCOPE_CODE,
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": mii_c.CONSENT_CATEGORY_RESEARCH_SYSTEM,
                        "code": mii_c.CONSENT_CATEGORY_RESEARCH_CODE,
                    }
                ]
            }
        ],
        "patient": {"reference": patient_ref},
        "dateTime": consent.valid_from.isoformat() if consent.valid_from else None,
        "policyRule": {
            "coding": [
                {
                    "system": f"{mii_c.MII_FHIR_CANONICAL_BASE}/sid/policy",
                    "code": consent.policy_id,
                    "display": f"Policy {consent.policy_id} v{consent.policy_version}",
                }
            ]
        },
        "provision": {
            "period": {
                "start": consent.valid_from.isoformat() if consent.valid_from else None,
                "end": consent.valid_to.isoformat() if consent.valid_to else None,
            },
            "purpose": purpose or None,
        },
    }


async def find_active_consent(
    db: AsyncSession,
    pseudonym_id: str,
    policy_id: str,
    scope: dict,
) -> ResearchConsent | None:
    """Active consent for export check (same scope as patient)."""
    now = datetime.now(UTC)
    stmt = select(ResearchConsent).where(
        ResearchConsent.pseudonym_id == pseudonym_id,
        ResearchConsent.policy_id == policy_id,
        ResearchConsent.status == "active",
        ResearchConsent.valid_from <= now,
    )
    stmt = _apply_scope_consent(stmt, scope)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    for c in rows:
        if c.valid_to is None or c.valid_to >= now:
            return c
    return None


def projects_covered(consent: ResearchConsent, required: list[str]) -> bool:
    """If required empty, True. Else every id must appear in covered_project_ids."""
    if not required:
        return True
    covered = set(str(x) for x in (consent.covered_project_ids or []))
    return all(r in covered for r in required)
