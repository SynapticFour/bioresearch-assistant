"""Tests for consent and MII export APIs."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.patient_record import PatientRecordModel

FIXTURE_GOLDEN = (
    Path(__file__).resolve().parent / "fixtures" / "mii" / "golden_resource_type_counts.json"
)


@pytest.mark.asyncio
async def test_create_consent_requires_patient(async_client: AsyncClient) -> None:
    """POST /consents returns 404 when pseudonym unknown."""
    resp = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": "nonexistent-pp",
            "policy_version": "2025-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
            "covered_project_ids": ["proj-a"],
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mii_bundle_403_without_consent(async_client: AsyncClient, db_session) -> None:
    """MII export without consent returns 403."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={"pseudonym_ids": [pid], "modules": ["diagnosis"]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mii_bundle_200_with_consent(async_client: AsyncClient, db_session) -> None:
    """MII export succeeds with active consent."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [
                    {
                        "term": {
                            "id": "ORPHA:558",
                            "label": "Test disease",
                            "version": "2026",
                        }
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2025-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
            "covered_project_ids": ["proj-a"],
        },
    )
    assert c.status_code == 201

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={"pseudonym_ids": [pid], "modules": ["diagnosis"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bundle"]["resourceType"] == "Bundle"
    assert data["bundle"]["type"] == "collection"
    assert data["validation_summary"]["ok"] is True
    assert data["validator_ig_package_id"]
    assert data["validator_ig_package_version"]
    assert data["validator_mode"] == "basic"
    condition = next(
        e["resource"]
        for e in data["bundle"]["entry"]
        if e["resource"]["resourceType"] == "Condition"
    )
    assert condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition["verificationStatus"]["coding"][0]["code"] == "confirmed"
    assert condition["category"][0]["coding"][0]["code"] == "problem-list-item"
    assert condition["code"]["coding"][0]["version"] == "2026"
    assert condition["extension"][0]["url"].endswith("mapping-provenance")


@pytest.mark.asyncio
async def test_mii_bundle_laboratory_from_measurements(
    async_client: AsyncClient, db_session
) -> None:
    """Labor module maps Phenopacket measurements to Observation resources."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "measurements": [
                    {
                        "assay": {
                            "id": "LOINC:718-7",
                            "label": "Hemoglobin [Mass/volume]",
                            "version": "2.81",
                        },
                        "time_observed": "2026-01-02T10:15:00Z",
                        "value": {
                            "quantity": {"value": 13.5},
                            "unit": {
                                "label": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL",
                            },
                        },
                        "reference_range": {
                            "low": {
                                "value": 12.0,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL",
                            },
                            "high": {
                                "value": 16.0,
                                "unit": "g/dL",
                                "system": "http://unitsofmeasure.org",
                                "code": "g/dL",
                            },
                        },
                        "interpretation": "N",
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={"pseudonym_ids": [pid], "modules": ["laboratory"]},
    )
    assert resp.status_code == 200
    entries = resp.json()["bundle"]["entry"]
    obs = [e["resource"] for e in entries if e["resource"]["resourceType"] == "Observation"]
    assert len(obs) >= 1
    loinc_obs = next(
        o for o in obs if o.get("code", {}).get("coding", [{}])[0].get("system") == "http://loinc.org"
    )
    assert loinc_obs["effectiveDateTime"] == "2026-01-02T10:15:00Z"
    assert loinc_obs["valueQuantity"]["value"] == 13.5
    assert loinc_obs["code"]["coding"][0]["version"] == "2.81"
    assert loinc_obs["referenceRange"][0]["low"]["value"] == 12.0
    assert loinc_obs["referenceRange"][0]["high"]["value"] == 16.0
    assert loinc_obs["interpretation"][0]["coding"][0]["code"] == "N"
    assert resp.json()["validation_summary"]["terminology_summary"]["known_codings"] >= 1


