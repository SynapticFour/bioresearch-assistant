"""Pydantic schemas for research consent API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PurposeCode(BaseModel):
    """FHIR-style coding for consent purpose (e.g. v3-ActReason)."""

    system: str | None = None
    code: str
    display: str | None = None


class ResearchConsentCreate(BaseModel):
    """Create a consent record."""

    pseudonym_id: str = Field(..., min_length=1, max_length=128)
    policy_id: str = Field(default="mii-broad-consent", max_length=128)
    policy_version: str = Field(..., min_length=1, max_length=64)
    status: str = Field(default="draft", pattern="^(draft|active)$")
    valid_from: datetime
    valid_to: datetime | None = None
    covered_project_ids: list[str] = Field(default_factory=list)
    purpose_codes: list[PurposeCode] = Field(default_factory=list)
    source: str = Field(default="manual", pattern="^(manual|import|external_system)$")
    meta_json: dict[str, Any] = Field(default_factory=dict)


class ResearchConsentUpdate(BaseModel):
    """Patch consent (limited fields)."""

    covered_project_ids: list[str] | None = None
    valid_to: datetime | None = None
    meta_json: dict[str, Any] | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|inactive|withdrawn)$")


class ResearchConsentRead(BaseModel):
    """API response for a consent record."""

    model_config = {"from_attributes": True}

    id: UUID
    pseudonym_id: str
    policy_id: str
    policy_version: str
    status: str
    valid_from: datetime
    valid_to: datetime | None
    covered_project_ids: list[Any]
    purpose_codes: list[Any]
    source: str
    meta_json: dict[str, Any]
    user_id: str | None
    team_id: str | None
    created_at: datetime
    updated_at: datetime


class WithdrawConsentBody(BaseModel):
    """Optional body for withdraw."""

    reason: str | None = Field(default=None, max_length=512)
