"""Pydantic models for PubMed article data from NCBI E-utilities."""

from pydantic import BaseModel, Field


class PubMedSearchRequest(BaseModel):
    """Request body for POST /literature/search."""

    query: str = Field(..., min_length=1, description="Search term (e.g. BRCA1 breast cancer)")
    max_results: int = Field(
        default=10, ge=1, le=100, description="Maximum number of papers to return"
    )
    language: str = Field(
        default="de",
        description="Language for KI summary (de, en)",
    )


class PubMedSearchResponse(BaseModel):
    """Response model for literature search and get paper (PMID, title, abstract, summary, etc.)."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(default="", description="Article title")
    abstract: str | None = Field(default=None, description="Abstract text")
    authors: list[str] = Field(default_factory=list, description="Author names")
    year: int | None = Field(default=None, description="Publication year")
    journal: str | None = Field(default=None, description="Journal title")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    summary: str | None = Field(default=None, description="KI-generated summary (if available)")


class LiteratureStatsResponse(BaseModel):
    """Dashboard stats: total papers count and last stored papers."""

    total_papers: int = Field(..., description="Total number of papers stored")
    recent_papers: list[PubMedSearchResponse] = Field(
        default_factory=list,
        description="Last stored papers (newest first)",
    )


class PubMedArticle(BaseModel):
    """Metadata for a single PubMed article.

    Mirrors the main fields returned by NCBI efetch (PubMed XML).
    """

    pmid: str = Field(..., description="PubMed ID (PMID)")
    title: str = Field(default="", description="Article title")
    abstract: str = Field(
        default="", description="Abstract text (may be concatenated from multiple sections)"
    )
    authors: list[str] = Field(
        default_factory=list, description="Author names (e.g. 'LastName ForeName')"
    )
    journal: str = Field(default="", description="Journal title")
    year: int | None = Field(default=None, description="Publication year")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    keywords: list[str] = Field(default_factory=list, description="Keywords or MeSH terms")

    model_config = {"frozen": False}
