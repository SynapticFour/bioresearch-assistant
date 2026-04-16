"""Schemas for terminology mapping overrides."""

from typing import Literal

from pydantic import BaseModel, Field

OverrideModule = Literal["diagnosis", "laboratory"]


class TerminologyOverrideCreate(BaseModel):
    """Create or replace an active mapping override."""

    module: OverrideModule
    raw_id: str = Field(..., min_length=1, max_length=512)
    target_system: str = Field(..., min_length=1, max_length=512)
    target_code: str = Field(..., min_length=1, max_length=256)
    target_display: str | None = Field(default=None, max_length=512)
    notes: str | None = None


class TerminologyOverrideRead(BaseModel):
    """Stored override row."""

    model_config = {"from_attributes": True}

    id: str
    module: str
    raw_id: str
    target_system: str
    target_code: str
    target_display: str | None
    notes: str | None
    is_active: bool
    created_by_user_id: str | None
    created_at: str | None = None


class TerminologyOverrideListResponse(BaseModel):
    """List overrides."""

    items: list[TerminologyOverrideRead]
    total: int
