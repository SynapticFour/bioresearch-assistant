"""FHIR bundle validation helpers for MII export."""

from __future__ import annotations

from typing import Any

from app.interoperability.mii import constants as mii_c
from app.interoperability.mii.ig_loader import profile_by_module


def _expected_profile_for_resource(resource: dict[str, Any]) -> str | None:
    rtype = resource.get("resourceType")
    if rtype == "Patient":
        return profile_by_module("person")
    if rtype == "Condition":
        return profile_by_module("diagnosis")
    if rtype == "Specimen":
        return profile_by_module("biospecimen")
    if rtype == "Observation":
        rid = str(resource.get("id", ""))
        categories = resource.get("category") or []
        first_code = ""
        if categories and isinstance(categories, list):
            coding = (categories[0] or {}).get("coding") or []
            if coding:
                first_code = str((coding[0] or {}).get("code") or "")
        if rid.startswith("observation-genomics-"):
            return profile_by_module("genomics")
        if first_code == "laboratory":
            return profile_by_module("laboratory")
        return profile_by_module("phenotype")
    return None


def validate_bundle(
    bundle: dict[str, Any],
    *,
    strict_profile_validation: bool,
) -> dict[str, Any]:
    """Validate generated bundle and return machine-readable report.

    This is an in-process quality gate. External validator_cli remains the source
    of truth for full IG conformance.
    """
    errors: list[str] = []
    warnings: list[str] = []
    checked_resources = 0
    profile_checks = 0
    binding_checks = 0

    if bundle.get("resourceType") != "Bundle":
        errors.append("Bundle.resourceType must be 'Bundle'")
    if bundle.get("type") != "collection":
        errors.append("Bundle.type must be 'collection'")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        errors.append("Bundle.entry must be a non-empty list")
        entries = []

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry[{idx}] must be an object")
            continue
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            errors.append(f"entry[{idx}].resource missing")
            continue
        checked_resources += 1
        if not resource.get("resourceType"):
            errors.append(f"entry[{idx}].resource.resourceType missing")
        if not resource.get("id"):
            errors.append(f"entry[{idx}].resource.id missing")

        expected_profile = _expected_profile_for_resource(resource)
        if strict_profile_validation and expected_profile:
            profile_checks += 1
            profiles = ((resource.get("meta") or {}).get("profile")) or []
            if expected_profile not in profiles:
                errors.append(f"entry[{idx}] missing expected profile {expected_profile}")
        elif strict_profile_validation and expected_profile is None:
            warnings.append(
                f"entry[{idx}] has no mapped module/profile for {resource.get('resourceType')}"
            )

        if strict_profile_validation:
            rtype = resource.get("resourceType")
            if rtype == "Condition":
                binding_checks += 1
                coding = ((resource.get("code") or {}).get("coding") or [{}])[0]
                system = str(coding.get("system") or "")
                allowed = {
                    "http://www.orpha.net",
                    "http://purl.obolibrary.org/obo/mondo.owl",
                    "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                    "http://snomed.info/sct",
                }
                if system not in allowed:
                    errors.append(
                        f"entry[{idx}] Condition.code.system not in allowed binding set: {system}"
                    )
            elif rtype == "Observation":
                rid = str(resource.get("id", ""))
                category = (((resource.get("category") or [{}])[0]).get("coding") or [{}])[0]
                cat_code = str(category.get("code") or "")
                coding = ((resource.get("code") or {}).get("coding") or [{}])[0]
                code_system = str(coding.get("system") or "")
                if rid.startswith("observation-phenotype-"):
                    binding_checks += 1
                    if code_system != "http://purl.obolibrary.org/obo/hp.owl":
                        errors.append(
                            "entry["
                            f"{idx}] phenotype Observation requires HP system, "
                            f"got {code_system}"
                        )
                elif rid.startswith("observation-lab-") or cat_code == "laboratory":
                    binding_checks += 1
                    allowed = {
                        "http://loinc.org",
                        "https://www.medizininformatik-initiative.de/fhir/core",
                    }
                    if code_system not in allowed:
                        errors.append(
                            "entry["
                            f"{idx}] laboratory Observation.code.system not in "
                            f"allowed set: {code_system}"
                        )
                elif rid.startswith("observation-genomics-"):
                    binding_checks += 1
                    if code_system != mii_c.MII_FHIR_CANONICAL_BASE:
                        errors.append(
                            "entry["
                            f"{idx}] genomics Observation.code.system expected "
                            f"{mii_c.MII_FHIR_CANONICAL_BASE}, got {code_system}"
                        )

    return {
        "ok": len(errors) == 0,
        "mode": "strict-profile" if strict_profile_validation else "basic",
        "checked_resources": checked_resources,
        "profile_checks": profile_checks,
        "binding_checks": binding_checks,
        "errors": errors,
        "warnings": warnings,
    }
