"""Schemas for MII-KDS FHIR bundle export."""

from typing import Any, Literal

from pydantic import BaseModel, Field


MiiModule = Literal["diagnosis", "laboratory", "biospecimen", "genomics"]


class MiiBundleExportRequest(BaseModel):
    """Body for synchronous MII bundle export."""

    pseudonym_ids: list[str] = Field(..., min_length=1)
    policy_id: str | None = Field(
        default=None,
        description="Consent policy to check (default: server MII_DEFAULT_CONSENT_POLICY_ID).",
    )
    modules: list[MiiModule] = Field(
        default_factory=lambda: ["diagnosis", "laboratory", "biospecimen", "genomics"]
    )
    research_project_ids: list[str] = Field(
        default_factory=list,
        description="If non-empty, active consent must cover all these project ids.",
    )
    fail_on_partial_mapping: bool = Field(
        default=False,
        description="If true, return 422 when phenopacket data cannot be mapped for a module.",
    )
    strict_profile_validation: bool = Field(
        default=False,
        description=(
            "If true, require expected profile canonical in resource.meta.profile "
            "for mapped modules."
        ),
    )


class MiiBundleExportResponse(BaseModel):
    """FHIR Bundle as JSON (dict)."""

    bundle: dict[str, Any]
    consent_check_summary: dict[str, Any]
    validation_summary: dict[str, Any]
    validator_ig_package_id: str
    validator_ig_package_version: str
    validator_mode: str
    profile_set_version: str


class MiiExportJobCreate(BaseModel):
    """Create async export job (persists artifact)."""

    pseudonym_ids: list[str] = Field(..., min_length=1)
    policy_id: str | None = None
    modules: list[MiiModule] = Field(default_factory=list)
    research_project_ids: list[str] = Field(default_factory=list)
    fail_on_partial_mapping: bool = False
    strict_profile_validation: bool = False


class MiiExportJobRead(BaseModel):
    """Job status."""

    model_config = {"from_attributes": True}

    id: str
    status: str
    error_message: str | None
    consent_check_summary: dict[str, Any] | None
    validation_summary: dict[str, Any] | None = None
    validator_ig_package_id: str | None = None
    validator_ig_package_version: str | None = None
    validator_mode: str | None = None
    artifact_id: str | None = None
    created_at: str | None = None
    finished_at: str | None = None
    attempt_count: int | None = None
    max_attempts: int | None = None
    next_run_at: str | None = None


class MiiExportJobMetricsRead(BaseModel):
    """Per-user job counts by status."""

    by_status: dict[str, int] = Field(default_factory=dict)