@pytest.mark.asyncio
async def test_mii_bundle_strict_profile_validation_passes_with_auto_profiles(
    async_client: AsyncClient, db_session
) -> None:
    """Strict profile validation passes because exporter now auto-attaches profiles."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [{"term": {"id": "ORPHA:558", "label": "Test disease"}}],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={
            "pseudonym_ids": [pid],
            "modules": ["diagnosis"],
            "strict_profile_validation": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["validation_summary"]["ok"] is True
    for entry in data["bundle"]["entry"]:
        res = entry["resource"]
        assert "meta" in res
        assert "profile" in res["meta"]


@pytest.mark.asyncio
async def test_mii_export_job_persists_validation_report(
    async_client: AsyncClient, db_session
) -> None:
    """Job endpoint returns dedicated validation report metadata fields after async completion."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [{"term": {"id": "ORPHA:558", "label": "Test disease"}}],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    job_resp = await async_client.post(
        "/api/v1/mii-export/jobs",
        json={
            "pseudonym_ids": [pid],
            "modules": ["diagnosis"],
            "strict_profile_validation": True,
        },
    )
    assert job_resp.status_code == 202
    job_id = job_resp.json()["id"]
    job_data = None
    for _ in range(200):
        poll = await async_client.get(f"/api/v1/mii-export/jobs/{job_id}")
        assert poll.status_code == 200
        job_data = poll.json()
        if job_data["status"] == "succeeded":
            break
        if job_data["status"] in ("failed", "dead_letter"):
            raise AssertionError(job_data)
        await asyncio.sleep(0.02)
    assert job_data is not None
    assert job_data["validation_summary"]["ok"] is True
    assert job_data["validator_mode"] == "strict-profile"
    assert job_data["validator_ig_package_id"]
    assert job_data["validator_ig_package_version"]

    metrics = await async_client.get("/api/v1/mii-export/jobs/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["by_status"].get("succeeded", 0) >= 1


@pytest.mark.asyncio
async def test_mii_bundle_applies_terminology_override(
    async_client: AsyncClient, db_session
) -> None:
    """Governance overrides replace default disease/lab codings in MII bundle."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [
                    {
                        "term": {
                            "id": "ORPHA:558",
                            "label": "Test disease",
                            "version": "2026",
                        }
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()

    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    ov = await async_client.post(
        "/api/v1/terminology/overrides",
        json={
            "module": "diagnosis",
            "raw_id": "ORPHA:558",
            "target_system": "http://snomed.info/sct",
            "target_code": "999001",
            "target_display": "Governed override",
        },
    )
    assert ov.status_code == 201

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={"pseudonym_ids": [pid], "modules": ["diagnosis"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    condition = next(
        e["resource"]
        for e in data["bundle"]["entry"]
        if e["resource"]["resourceType"] == "Condition"
    )
    assert condition["code"]["coding"][0]["system"] == "http://snomed.info/sct"
    assert condition["code"]["coding"][0]["code"] == "999001"
    assert condition["recordedDate"] == "2026-01-01T00:00:00Z"


@pytest.mark.asyncio
async def test_mii_bundle_strict_intention_fields_per_module(
    async_client: AsyncClient, db_session
) -> None:
    """Intention-level check: key MII module fields are present and semantically populated."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [{"term": {"id": "ORPHA:558", "label": "Test disease"}}],
                "measurements": [
                    {
                        "assay": {"id": "LOINC:718-7", "label": "Hemoglobin"},
                        "value": {"quantity": {"value": 13.5}},
                    }
                ],
                "biosamples": [{"id": "B1", "sample_type": "Blood"}],
                "interpretations": [
                    {
                        "diagnosis": {
                            "genomic_interpretations": [
                                {
                                    "gene": {"symbol": "BRCA1", "value_id": "HGNC:1100"},
                                    "variant_interpretation": {
                                        "clinical_significance": "pathogenic"
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()
    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201
    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={
            "pseudonym_ids": [pid],
            "modules": ["diagnosis", "laboratory", "biospecimen", "genomics"],
            "strict_profile_validation": True,
        },
    )
    assert resp.status_code == 200
    b = resp.json()["bundle"]
    resources = [e["resource"] for e in b["entry"]]

    patient = next(r for r in resources if r["resourceType"] == "Patient")
    assert patient["identifier"][0]["value"] == pid

    condition = next(r for r in resources if r["resourceType"] == "Condition")
    assert condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition["verificationStatus"]["coding"][0]["code"] == "confirmed"
    assert condition["recordedDate"] == "2026-01-01T00:00:00Z"

    lab = next(r for r in resources if r["id"].startswith("observation-lab-"))
    assert lab["status"] == "final"
    assert lab["category"][0]["coding"][0]["code"] == "laboratory"
    assert lab["code"]["coding"][0]["system"] == "http://loinc.org"

    specimen = next(r for r in resources if r["resourceType"] == "Specimen")
    assert specimen["subject"]["reference"].startswith("Patient/")
    assert specimen["identifier"][0]["value"] == "B1"

    genomics = next(r for r in resources if r["id"].startswith("observation-genomics-"))
    assert genomics["valueString"] == "BRCA1"
    assert genomics["interpretation"][0]["coding"][0]["code"] == "A"
    assert resp.json()["validation_summary"]["binding_checks"] >= 2


@pytest.mark.asyncio
async def test_mii_bundle_fail_on_partial_mapping_returns_422(
    async_client: AsyncClient, db_session
) -> None:
    """When fail_on_partial_mapping is enabled, missing module source data fails export."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [{"term": {"id": "ORPHA:558", "label": "Test disease"}}],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()
    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={
            "pseudonym_ids": [pid],
            "modules": ["laboratory"],
            "fail_on_partial_mapping": True,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_mii_bundle_genomics_includes_hgvs_and_significance_component(
    async_client: AsyncClient, db_session
) -> None:
    """Genomics mapping carries HGVS and significance details in Observation components."""
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "interpretations": [
                    {
                        "diagnosis": {
                            "genomic_interpretations": [
                                {
                                    "gene": {"symbol": "BRCA1", "value_id": "HGNC:1100"},
                                    "variant_interpretation": {
                                        "hgvs": "NM_007294.4:c.68_69del",
                                        "clinical_significance": "pathogenic",
                                    },
                                }
                            ]
                        }
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()
    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201
    resp = await async_client.post(
        "/api/v1/mii-export/bundles",
        json={"pseudonym_ids": [pid], "modules": ["genomics"]},
    )
    assert resp.status_code == 200
    entries = resp.json()["bundle"]["entry"]
    obs = [e["resource"] for e in entries if e["resource"]["resourceType"] == "Observation"]
    assert len(obs) == 1
    g = obs[0]
    assert any(c.get("valueString") == "NM_007294.4:c.68_69del" for c in g.get("component", []))
    assert any(c.get("valueString") == "pathogenic" for c in g.get("component", []))
    assert g["interpretation"][0]["coding"][0]["code"] == "A"


@pytest.mark.asyncio
async def test_mii_bundle_matches_golden_resource_type_counts(
    async_client: AsyncClient, db_session
) -> None:
    """Golden-ish E2E check: resource type counts per selected module."""
    golden = json.loads(FIXTURE_GOLDEN.read_text(encoding="utf-8"))
    pid = f"test-pp-{uuid4().hex[:8]}"
    db_session.add(
        PatientRecordModel(
            pseudonym_id=pid,
            phenopacket_json={
                "id": pid,
                "subject": {"id": pid},
                "meta_data": {"created": "2026-01-01T00:00:00Z"},
                "diseases": [{"term": {"id": "ORPHA:558", "label": "Test disease"}}],
                "phenotypic_features": [{"type": {"id": "HP:0001250", "label": "Seizures"}}],
                "measurements": [
                    {
                        "assay": {"id": "LOINC:718-7", "label": "Hemoglobin [Mass/volume]"},
                        "value": {"quantity": {"value": 13.5}},
                    }
                ],
                "interpretations": [
                    {
                        "diagnosis": {
                            "genomic_interpretations": [
                                {"gene": {"symbol": "BRCA1", "value_id": "HGNC:1100"}}
                            ]
                        }
                    }
                ],
            },
            user_id="dev-user",
            team_id=None,
        )
    )
    await db_session.commit()
    c = await async_client.post(
        "/api/v1/consents",
        json={
            "pseudonym_id": pid,
            "policy_version": "2026-1",
            "status": "active",
            "valid_from": datetime.now(UTC).isoformat(),
        },
    )
    assert c.status_code == 201

    for module in ("diagnosis", "laboratory", "genomics"):
        resp = await async_client.post(
            "/api/v1/mii-export/bundles",
            json={"pseudonym_ids": [pid], "modules": [module]},
        )
        assert resp.status_code == 200
        entries = resp.json()["bundle"]["entry"]
        counts: dict[str, int] = {}
        for e in entries:
            rt = e["resource"]["resourceType"]
            counts[rt] = counts.get(rt, 0) + 1
        assert counts == golden[module]
