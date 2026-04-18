"""Locus (curated RAG) API schemas."""

from pydantic import BaseModel, Field


class LocusRAGRequest(BaseModel):
    """Request for POST /locus/rag."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Frage in natürlicher Sprache",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Anzahl Korpus-Ausschnitte",
    )
    language: str = Field(default="de", description="de | en")
    corpus_ids: list[str] | None = Field(
        default=None,
        description="Optional: nur diese Korpus-IDs (z. B. ga4gh_spec, mii_kds, guidelines)",
    )


class LocusSource(BaseModel):
    """One Locus index chunk used as a source."""

    chunk_id: int
    corpus_id: str
    source_ref: str
    title: str
    similarity_score: float = Field(..., description="Ähnlichkeit 0–100 (approx)")
    used_chars: int = Field(..., description="Zeichen aus content genutzt")


class LocusRAGResponse(BaseModel):
    """Response for POST /locus/rag."""

    answer: str
    sources: list[LocusSource] = Field(default_factory=list)
    question: str
    model_used: str
    context_chunks: int


class LocusStatusResponse(BaseModel):
    """GET /locus/status"""

    locus_enabled: bool
    chunk_count: int
    corpora: list[str] = Field(
        default_factory=list,
        description="Distinct corpus_id values present in the index",
    )
