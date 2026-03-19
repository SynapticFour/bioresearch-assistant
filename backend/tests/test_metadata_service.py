"""Tests for MetadataService (DOI, FASTA, VCF)."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    assert result["sequence_length"] == 39
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


@pytest.mark.asyncio
async def test_fasta_parsing_multisequence() -> None:
    """FASTA mit mehreren Sequenzen — erste Header-Zeile wird verwendet."""
    service = MetadataService()
    fasta = ">seq1 Description1 [Homo sapiens]\nATCGATCG\n>seq2 Description2\nGCTAGCTA"
    result = await service.extract_from_fasta(fasta)
    assert result["name"] == "seq1"
    assert "Description1" in result["description"]
    assert result["organism"] == "Homo sapiens"
    assert result["sequence_length"] == 8  # only first sequence before next >


@pytest.mark.asyncio
async def test_vcf_no_samples() -> None:
    """VCF ohne Sample-Spalten."""
    service = MetadataService()
    vcf = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT"
    result = await service.extract_from_vcf_header(vcf)
    assert result["samples"] == []
    assert result.get("format") == "vcf"


@pytest.mark.asyncio
async def test_doi_invalid_returns_none() -> None:
    """Ungültige DOI oder 404 gibt None zurück."""
    from unittest.mock import patch

    service = MetadataService()
    with patch("app.services.metadata_service.httpx.AsyncClient") as MockClient:
        mock_resp = MagicMock(status_code=404)
        mock_get = AsyncMock(return_value=mock_resp)
        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await service.extract_from_doi("10.9999/invalid")
    assert result is None


@pytest.mark.asyncio
async def test_extract_from_doi_empty_returns_none() -> None:
    """Empty or whitespace DOI returns None."""
    service = MetadataService()
    assert await service.extract_from_doi("") is None
    assert await service.extract_from_doi("   ") is None


@pytest.mark.asyncio
async def test_extract_from_doi_exception_returns_none() -> None:
    """When HTTP client raises, extract_from_doi returns None."""
    service = MetadataService()
    with patch("app.services.metadata_service.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(side_effect=Exception("network error"))
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = await service.extract_from_doi("10.1234/real")
    assert result is None


@pytest.mark.asyncio
async def test_extract_from_fasta_no_header_returns_format_only() -> None:
    """FASTA without '>' header returns minimal dict with format/source."""
    service = MetadataService()
    result = await service.extract_from_fasta("not a fasta header\nACGT")
    assert result == {"format": "fasta", "source": "fasta_header"}


@pytest.mark.asyncio
async def test_extract_from_pmid_exception_returns_none() -> None:
    """When PubMed fetch raises, extract_from_pmid returns None."""
    service = MetadataService()
    with patch("app.services.pubmed_service.PubMedService") as MockPubMed:
        mock_instance = MagicMock()
        mock_instance.fetch_article = AsyncMock(side_effect=Exception("API error"))
        MockPubMed.return_value = mock_instance
        result = await service.extract_from_pmid("12345")
    assert result is None


@pytest.mark.asyncio
async def test_extract_from_vcf_contig_line() -> None:
    """VCF with ##contig= lines populates contigs."""
    service = MetadataService()
    vcf = "##fileformat=VCFv4.2\n##contig=chr1\n##contig=chr2\n#CHROM\tPOS\tID"
    result = await service.extract_from_vcf_header(vcf)
    assert result["format"] == "vcf"
    assert len(result["contigs"]) == 2
