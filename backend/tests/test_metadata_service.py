"""Tests for MetadataService (DOI, FASTA, VCF)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.metadata_service import MetadataService


@pytest.mark.asyncio
async def test_extract_from_fasta() -> None:
    """FASTA header parsing: accession, description, organism, sequence_length."""
    service = MetadataService()
    fasta = ">NM_007294.4 BRCA1 mRNA [Homo sapiens]\nATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAATC"
    result = await service.extract_from_fasta(fasta)
    assert result["name"] == "NM_007294.4"
    assert "BRCA1" in result["description"]
    assert result["organism"] == "Homo sapiens"
    assert result["sequence_length"] == 40
    assert result.get("format") == "fasta"
    assert result.get("source") == "fasta_header"


@pytest.mark.asyncio
async def test_extract_from_vcf_header() -> None:
    """VCF header: reference, samples from #CHROM line."""
    service = MetadataService()
    vcf = (
        "##fileformat=VCFv4.2\n"
        "##reference=GRCh38\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPATIENT-001"
    )
    result = await service.extract_from_vcf_header(vcf)
    assert result["reference"] == "GRCh38"
    assert "PATIENT-001" in result["samples"]
    assert result.get("format") == "vcf"
    assert result.get("source") == "vcf_header"


@pytest.mark.asyncio
async def test_extract_from_doi_mock() -> None:
    """DOI extraction via CrossRef (mocked)."""
    from unittest.mock import patch

    service = MetadataService()
    mock_response = {
        "message": {
            "title": ["BRCA1 Study"],
            "author": [{"family": "Smith", "given": "J"}],
            "published": {"date-parts": [[2024]]},
            "container-title": ["Nature Genetics"],
            "abstract": "Test abstract",
        }
    }
    mock_resp = MagicMock(status_code=200, json=lambda: mock_response)
    mock_get = AsyncMock(return_value=mock_resp)
    mock_client_instance = MagicMock()
    mock_client_instance.get = mock_get
    with patch("app.services.metadata_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await service.extract_from_doi("10.1038/test")
    assert result is not None
    assert result["title"] == "BRCA1 Study"
    assert result["year"] == 2024
    assert result.get("source") == "crossref"
