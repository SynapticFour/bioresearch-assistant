"""Pydantic schemas for PhenoFlow (Search-to-Execution bridge)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PhenopacketAssetFileType(str, Enum):
    """Supported genomics asset types for PhenoFlow mapping."""

    bam = "bam"
    cram = "cram"
    vcf = "vcf"
    fastq = "fastq"
    other = "other"


class PhenopacketAssetLinkRequest(BaseModel):
    """Link a DRS object to a stored Phenopacket (by pseudonym_id)."""

    drs_object_id: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="DRS object_id (relative path under drs_storage_path).",
    )
    file_type: PhenopacketAssetFileType = Field(
        ...,
        description="Type hint used to build workflow input parameters.",
    )


class PhenopacketAssetLinkResponse(BaseModel):
    """Response for asset-link creation."""

    asset_id: int = Field(..., description="Database id of the asset mapping")
    pseudonym_id: str
    drs_object_id: str
    file_type: PhenopacketAssetFileType


class PhenopacketAssetSummary(BaseModel):
    """Asset summary for UI listing."""

    asset_id: int
    drs_object_id: str
    file_type: PhenopacketAssetFileType


class PhenoFlowRunRequest(BaseModel):
    """Submit a Search-to-Execution request.

    v0.1 is intentionally narrow:
        * query matches only locally stored Phenopackets (patient_records)
        * matches must have a linked DRS asset in phenopacket_assets
        * system submits a WES RunRequest per matched Phenopacket-asset pair
    """

    hpo_terms: list[str] = Field(
        ...,
        min_length=1,
        description="HPO term CURIEs (e.g. ['HP:0001250']).",
    )
    file_type: PhenopacketAssetFileType | None = Field(
        default=None,
        description="Optional filter on linked asset type (bam/cram/vcf/fastq).",
    )
    limit_matches: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Max number of matched Phenopacket-asset pairs to submit.",
    )

    workflow_url: str = Field(
        ...,
        min_length=1,
        description="Workflow descriptor or local .nf path (validated by WES service).",
    )
    workflow_type: str = Field(
        default="NEXTFLOW",
        description="GA4GH WES workflow_type descriptor (e.g. NEXTFLOW, CWL, WDL).",
    )
    workflow_type_version: str = Field(
        default="DSL2",
        description="GA4GH WES workflow_type_version descriptor (e.g. DSL2).",
    )
    workflow_params_template: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Template for workflow_params. String values may contain placeholders: "
            "{{drs_object_id}}, {{drs_stream_url}}, {{pseudonym_id}}, {{file_type}}."
        ),
    )

    @field_validator("hpo_terms")
    @classmethod
    def validate_hpo_terms(cls, value: list[str]) -> list[str]:
        """Require canonical HPO CURIE format and normalize case."""
        pattern = re.compile(r"^HP:\d{7}$")
        normalized = [term.strip().upper() for term in value if term and term.strip()]
        if not normalized:
            raise ValueError("At least one HPO term is required.")
        invalid = [term for term in normalized if not pattern.match(term)]
        if invalid:
            raise ValueError(
                "Invalid HPO terms: "
                + ", ".join(invalid)
                + ". Expected format HP:0000001 (7 digits)."
            )
        return sorted(set(normalized))


class PhenoFlowRunItemSubmission(BaseModel):
    """Per-match submission record returned for POST /phenoflow/runs."""

    pseudonym_id: str
    drs_object_id: str
    file_type: PhenopacketAssetFileType
    wes_run_id: str | None = None
    state_snapshot: str
    error: str | None = None


class PhenoFlowRunResponse(BaseModel):
    """Summary response for submitted PhenoFlow run."""

    phenoflow_run_id: str
    matched_count: int
    submitted_count: int
    items: list[PhenoFlowRunItemSubmission] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PhenoFlowRunItemResponse(BaseModel):
    """Item-level provenance included in GET /phenoflow/runs/{id}."""

    pseudonym_id: str
    drs_object_id: str
    file_type: PhenopacketAssetFileType
    wes_run_id: str | None = None
    state_snapshot: str
    error: str | None = None
    created_at: str | None = None


class PhenoFlowRunDetailResponse(BaseModel):
    """Detailed PhenoFlow run response."""

    phenoflow_run_id: str
    status: str
    query_spec: dict[str, Any]
    workflow_spec: dict[str, Any]
    items: list[PhenoFlowRunItemResponse] = Field(default_factory=list)


class PhenoFlowRunListItem(BaseModel):
    """List item for GET /phenoflow/runs."""

    phenoflow_run_id: str
    status: str
    created_at: str | None = None
    matched_count: int
    submitted_count: int


class PhenoFlowRunListResponse(BaseModel):
    """Paginated-like response for listing PhenoFlow runs."""

    items: list[PhenoFlowRunListItem] = Field(default_factory=list)
