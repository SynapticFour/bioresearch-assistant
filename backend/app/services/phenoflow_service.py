"""PhenoFlow orchestration service (Search-to-Execution bridge).

v0.1 design:
    * Query locally stored Phenopackets (patient_records) by HPO term(s).
    * Use phenopacket_assets to find linked DRS object_id(s) for each match.
    * Resolve DRS access URL (stream URL) via existing DRS service helpers.
    * Submit WES RunRequest per matched Phenopacket-asset pair.
    * Persist provenance into phenoflow_runs / phenoflow_run_items.

Data safety:
    * We only persist DRS identifiers (object_id) and WES run IDs.
    * No decoded genomic data is stored.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.isolation import get_scope_filter
from app.models.patient_record import PatientRecordModel
from app.models.phenoflow_run import PhenoFlowRun
from app.models.phenoflow_run_item import PhenoFlowRunItem
from app.models.phenopacket_asset import PhenopacketAsset
from app.schemas.phenoflow import (
    PhenoFlowRunItemSubmission,
    PhenoFlowRunRequest,
    PhenoFlowRunResponse,
    PhenopacketAssetFileType,
)
from app.schemas.wes import RunRequest, State
from app.services.drs_service import get_access_url
from app.services.wes_service import create_run as create_wes_run

logger = logging.getLogger(__name__)


HPO_KEYS_CANDIDATES = (
    "phenotypic_features",
    "phenotypicFeatures",
)

TYPE_KEYS_CANDIDATES = (
    "type",
    "ontology_term_type",
)

HPO_ID_KEYS_CANDIDATES = (
    "id",
    "hpo_id",
)

PLACEHOLDER_DRS_OBJECT_ID = "{{drs_object_id}}"
PLACEHOLDER_DRS_STREAM_URL = "{{drs_stream_url}}"
PLACEHOLDER_PHENOPACKET_ID = "{{pseudonym_id}}"
PLACEHOLDER_FILE_TYPE = "{{file_type}}"

PHENOPACKET_SCAN_MULTIPLIER = 10
MAX_PHENOPACKET_SCAN = 1000


def _extract_hpo_ids(phenopacket_json: object) -> set[str]:
    """Extract HPO term IDs from a Phenopacket v2 JSON dict."""
    if phenopacket_json is None:
        return set()
    if isinstance(phenopacket_json, str):
        # Defensive: endpoints sometimes handle stored JSON as string.
        try:
            import json

            phenopacket_json = json.loads(phenopacket_json)
        except Exception:
            return set()

    if not isinstance(phenopacket_json, dict):
        return set()

    hpo_ids: set[str] = set()
    phenotypic_features: list[Any] = []
    for k in HPO_KEYS_CANDIDATES:
        raw = phenopacket_json.get(k)
        if isinstance(raw, list):
            phenotypic_features = raw
            break

    for feature in phenotypic_features:
        if not isinstance(feature, dict):
            continue
        term_type: dict[str, Any] = {}
        for tk in TYPE_KEYS_CANDIDATES:
            v = feature.get(tk)
            if isinstance(v, dict):
                term_type = v
                break
        if not term_type:
            continue
        hpo_id = None
        for hidk in HPO_ID_KEYS_CANDIDATES:
            if isinstance(term_type.get(hidk), str):
                hpo_id = term_type[hidk]
                break
        if isinstance(hpo_id, str) and hpo_id.strip():
            hpo_ids.add(hpo_id.strip())

    return hpo_ids


def _apply_placeholders(template: object, context: dict[str, str]) -> object:
    """Recursively replace string placeholders within a workflow_params template."""
    if isinstance(template, str):
        out = template
        for placeholder, value in context.items():
            out = out.replace(placeholder, value)
        return out
    if isinstance(template, dict):
        return {k: _apply_placeholders(v, context) for k, v in template.items()}
    if isinstance(template, list):
        return [_apply_placeholders(v, context) for v in template]
    return template


def _apply_scope(stmt: object, model: object, current_user: dict[str, object]) -> object:
    """Apply isolation filtering to a select statement."""
    scope = get_scope_filter(current_user)
    if "user_id" in scope and scope["user_id"]:
        return stmt.where(model.user_id == scope["user_id"])
    if "team_id" in scope and scope["team_id"]:
        return stmt.where(model.team_id == scope["team_id"])
    return stmt


async def submit_pheno_flow_run(
    db: AsyncSession,
    request: PhenoFlowRunRequest,
    *,
    current_user: dict,
) -> PhenoFlowRunResponse:
    """Execute PhenoFlow v0.1: match phenopackets, resolve DRS, submit WES."""

    hpo_terms = sorted({t.strip() for t in request.hpo_terms if t and t.strip()})
    if not hpo_terms:
        return PhenoFlowRunResponse(
            phenoflow_run_id=str(uuid4()),
            matched_count=0,
            submitted_count=0,
            items=[],
            errors=["No valid HPO terms provided."],
        )

    logger.info(
        "PhenoFlow submit started (hpo_terms=%s limit_matches=%s)",
        len(hpo_terms),
        request.limit_matches,
    )

    # Persist master record first so even partial failures are traceable.
    phenoflow_run_id = uuid4()
    run = PhenoFlowRun(
        phenoflow_run_id=phenoflow_run_id,
        status="SUBMITTED",
        query_spec={
            "hpo_terms": hpo_terms,
            "file_type": request.file_type.value if request.file_type else None,
            "limit_matches": request.limit_matches,
        },
        workflow_spec={
            "workflow_url": request.workflow_url,
            "workflow_type": request.workflow_type,
            "workflow_type_version": request.workflow_type_version,
            "workflow_params_template": request.workflow_params_template,
        },
        user_id=(current_user.get("sub")),
        team_id=None,
        start_time=datetime.now(UTC),
        end_time=None,
    )
    # Isolation may use team_id derived from claims. Reuse isolation helper by
    # filtering rather than trying to compute team_id here (we store asset scope too).
    # Store user_id/team_id as best-effort:
    scope = get_scope_filter(current_user)
    if "user_id" in scope:
        run.user_id = scope.get("user_id")
    if "team_id" in scope:
        run.team_id = scope.get("team_id")

    db.add(run)

    scan_limit = min(
        MAX_PHENOPACKET_SCAN,
        max(1, request.limit_matches * PHENOPACKET_SCAN_MULTIPLIER),
    )
    stmt = select(PatientRecordModel).order_by(PatientRecordModel.pseudonym_id).limit(scan_limit)
    stmt = _apply_scope(stmt, PatientRecordModel, current_user)

    r = await db.execute(stmt)
    candidate_records = list(r.scalars().all())

    matched_count = 0

    # First pass: identify matching phenopacket pseudonym_ids.
    matching_pseudonyms: list[str] = []
    for rec in candidate_records:
        pp_dict = rec.phenopacket_json
        hpo_ids = _extract_hpo_ids(pp_dict)
        if hpo_ids.intersection(set(hpo_terms)):
            matching_pseudonyms.append(rec.pseudonym_id)

    if not matching_pseudonyms:
        await db.flush()
        return PhenoFlowRunResponse(
            phenoflow_run_id=str(phenoflow_run_id),
            matched_count=0,
            submitted_count=0,
            items=[],
            errors=[],
        )

    # Second pass: fetch linked assets for matching phenopackets.
    assets_stmt = select(PhenopacketAsset).where(
        PhenopacketAsset.pseudonym_id.in_(matching_pseudonyms),
    )
    if request.file_type is not None:
        assets_stmt = assets_stmt.where(PhenopacketAsset.file_type == request.file_type.value)
    assets_stmt = _apply_scope(assets_stmt, PhenopacketAsset, current_user)
    assets_r = await db.execute(assets_stmt)
    assets = list(assets_r.scalars().all())

    assets_by_pseudonym: dict[str, list[PhenopacketAsset]] = {}
    for a in assets:
        assets_by_pseudonym.setdefault(a.pseudonym_id, []).append(a)

    errors: list[str] = []
    submitted_count = 0
    items: list[PhenoFlowRunItemSubmission] = []

    # Third pass: submit WES per phenopacket-asset pair up to limit_matches.
    pairs_seen = 0
    for pseudonym_id in matching_pseudonyms:
        for asset in assets_by_pseudonym.get(pseudonym_id, []):
            pairs_seen += 1
            if pairs_seen > request.limit_matches:
                break

            matched_count += 1

            try:
                file_type_enum = PhenopacketAssetFileType(asset.file_type)
            except ValueError:
                file_type_enum = PhenopacketAssetFileType.other

            stream_access = get_access_url(asset.drs_object_id, "default")
            if stream_access is None or not stream_access.url:
                err = f"DRS access_url not found for object_id={asset.drs_object_id!r}"
                errors.append(err)
                db.add(
                    PhenoFlowRunItem(
                        phenoflow_run_id=phenoflow_run_id,
                        pseudonym_id=pseudonym_id,
                        drs_object_id=asset.drs_object_id,
                        file_type=asset.file_type,
                        wes_run_id=None,
                        state_snapshot="ERROR",
                        error=err,
                    ),
                )
                items.append(
                    PhenoFlowRunItemSubmission(
                        pseudonym_id=pseudonym_id,
                        drs_object_id=asset.drs_object_id,
                        file_type=file_type_enum,
                        wes_run_id=None,
                        state_snapshot="ERROR",
                        error=err,
                    ),
                )
                continue

            context = {
                PLACEHOLDER_DRS_OBJECT_ID: asset.drs_object_id,
                PLACEHOLDER_DRS_STREAM_URL: stream_access.url,
                PLACEHOLDER_PHENOPACKET_ID: pseudonym_id,
                PLACEHOLDER_FILE_TYPE: asset.file_type,
            }
            workflow_params = _apply_placeholders(request.workflow_params_template, context)

            wes_tags = {
                "phenoflow_run_id": str(phenoflow_run_id),
                "pseudonym_id": pseudonym_id,
                "drs_object_id": asset.drs_object_id,
            }

            run_req = RunRequest(
                workflow_type=request.workflow_type,
                workflow_type_version=request.workflow_type_version,
                workflow_url=request.workflow_url,
                workflow_params=workflow_params,
                tags=wes_tags,
            )
            try:
                wes_run_id = await _submit_wes_run(db, run_req)
            except Exception as e:  # noqa: BLE001
                err = (
                    "WES submission failed for "
                    f"pseudonym_id={pseudonym_id!r}, drs_object_id={asset.drs_object_id!r}: {e}"
                )
                errors.append(err)
                db.add(
                    PhenoFlowRunItem(
                        phenoflow_run_id=phenoflow_run_id,
                        pseudonym_id=pseudonym_id,
                        drs_object_id=asset.drs_object_id,
                        file_type=asset.file_type,
                        wes_run_id=None,
                        state_snapshot=State.SYSTEM_ERROR.value,
                        error=err,
                    ),
                )
                items.append(
                    PhenoFlowRunItemSubmission(
                        pseudonym_id=pseudonym_id,
                        drs_object_id=asset.drs_object_id,
                        file_type=file_type_enum,
                        wes_run_id=None,
                        state_snapshot=State.SYSTEM_ERROR.value,
                        error=err,
                    ),
                )
                continue

            db.add(
                PhenoFlowRunItem(
                    phenoflow_run_id=phenoflow_run_id,
                    pseudonym_id=pseudonym_id,
                    drs_object_id=asset.drs_object_id,
                    file_type=asset.file_type,
                    wes_run_id=wes_run_id,
                    state_snapshot=State.QUEUED.value,
                    error=None,
                ),
            )
            submitted_count += 1
            items.append(
                PhenoFlowRunItemSubmission(
                    pseudonym_id=pseudonym_id,
                    drs_object_id=asset.drs_object_id,
                    file_type=file_type_enum,
                    wes_run_id=str(wes_run_id),
                    state_snapshot=State.QUEUED.value,
                    error=None,
                ),
            )

        if pairs_seen > request.limit_matches:
            break

    run.end_time = datetime.now(UTC)

    await db.flush()
    return PhenoFlowRunResponse(
        phenoflow_run_id=str(phenoflow_run_id),
        matched_count=matched_count,
        submitted_count=submitted_count,
        items=items,
        errors=errors,
    )


async def _submit_wes_run(db: AsyncSession, run_req: RunRequest) -> UUID:
    """Submit a WES run and return its UUID."""
    wes_run_id = await create_wes_run(db, run_req, workflow_attachments=None)
    # create_wes_run writes WorkflowRun row + schedules background task but doesn't commit.
    return UUID(str(wes_run_id))
