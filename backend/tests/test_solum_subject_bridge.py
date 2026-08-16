"""Tests for Solum subject-bridge mapping (org plan F3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.solum_subject_bridge import build_subject_link_payload


def test_build_subject_link_defaults_subject_to_phenopacket_id() -> None:
    payload = build_subject_link_payload(
        phenopacket_id="ppkt-001",
        actor="researcher/dev-user",
        purpose="research",
    )
    assert payload == {
        "actor": "researcher/dev-user",
        "capability": ["solum:cdr:write"],
        "purpose": "research",
        "solum_subject_id": "ppkt-001",
        "phenopacket_id": "ppkt-001",
    }


def test_build_subject_link_explicit_subject_and_drs() -> None:
    payload = build_subject_link_payload(
        phenopacket_id="ppkt-001",
        actor="practitioner/7",
        purpose="care_provision",
        capability=["solum:cdr:write"],
        solum_subject_id="subj-clinical-9",
        ferrum_drs_id="drs.example/obj-1",
    )
    assert payload["solum_subject_id"] == "subj-clinical-9"
    assert payload["phenopacket_id"] == "ppkt-001"
    assert payload["ferrum_drs_id"] == "drs.example/obj-1"
    assert payload["actor"] == "practitioner/7"
    assert payload["purpose"] == "care_provision"
    assert payload["capability"] == ["solum:cdr:write"]


def test_build_subject_link_rejects_empty() -> None:
    with pytest.raises(ValueError):
        build_subject_link_payload(
            phenopacket_id="  ",
            actor="researcher/dev-user",
            purpose="research",
        )


def test_build_subject_link_rejects_missing_actor_or_purpose() -> None:
    with pytest.raises(ValueError, match="actor"):
        build_subject_link_payload(
            phenopacket_id="ppkt-001",
            actor="  ",
            purpose="research",
        )
    with pytest.raises(ValueError, match="purpose"):
        build_subject_link_payload(
            phenopacket_id="ppkt-001",
            actor="researcher/dev-user",
            purpose="  ",
        )


def test_subject_link_contract_keys_match_solum_adr0003() -> None:
    """Freeze SubjectLinkBody keys against the Solum pin in config/ci/solum-revision.txt."""
    pin = Path(__file__).resolve().parents[2] / "config" / "ci" / "solum-revision.txt"
    text = pin.read_text(encoding="utf-8")
    assert "v0.1.0" in text
    payload = build_subject_link_payload(
        phenopacket_id="ppkt-001",
        actor="researcher/dev-user",
        purpose="research",
        ferrum_drs_id="drs.example/obj-1",
    )
    assert set(payload) >= {
        "actor",
        "capability",
        "purpose",
        "solum_subject_id",
        "phenopacket_id",
        "ferrum_drs_id",
    }
