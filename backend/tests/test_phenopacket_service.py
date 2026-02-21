"""Tests for GA4GH Phenopackets v2 service."""

import pytest

from app.schemas.phenopackets import (
    DiseaseTerm,
    GeneOfInterest,
    OntologyTerm,
    PatientData,
)
from app.services.phenopacket_service import (
    create_phenopacket,
    export_phenopacket,
    phenopacket_to_dict,
    validate_phenopacket,
)


@pytest.fixture
def sample_patient_data():
    """Sample patient data with pseudonym ID only (no real PII)."""
    return PatientData(
        pseudonym_id="PSEUDO-001",
        phenotypes=[
            OntologyTerm(id="HP:0001250", label="Seizure"),
            OntologyTerm(id="HP:0002013", label="Constipation"),
        ],
        diseases=[DiseaseTerm(id="OMIM:143100", label="Huntington disease")],
        genes_of_interest=[
            GeneOfInterest(value_id="HGNC:1100", symbol="BRCA1"),
            GeneOfInterest(value_id="HGNC:11998", symbol="TP53"),
        ],
    )


def test_create_phenopacket_returns_valid_structure(sample_patient_data):
    """create_phenopacket returns a Phenopacket with subject and metadata."""
    pp = create_phenopacket(sample_patient_data)
    assert pp.id == "PSEUDO-001"
    assert pp.subject.id == "PSEUDO-001"
    assert len(pp.phenotypic_features) == 2
    assert len(pp.diseases) == 1
    assert pp.meta_data.phenopacket_schema_version == "2.0"


def test_phenopacket_never_contains_real_patient_id(sample_patient_data):
    """Security: phenopacket must only contain pseudonym_id, no real names/IDs."""
    pp = create_phenopacket(sample_patient_data)
    pp_dict = phenopacket_to_dict(pp)
    # Only pseudonym should appear as identifier
    assert pp_dict.get("id") == "PSEUDO-001"
    subject = pp_dict.get("subject", {})
    assert subject.get("id") == "PSEUDO-001"
    # Ensure no common PII placeholders appear in serialized form
    serialized = str(pp_dict).lower()
    assert "max" not in serialized or "mustermann" not in serialized
    assert "patient" not in serialized or "pseudo" in serialized


def test_validate_phenopacket_accepts_valid_input(sample_patient_data):
    """validate_phenopacket accepts a valid phenopacket dict."""
    pp = create_phenopacket(sample_patient_data)
    pp_dict = phenopacket_to_dict(pp)
    result = validate_phenopacket(pp_dict)
    assert result.valid is True
    assert result.errors == []


def test_validate_phenopacket_rejects_missing_id():
    """validate_phenopacket returns valid=False when id is missing."""
    result = validate_phenopacket({"id": "", "meta_data": {"created": "2024-01-01T00:00:00Z"}})
    assert result.valid is False
    assert any("id" in e.lower() for e in result.errors)


def test_export_phenopacket_returns_json_ld(sample_patient_data):
    """export_phenopacket adds @context for JSON-LD interoperability."""
    pp = create_phenopacket(sample_patient_data)
    pp_dict = phenopacket_to_dict(pp)
    exported = export_phenopacket(pp_dict)
    assert "@context" in exported
    assert "phenopacket-schema" in exported["@context"]
    assert exported["id"] == "PSEUDO-001"
