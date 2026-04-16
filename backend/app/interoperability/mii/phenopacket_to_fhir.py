"""Map Phenopacket v2 JSON (snake_case) to FHIR R4 resource dicts (MII-oriented).

Genomics-Entscheidung: primaer aus Phenopacket-Interpretationen (Gene/Symbole);
tiefe Varianten-HGVS folgen in einer spaeteren Iteration mit normalisierten Genomics-Tabellen.
"""

from __future__ import annotations

import re
from typing import Any

from app.interoperability.mii import constants as mii_c
from app.services.terminology_mapping_service import map_disease_coding, map_lab_assay_coding

_SAFE_ID = re.compile(r"[^A-Za-z0-9\-.]")


def _slug(s: str) -> str:
    return _SAFE_ID.sub("-", s)[:64].strip("-") or "id"


def build_patient(
    pseudonym_id: str, attach_profile: bool, profile_url: str | None
) -> dict[str, Any]:
    """Patient with pseudonym-only identifier (no real PII)."""
    pid = f"patient-{_slug(pseudonym_id)}"
    pat: dict[str, Any] = {
        "resourceType": "Patient",
        "id": pid,
        "identifier": [
            {
                "use": "secondary",
                "type": {
                    "coding": [
                        {
                            "system": "urn:ietf:rfc:3986",
                            "code": "MR",
                            "display": "Medical record number",
                        }
                    ]
                },
                "system": "urn:oid:1.3.6.1.4.1.54851.1",
                "value": pseudonym_id,
            }
        ],
    }
    if attach_profile and profile_url:
        pat["meta"] = {"profile": [profile_url]}
    return pat


def build_conditions_from_diseases(
    pseudonym_id: str,
    patient_ref: str,
    diseases: list[dict[str, Any]],
    attach_profile: bool,
    profile_url: str | None,
    *,
    disease_overrides: dict[str, dict[str, Any]] | None = None,
    recorded_date: str | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, d in enumerate(diseases):
        term = d.get("term") or {}
        oid = term.get("id") or f"UNKNOWN-{i}"
        label = term.get("label") or oid
        cid = f"condition-{_slug(pseudonym_id)}-{i}"
        raw_key = str(oid)
        ov = (disease_overrides or {}).get(raw_key)
        coding, provenance = map_disease_coding(
            term,
            source="phenopacket.diseases.term",
            override_target=ov,
        )
        cond: dict[str, Any] = {
            "resourceType": "Condition",
            "id": cid,
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed",
                    }
                ]
            },
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                            "code": "problem-list-item",
                        }
                    ]
                }
            ],
            "subject": {"reference": patient_ref},
            "code": {
                "coding": [coding],
                "text": label,
            },
            "extension": [
                {
                    "url": "https://synapticfour.com/fhir/StructureDefinition/mapping-provenance",
                    "valueString": f"{provenance['source']}|{provenance['raw_id']}",
                }
            ],
        }
        if d.get("onset"):
            cond["onsetString"] = str(d["onset"])
        if recorded_date:
            cond["recordedDate"] = str(recorded_date)
        if attach_profile and profile_url:
            cond["meta"] = {"profile": [profile_url]}
        out.append(cond)
    return out


def build_observations_from_phenotypes(
    pseudonym_id: str,
    patient_ref: str,
    features: list[dict[str, Any]],
    attach_profile: bool,
    profile_url: str | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, pf in enumerate(features):
        t = pf.get("type") or {}
        hp_id = t.get("id") or f"HP:unknown-{i}"
        label = t.get("label") or hp_id
        obs_id = f"observation-phenotype-{_slug(pseudonym_id)}-{i}"
        hp_code = hp_id.replace("HP:", "") if hp_id.startswith("HP:") else hp_id
        obs: dict[str, Any] = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "exam",
                            "display": "Exam",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://purl.obolibrary.org/obo/hp.owl",
                        "code": hp_code,
                        "display": label,
                    }
                ],
                "text": label,
            },
            "subject": {"reference": patient_ref},
        }
        if attach_profile and profile_url:
            obs["meta"] = {"profile": [profile_url]}
        out.append(obs)
    return out


