"""Pydantic schemas for FAIR Data Export."""

from pydantic import BaseModel, Field


class FAIRExportOptions(BaseModel):
    """Options for creating a FAIR-compliant export package."""

    title: str = Field(..., min_length=1, description="Package title")
    description: str = Field(default="", description="Package description")
    authors: list[str] = Field(default_factory=list, description="Author names")
    license: str = Field(default="CC-BY-4.0", description="License identifier")
    identifier: str | None = Field(
        default=None,
        description="Persistent identifier (DOI, Handle, accession) — required for FAIR Findable",
    )
    include_papers: bool = Field(default=True, description="Include linked papers")
    include_phenopackets: bool = Field(default=True, description="Include phenopackets")
    include_notebooks: bool = Field(default=True, description="Include notebooks")
    include_drs: bool = Field(default=False, description="Include DRS files (often large)")
    keywords: list[str] = Field(default_factory=list, description="Keywords")
    funding: str | None = Field(default=None, description="e.g. DFG 123456")


class FAIRComplianceReport(BaseModel):
    """FAIR compliance check result."""

    findable: bool = Field(..., description="F: has DOI/PID or will get one")
    accessible: bool = Field(..., description="A: access described")
    interoperable: bool = Field(..., description="I: standard formats")
    reusable: bool = Field(..., description="R: has license")
    score: int = Field(..., ge=0, le=100, description="Overall score 0-100")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggestions to improve FAIR compliance",
    )
