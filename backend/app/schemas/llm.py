"""Pydantic models for LLM outputs (summaries, entity extraction)."""

from pydantic import BaseModel, Field


class PaperSummary(BaseModel):
    """Structured summary of a research paper (from abstract + optional context)."""

    summary: str = Field(..., description="2-3 sentence summary of the paper")
    key_findings: list[str] = Field(
        default_factory=list,
        description="List of main findings or conclusions",
    )
    methods: list[str] = Field(
        default_factory=list,
        description="List of methods or approaches used",
    )
    relevance_score: float | None = Field(
        default=None,
        description="Relevance to given context, 0.0 to 1.0 (only when context was provided)",
        ge=0.0,
        le=1.0,
    )


class BiologicalEntities(BaseModel):
    """Extracted biological/named entities from text."""

    genes: list[str] = Field(default_factory=list, description="Gene names/symbols")
    proteins: list[str] = Field(default_factory=list, description="Protein names")
    diseases: list[str] = Field(default_factory=list, description="Diseases or conditions")
    organisms: list[str] = Field(default_factory=list, description="Organisms (species, etc.)")
    chemicals: list[str] = Field(default_factory=list, description="Chemicals, compounds, drugs")
