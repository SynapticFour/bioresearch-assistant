"""Terminology mapping helpers with lightweight provenance metadata."""

from __future__ import annotations

from typing import Any


def map_disease_coding(
    term: dict[str, Any],
    *,
    source: str,
    override_target: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map disease term id to FHIR Coding + provenance."""
    raw_id = str(term.get("id") or "")
    version = term.get("version") or term.get("ontology_version")
    display = term.get("label") or raw_id or "unknown"

    if override_target:
        coding = {
            "system": override_target["system"],
            "code": override_target["code"],
            "display": override_target.get("display") or display,
        }
        if version and "version" not in coding:
            coding["version"] = str(version)
        provenance = {
            "source": source,
            "raw_id": raw_id,
            "mapped_system": coding["system"],
            "mapped_code": coding["code"],
            "version": str(version) if version else None,
            "governance_override": True,
        }
        return coding, provenance

    system = "http://purl.obolibrary.org/obo/mondo.owl"
    code = raw_id or "UNKNOWN"
    if raw_id.startswith("ORPHA:"):
        system = "http://www.orpha.net"
        code = raw_id.replace("ORPHA:", "")
    elif raw_id.startswith("MONDO:"):
        system = "http://purl.obolibrary.org/obo/mondo.owl"
        code = raw_id.replace("MONDO:", "")
    elif raw_id.startswith("ICD10:") or raw_id.startswith("ICD-10:"):
        system = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
        code = raw_id.split(":", 1)[1]
    elif raw_id.startswith("SNOMED:") or raw_id.startswith("SNOMEDCT:"):
        system = "http://snomed.info/sct"
        code = raw_id.split(":", 1)[1]

    coding: dict[str, Any] = {
        "system": system,
        "code": code,
        "display": display,
    }
    if version:
        coding["version"] = str(version)
    provenance = {
        "source": source,
        "raw_id": raw_id,
        "mapped_system": system,
        "mapped_code": code,
        "version": str(version) if version else None,
    }
    return coding, provenance


def map_lab_assay_coding(
    assay: dict[str, Any],
    *,
    source: str,
    override_target: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map assay id to FHIR Coding + provenance."""
    raw_id = str(assay.get("id") or "")
    version = assay.get("version") or assay.get("coding_version")
    display = assay.get("label") or raw_id or "lab-assay"

    if override_target:
        coding = {
            "system": override_target["system"],
            "code": override_target["code"],
            "display": override_target.get("display") or display,
        }
        if version:
            coding["version"] = str(version)
        provenance = {
            "source": source,
            "raw_id": raw_id,
            "mapped_system": coding["system"],
            "mapped_code": coding["code"],
            "version": str(version) if version else None,
            "governance_override": True,
        }
        return coding, provenance

    if raw_id.upper().startswith("LOINC:"):
        system = "http://loinc.org"
        code = raw_id.replace("LOINC:", "")
    else:
        system = "https://www.medizininformatik-initiative.de/fhir/core"
        code = raw_id or "LAB-UNKNOWN"

    coding: dict[str, Any] = {
        "system": system,
        "code": code,
        "display": display,
    }
    if version:
        coding["version"] = str(version)
    provenance = {
        "source": source,
        "raw_id": raw_id,
        "mapped_system": system,
        "mapped_code": code,
        "version": str(version) if version else None,
    }
    return coding, provenance


def summarize_coding_quality(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Build lightweight terminology quality summary over mapped resources."""
    known_system_prefixes = (
        "http://loinc.org",
        "http://snomed.info/sct",
        "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
        "http://www.orpha.net",
        "http://purl.obolibrary.org/obo/mondo.owl",
    )
    total_codings = 0
    known_codings = 0
    codings_per_system: dict[str, int] = {}
    with_version = 0

    for resource in resources:
        code = resource.get("code") or {}
        coding_list = code.get("coding") or []
        for coding in coding_list:
            total_codings += 1
            system = str(coding.get("system") or "")
            codings_per_system[system] = codings_per_system.get(system, 0) + 1
            if any(system.startswith(prefix) for prefix in known_system_prefixes):
                known_codings += 1
            if coding.get("version"):
                with_version += 1

    return {
        "total_codings": total_codings,
        "known_codings": known_codings,
        "known_ratio": (known_codings / total_codings) if total_codings else 1.0,
        "with_version": with_version,
        "systems": codings_per_system,
    }
