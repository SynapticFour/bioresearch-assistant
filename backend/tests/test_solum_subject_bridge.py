"""Tests for Solum subject-bridge mapping (org plan F3)."""

from __future__ import annotations

import pytest

from app.services.solum_subject_bridge import build_subject_link_payload


def test_build_subject_link_defaults_subject_to_phenopacket_id() -> None:
    payload = build_subject_link_payload(phenopacket_id="ppkt-001")
    assert payload == {
        "solum_subject_id": "ppkt-001",
        "phenopacket_id": "ppkt-001",
    }


def test_build_subject_link_explicit_subject_and_drs() -> None:
    payload = build_subject_link_payload(
        phenopacket_id="ppkt-001",
        solum_subject_id="subj-clinical-9",
        ferrum_drs_id="drs.example/obj-1",
    )
    assert payload["solum_subject_id"] == "subj-clinical-9"
    assert payload["phenopacket_id"] == "ppkt-001"
    assert payload["ferrum_drs_id"] == "drs.example/obj-1"


def test_build_subject_link_rejects_empty() -> None:
    with pytest.raises(ValueError):
        build_subject_link_payload(phenopacket_id="  ")
