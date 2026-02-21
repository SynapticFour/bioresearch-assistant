"""Pydantic schemas for GA4GH Phenopackets v2 API.

Align with https://phenopacket-schema.readthedocs.io/
Patient identifiers are always pseudonym IDs; no real patient data.
"""

from pydantic import BaseModel, Field

# --- Input: internal representation for creating a phenopacket ---


class OntologyTerm(BaseModel):
    """Ontology term (e.g. HPO phenotype)."""

    id: str = Field(..., description="CURIE (e.g. HP:0004444)")
    label: str | None = Field(None, description="Human-readable label")


class DiseaseTerm(BaseModel):
    """Disease term (OMIM, Orphanet, MONDO, etc.)."""

    id: str = Field(..., description="CURIE (e.g. OMIM:164400, Orphanet:710)")
    label: str | None = Field(None, description="Human-readable label")


class GeneOfInterest(BaseModel):
    """Gene of interest (HGNC or symbol)."""

    value_id: str = Field(..., description="CURIE (e.g. HGNC:3477)")
    symbol: str = Field(..., description="Gene symbol (e.g. ETF1)")


class PatientData(BaseModel):
    """Input for creating a phenopacket. All identifiers are pseudonym IDs."""

    pseudonym_id: str = Field(
        ..., min_length=1, description="Pseudonymized patient ID (no real PII)"
    )
    phenotypes: list[OntologyTerm] = Field(
        default_factory=list,
        description="HPO phenotypic features",
    )
    diseases: list[DiseaseTerm] = Field(
        default_factory=list,
        description="Diseases (OMIM, Orphanet, MONDO)",
    )
    genes_of_interest: list[GeneOfInterest] = Field(
        default_factory=list,
        description="Genes of interest (e.g. HGNC)",
    )


# --- Validation ---


class ValidationResult(BaseModel):
    """Result of phenopacket schema validation."""

    valid: bool = Field(..., description="True if phenopacket is valid")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")


# --- Internal record (stored in DB, keyed by pseudonym_id) ---


class PatientRecord(BaseModel):
    """Internal patient record derived from or used to build a phenopacket."""

    pseudonym_id: str = Field(..., description="Pseudonymized patient ID")
    phenotypes: list[OntologyTerm] = Field(default_factory=list)
    diseases: list[DiseaseTerm] = Field(default_factory=list)
    genes_of_interest: list[GeneOfInterest] = Field(default_factory=list)
