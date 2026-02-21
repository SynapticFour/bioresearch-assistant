"""Pydantic schemas for pseudonymization API."""

from pydantic import BaseModel, Field, field_validator


class EntityFound(BaseModel):
    """Single detected entity with type and span."""

    type: str = Field(..., description="Entity type (e.g. PERSON, DATE_TIME)")
    start: int = Field(..., ge=0, description="Start offset in original text")
    end: int = Field(..., ge=0, description="End offset in original text")


class PseudonymizationResult(BaseModel):
    """Result of pseudonymize operation."""

    pseudonymized_text: str = Field(..., description="Text with PII replaced by placeholders")
    mapping_id: str | None = Field(
        None, description="ID to use for restore (only set when entities were found)"
    )
    entities_found: list[EntityFound] = Field(
        default_factory=list,
        description="Detected entities with type and position",
    )


class PseudonymizeRequest(BaseModel):
    """Request body for POST /pseudonymize."""

    text: str = Field(..., min_length=1, description="Clinical text to pseudonymize")
    language: str = Field(default="de", description="Language code (de, en)")

    @field_validator("language")
    @classmethod
    def language_de_or_en(cls, v: str) -> str:
        if v not in ("de", "en"):
            raise ValueError("language must be 'de' or 'en'")
        return v


class RestoreRequest(BaseModel):
    """Request body for POST /pseudonymize/restore."""

    pseudonymized_text: str = Field(..., min_length=1, description="Pseudonymized text")
    mapping_id: str = Field(..., min_length=1, description="Mapping ID from pseudonymize response")


class RestoreResult(BaseModel):
    """Result of restore operation."""

    restored_text: str = Field(..., description="Original text with PII restored")


class AuditLogEntry(BaseModel):
    """Single audit log entry (no raw input)."""

    operation_id: str
    user_id: str | None = None
    timestamp: str  # ISO format
    entities_count: int
    input_hash: str
    operation_type: str

    model_config = {"from_attributes": True}
