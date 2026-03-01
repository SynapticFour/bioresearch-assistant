"""Pydantic schemas for BLAST search API and results (Biopython NCBIXML)."""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BLASTParams(BaseModel):
    """Parameters for a BLAST search (passed to Nextflow workflow)."""

    database: str = Field(default="nt", description="BLAST database: nt, nr, or custom name")
    evalue: float = Field(default=0.001, ge=0.0, description="E-value threshold")
    max_hits: int = Field(default=10, ge=1, le=500, description="Maximum number of hit sequences")
    sequence_type: str = Field(
        default="auto",
        description="nucleotide | protein | auto (detect from query)",
    )
    db_path: str | None = Field(
        default=None, description="Optional full path to BLAST DB (else database name used)"
    )


class HSP(BaseModel):
    """High-scoring pair (single alignment)."""

    score: float = Field(..., description="Bit score")
    expect: float | None = Field(default=None, description="E-value")
    identities: int | None = Field(default=None, description="Number of identities")
    align_length: int | None = Field(default=None, description="Alignment length")
    query_start: int | None = Field(default=None)
    query_end: int | None = Field(default=None)
    hit_start: int | None = Field(default=None)
    hit_end: int | None = Field(default=None)
    query: str | None = Field(default=None, description="Query sequence fragment")
    match: str | None = Field(default=None, description="Match string")
    hit: str | None = Field(default=None, description="Hit sequence fragment")


class BLASTHit(BaseModel):
    """Single BLAST hit (one target sequence)."""

    hit_id: str = Field(..., description="Hit accession/ID")
    hit_def: str | None = Field(default=None, description="Hit definition line")
    hit_len: int | None = Field(default=None, description="Hit sequence length")
    hsps: list[HSP] = Field(default_factory=list, description="High-scoring pairs for this hit")


class BLASTStatistics(BaseModel):
    """BLAST run statistics (from BlastOutput)."""

    database: str | None = Field(default=None, description="Database name")
    program: str | None = Field(default=None, description="blastn/blastp etc.")
    version: str | None = Field(default=None, description="BLAST version")
    num_sequences: int | None = Field(default=None, description="Number of query sequences")
    num_hits: int = Field(default=0, description="Total number of hits")
    top_hit_ids: list[str] = Field(
        default_factory=list, description="Top hit accessions (for summary)"
    )


class BLASTResults(BaseModel):
    """Parsed BLAST results (from results.xml via Biopython)."""

    run_id: str = Field(..., description="WES run_id for this BLAST run")
    hits: list[BLASTHit] = Field(default_factory=list, description="All BLAST hits")
    statistics: BLASTStatistics = Field(
        default_factory=BLASTStatistics, description="Run statistics"
    )
    raw_outputs: dict[str, Any] | None = Field(
        default=None, description="Optional paths/snippets (results.xml, results.tsv, summary.json)"
    )


class PaperRef(BaseModel):
    """Paper reference for BLAST ↔ Literature Mining (subset of Paper)."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(default="", description="Article title")
    abstract: str = Field(default="", description="Abstract text")
    authors: list[str] = Field(default_factory=list, description="Author names")
    year: str | None = Field(default=None, description="Publication year")
    journal: str = Field(default="", description="Journal title")
    doi: str | None = Field(default=None, description="DOI")


# IUPAC nucleotide and amino acid single-letter codes (injection-safe for BLAST)
_BLAST_SEQUENCE_PATTERN = re.compile(
    r"^[A-Z\s\-*]+$",
    re.IGNORECASE,
)


class BLASTSearchRequest(BaseModel):
    """Request body for POST /api/v1/blast/search."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=100_000,
        description="DNA/Protein sequence (FASTA or raw)",
    )
    database: str = Field(default="nt", description="BLAST database: nt, nr, or custom")

    @field_validator("query")
    @classmethod
    def validate_sequence(cls, v: str) -> str:
        """Only allow valid IUPAC nucleotide/amino acid characters (injection prevention)."""
        lines = [line for line in v.splitlines() if not line.strip().startswith(">")]
        seq = "".join(lines).upper().replace(" ", "").replace("\t", "")
        if not seq:
            raise ValueError("Sequence is empty after removing FASTA headers")
        if not _BLAST_SEQUENCE_PATTERN.match(seq):
            raise ValueError(
                "Sequence contains invalid characters. "
                "Only IUPAC nucleotide/amino acid codes (A-Z, -, *) allowed."
            )
        return v

    evalue: float | None = Field(default=None, ge=0.0)
    max_hits: int | None = Field(default=None, ge=1, le=500)
    sequence_type: str | None = Field(default="auto")
    db_path: str | None = Field(default=None)


class BLASTSearchResponse(BaseModel):
    """Response for POST /api/v1/blast/search."""

    run_id: str = Field(..., description="WES run_id; poll GET .../results/{run_id} for results")


class BLASTResultsResponse(BaseModel):
    """Response for GET /api/v1/blast/results/{run_id} (optionally with papers)."""

    results: BLASTResults = Field(..., description="Parsed BLAST results")
    papers: list[PaperRef] | None = Field(
        default=None, description="Related papers from Literature Mining (if ?papers=true)"
    )