def build_specimens_from_biosamples(
    pseudonym_id: str,
    patient_ref: str,
    biosamples: list[dict[str, Any]],
    attach_profile: bool,
    profile_url: str | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, bs in enumerate(biosamples):
        bid = bs.get("id") or f"specimen-{i}"
        sid = f"specimen-{_slug(pseudonym_id)}-{i}"
        sp: dict[str, Any] = {
            "resourceType": "Specimen",
            "id": sid,
            "identifier": [{"value": str(bid)}],
            "subject": {"reference": patient_ref},
        }
        st = bs.get("type") or bs.get("sample_type")
        if isinstance(st, dict):
            term = st.get("label") or st.get("id")
            if term:
                sp["type"] = {"text": str(term)}
        elif isinstance(st, str):
            sp["type"] = {"text": st}
        if attach_profile and profile_url:
            sp["meta"] = {"profile": [profile_url]}
        out.append(sp)
    return out


def build_genomic_observations_from_interpretations(
    pseudonym_id: str,
    patient_ref: str,
    interpretations: list[dict[str, Any]],
    attach_profile: bool,
    profile_url: str | None,
) -> list[dict[str, Any]]:
    """Flatten gene/variant findings from Phenopacket interpretations."""
    significance_map = {
        "pathogenic": ("A", "Abnormal"),
        "likely_pathogenic": ("A", "Abnormal"),
        "benign": ("N", "Normal"),
        "likely_benign": ("N", "Normal"),
        "uncertain_significance": ("IND", "Intermediate"),
        "vus": ("IND", "Intermediate"),
    }
    out: list[dict[str, Any]] = []
    n = 0
    for interp in interpretations:
        diag = interp.get("diagnosis") or {}
        for gi in diag.get("genomic_interpretations") or []:
            gene = gi.get("gene") or {}
            sym = gene.get("symbol") or gene.get("value_id")
            if not sym:
                continue
            oid = f"observation-genomics-{_slug(pseudonym_id)}-{n}"
            n += 1
            obs: dict[str, Any] = {
                "resourceType": "Observation",
                "id": oid,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "text": f"Genomic finding: {sym}",
                    "coding": [
                        {
                            "system": mii_c.MII_FHIR_CANONICAL_BASE,
                            "code": "genomic-finding",
                            "display": f"Gene {sym}",
                        }
                    ],
                },
                "subject": {"reference": patient_ref},
                "valueString": str(sym),
            }
            variant_info = gi.get("variant_interpretation") or gi.get("variant") or {}
            components: list[dict[str, Any]] = []
            hgvs = (
                variant_info.get("hgvs") or variant_info.get("hgvs_c") or variant_info.get("hgvs_p")
            )
            if hgvs:
                components.append(
                    {
                        "code": {"text": "HGVS"},
                        "valueString": str(hgvs),
                    }
                )
            significance = (
                variant_info.get("clinical_significance")
                or variant_info.get("acmg_classification")
                or variant_info.get("classification")
            )
            if significance:
                sig_norm = str(significance).strip().lower().replace(" ", "_")
                components.append(
                    {
                        "code": {"text": "Clinical significance"},
                        "valueString": str(significance),
                    }
                )
                if sig_norm in significance_map:
                    code, display = significance_map[sig_norm]
                    obs["interpretation"] = [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                    "code": code,
                                    "display": display,
                                }
                            ]
                        }
                    ]
            if components:
                obs["component"] = components
            obs["extension"] = [
                {
                    "url": "https://synapticfour.com/fhir/StructureDefinition/mapping-provenance",
                    "valueString": "phenopacket.interpretations.diagnosis.genomic_interpretations",
                }
            ]
            if attach_profile and profile_url:
                obs["meta"] = {"profile": [profile_url]}
            out.append(obs)
    return out


