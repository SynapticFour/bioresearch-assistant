"""GA4GH Phenopackets v2 service.

Reference: https://phenopacket-schema.readthedocs.io/
All patient identifiers are pseudonym IDs only.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import google.protobuf
import phenopackets.schema.v2 as pps2
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.timestamp_pb2 import Timestamp

from app.schemas.phenopackets import (
    DiseaseTerm,
    GeneOfInterest,
    OntologyTerm,
    PatientData,
    PatientRecord,
    ValidationResult,
)

logger = logging.getLogger(__name__)

PHENOPACKET_SCHEMA_VERSION = "2.0"


def _default_metadata() -> pps2.MetaData:
    """Build required MetaData with standard ontology resources."""
    meta = pps2.MetaData(
        created_by="BioResearch Assistant",
        phenopacket_schema_version=PHENOPACKET_SCHEMA_VERSION,
    )
    ts = Timestamp()
    ts.FromDatetime(datetime.now(UTC))
    meta.created.CopyFrom(ts)
    meta.resources.extend(
        [
            pps2.Resource(
                id="hp",
                name="Human Phenotype Ontology",
                url="http://purl.obolibrary.org/obo/hp.owl",
                version="2024-01-01",
                namespace_prefix="HP",
                iri_prefix="http://purl.obolibrary.org/obo/HP_",
            ),
            pps2.Resource(
                id="omim",
                name="Online Mendelian Inheritance in Man",
                url="https://omim.org/",
                namespace_prefix="OMIM",
                iri_prefix="https://omim.org/entry/",
            ),
            pps2.Resource(
                id="orphanet",
                name="Orphanet",
                url="https://www.orpha.net/",
                namespace_prefix="Orphanet",
                iri_prefix="https://www.orpha.net/consor/cgi-bin/",
            ),
            pps2.Resource(
                id="hgnc",
                name="HUGO Gene Nomenclature Committee",
                url="https://www.genenames.org/",
                namespace_prefix="HGNC",
                iri_prefix="https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/",
            ),
        ]
    )
    return meta


def create_phenopacket(patient_data: PatientData) -> pps2.Phenopacket:
    """Build a GA4GH Phenopacket v2 from PatientData (pseudonym_id only).

    Args:
        patient_data: Pseudonym ID, HPO phenotypes, OMIM/Orphanet diseases, genes of interest.

    Returns:
        Phenopacket protobuf message.
    """
    subject = pps2.Individual(id=patient_data.pseudonym_id)
    phenotypic_features: list[pps2.PhenotypicFeature] = []
    for p in patient_data.phenotypes:
        pf = pps2.PhenotypicFeature()
        pf.type.CopyFrom(pps2.OntologyClass(id=p.id, label=p.label or p.id))
        phenotypic_features.append(pf)

    diseases: list[pps2.Disease] = []
    for d in patient_data.diseases:
        disease = pps2.Disease()
        disease.term.CopyFrom(pps2.OntologyClass(id=d.id, label=d.label or d.id))
        diseases.append(disease)

    meta = _default_metadata()
    pp = pps2.Phenopacket(
        id=patient_data.pseudonym_id,
        subject=subject,
        phenotypic_features=phenotypic_features,
        diseases=diseases,
        meta_data=meta,
    )

    if patient_data.genes_of_interest:
        try:
            interp = pps2.Interpretation(
                id=f"{patient_data.pseudonym_id}-interpretation-1",
                progress_status=pps2.ProgressStatus.UNKNOWN_PROGRESS,
            )
            diag = pps2.Diagnosis()
            diag.disease.CopyFrom(
                pps2.OntologyClass(id="MONDO:0000001", label="disease or disorder")
            )
            for g in patient_data.genes_of_interest:
                gi = pps2.GenomicInterpretation()
                gi.gene.CopyFrom(pps2.GeneDescriptor(value_id=g.value_id, symbol=g.symbol))
                diag.genomic_interpretations.append(gi)
            interp.diagnosis.CopyFrom(diag)
            pp.interpretations.append(interp)
        except AttributeError:
            logger.debug(
                "Interpretation/GenomicInterpretation not available in this phenopackets version"
            )

    return pp


def validate_phenopacket(phenopacket: dict) -> ValidationResult:
    """Validate a phenopacket dict against Phenopackets v2 schema.

    Args:
        phenopacket: JSON/dict representation of a phenopacket.

    Returns:
        ValidationResult with valid flag and any error messages.
    """
    try:
        pp = ParseDict(phenopacket, pps2.Phenopacket())
        if not pp.id:
            return ValidationResult(valid=False, errors=["Missing required field: id"])
        if not pp.meta_data.HasField("created"):
            return ValidationResult(valid=False, errors=["Missing required meta_data.created"])
        return ValidationResult(valid=True, errors=[])
    except Exception as e:
        logger.debug("Phenopacket validation failed: %s", e)
        return ValidationResult(valid=False, errors=[str(e)])


def phenopacket_to_internal(phenopacket: pps2.Phenopacket) -> PatientRecord:
    """Convert a Phenopacket to internal PatientRecord (pseudonym_id, phenotypes, diseases, genes).

    Args:
        phenopacket: Phenopacket protobuf message.

    Returns:
        PatientRecord for storage/API.
    """
    pseudonym_id = phenopacket.id or (phenopacket.subject.id if phenopacket.subject else "")

    phenotypes: list[OntologyTerm] = []
    for pf in phenopacket.phenotypic_features:
        if pf.type.id:
            phenotypes.append(OntologyTerm(id=pf.type.id, label=pf.type.label or None))

    diseases: list[DiseaseTerm] = []
    for d in phenopacket.diseases:
        if d.term.id:
            diseases.append(DiseaseTerm(id=d.term.id, label=d.term.label or None))

    genes_of_interest: list[GeneOfInterest] = []
    try:
        for interp in phenopacket.interpretations:
            if interp.diagnosis:
                for gi in interp.diagnosis.genomic_interpretations:
                    if gi.gene.value_id and gi.gene.symbol:
                        genes_of_interest.append(
                            GeneOfInterest(value_id=gi.gene.value_id, symbol=gi.gene.symbol)
                        )
    except AttributeError:
        pass

    return PatientRecord(
        pseudonym_id=pseudonym_id,
        phenotypes=phenotypes,
        diseases=diseases,
        genes_of_interest=genes_of_interest,
    )


def _message_to_dict_compat(message: pps2.Phenopacket) -> dict[str, Any]:
    """MessageToDict compatible with protobuf 4.x and 5.x."""
    major = int(google.protobuf.__version__.split(".")[0])
    if major >= 5:
        return MessageToDict(
            message,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=False,
        )
    return MessageToDict(
        message,
        preserving_proto_field_name=True,
        including_default_value_fields=False,
    )


def phenopacket_to_dict(phenopacket: pps2.Phenopacket) -> dict[str, Any]:
    """Serialize Phenopacket to dict (JSON-LD compatible)."""
    return _message_to_dict_compat(phenopacket)


def dict_to_phenopacket(data: dict[str, Any]) -> pps2.Phenopacket:
    """Deserialize dict to Phenopacket."""
    return ParseDict(data, pps2.Phenopacket())


def export_phenopacket(phenopacket_dict: dict[str, Any]) -> dict[str, Any]:
    """Export a stored phenopacket as JSON-LD (dict for HTTP response).

    Args:
        phenopacket_dict: Stored phenopacket as dict (from DB).

    Returns:
        Same dict, optionally with JSON-LD @context for interoperability.
    """
    out = dict(phenopacket_dict)
    if "@context" not in out:
        out["@context"] = "https://phenopacket-schema.readthedocs.io/en/latest/"
    return out