def build_laboratory_observations_from_measurements(
    pseudonym_id: str,
    patient_ref: str,
    measurements: list[dict[str, Any]],
    attach_profile: bool,
    profile_url: str | None,
    *,
    lab_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Map Phenopacket measurements to FHIR Observation (laboratory)."""
    interpretation_map = {
        "H": ("H", "High"),
        "L": ("L", "Low"),
        "N": ("N", "Normal"),
        "HH": ("HH", "Critical high"),
        "LL": ("LL", "Critical low"),
        "A": ("A", "Abnormal"),
    }

    def _to_quantity(raw: object) -> dict[str, object] | None:
        if not isinstance(raw, dict):
            return None
        qv = raw.get("value")
        if not isinstance(qv, (int, float)):
            return None
        out_q: dict[str, object] = {"value": qv}
        if raw.get("unit"):
            out_q["unit"] = raw.get("unit")
        if raw.get("system"):
            out_q["system"] = raw.get("system")
        if raw.get("code"):
            out_q["code"] = raw.get("code")
        return out_q

    out: list[dict[str, Any]] = []
    for i, m in enumerate(measurements):
        assay = m.get("assay") or {}
        value = m.get("value") or {}
        unit = value.get("unit") or {}
        obs_id = f"observation-lab-{_slug(pseudonym_id)}-{i}"
        assay_raw = str(assay.get("id") or "")
        ov = (lab_overrides or {}).get(assay_raw) if assay_raw else None
        coding, provenance = map_lab_assay_coding(
            assay,
            source="phenopacket.measurements.assay",
            override_target=ov,
        )
        code_id = assay.get("id") or f"LAB-{i}"
        obs: dict[str, Any] = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [coding],
                "text": assay.get("label") or str(code_id),
            },
            "subject": {"reference": patient_ref},
            "extension": [
                {
                    "url": "https://synapticfour.com/fhir/StructureDefinition/mapping-provenance",
                    "valueString": f"{provenance['source']}|{provenance['raw_id']}",
                }
            ],
        }
        if m.get("time_observed"):
            obs["effectiveDateTime"] = str(m.get("time_observed"))
        elif m.get("effective_date_time"):
            obs["effectiveDateTime"] = str(m.get("effective_date_time"))

        value_number = value.get("quantity", {}).get("value")
        if isinstance(value_number, (int, float)):
            obs["valueQuantity"] = {
                "value": value_number,
                "unit": unit.get("label"),
                "system": unit.get("system"),
                "code": unit.get("code"),
            }
        elif value.get("value") is not None:
            obs["valueString"] = str(value.get("value"))

        ref = m.get("reference_range") or {}
        if isinstance(ref, dict):
            rr: dict[str, Any] = {}
            low = _to_quantity(ref.get("low"))
            high = _to_quantity(ref.get("high"))
            if low:
                rr["low"] = low
            if high:
                rr["high"] = high
            if rr:
                obs["referenceRange"] = [rr]

        interpretation = m.get("interpretation")
        if isinstance(interpretation, str):
            key = interpretation.strip().upper()
            if key in interpretation_map:
                code, display = interpretation_map[key]
                obs["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": code,
                                "display": display,
                            }
                        ]
                    }
                ]

        specimen_id = m.get("specimen_id")
        if specimen_id:
            obs["specimen"] = {"reference": f"Specimen/{specimen_id}"}
        if attach_profile and profile_url:
            obs["meta"] = {"profile": [profile_url]}
        out.append(obs)
    return out


def extract_phenopacket_sections(pp: dict[str, Any]) -> dict[str, Any]:
    """Return lists used for module gating."""
    return {
        "diseases": pp.get("diseases") or [],
        "phenotypic_features": pp.get("phenotypic_features") or [],
        "biosamples": pp.get("biosamples") or [],
        "interpretations": pp.get("interpretations") or [],
        "measurements": pp.get("measurements") or [],
    }
