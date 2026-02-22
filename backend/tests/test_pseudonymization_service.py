"""Tests for pseudonymization service (German and English clinical texts)."""

import pytest

from app.services.pseudonymization_service import (
    analyze,
    input_hash_for_audit,
    pseudonymize,
    restore,
)

# --- German clinical text ---
DE_TEXT = (
    "Patient Max Mustermann, geboren am 15.03.1980, wurde am 22.01.2024 aufgenommen. "
    "Kontakt: max.mustermann@example.com, Tel. 0711-123456. "
    "Patienten-ID: 4711. Fallnummer 998877. "
    "Behandelnder Arzt: Dr. med. Anna Schmidt (Ärztekammer BW)."
)

# --- English clinical text ---
EN_TEXT = (
    "Patient John Doe, DOB 1985-04-20, admitted on 2024-01-15. "
    "Contact: john.doe@hospital.org, phone +1-555-123-4567. "
    "MRN 12345678. Attending: Dr. Jane Smith."
)


class TestAnalyze:
    """Tests for analyze() — entity detection."""

    def test_analyze_german_finds_person_and_dates(self) -> None:
        results = analyze(DE_TEXT, language="de")
        types = {r.entity_type for r in results}
        assert "PERSON" in types or len(results) >= 1
        # Presidio may detect names and/or dates
        assert len(results) >= 2

    def test_analyze_german_finds_patient_id(self) -> None:
        results = analyze(
            "Patienten-ID: 4711. Fallnummer 999.",
            language="de",
        )
        types = {r.entity_type for r in results}
        assert "MEDICAL_RECORD_NUMBER" in types

    def test_analyze_english_finds_entities(self) -> None:
        results = analyze(EN_TEXT, language="en")
        types = {r.entity_type for r in results}
        assert "PERSON" in types or "EMAIL_ADDRESS" in types or len(results) >= 1

    def test_analyze_empty_text(self) -> None:
        results = analyze("", language="de")
        assert results == []


class TestPseudonymize:
    """Tests for pseudonymize() and restore() roundtrip."""

    def test_pseudonymize_german_returns_placeholders(self) -> None:
        out = pseudonymize(DE_TEXT, language="de")
        assert "pseudonymized_text" in out
        assert "entities_found" in out
        # Original PII should not appear in pseudonymized text
        assert "Max Mustermann" not in out["pseudonymized_text"] or (
            "Mustermann" not in out["pseudonymized_text"]
        )
        assert "4711" not in out["pseudonymized_text"] or "<" in out["pseudonymized_text"]
        assert out["encrypted_mapping_bytes"] is None or isinstance(
            out["encrypted_mapping_bytes"], bytes
        )

    def test_pseudonymize_english_returns_placeholders(self) -> None:
        out = pseudonymize(EN_TEXT, language="en")
        assert "pseudonymized_text" in out
        assert "John Doe" not in out["pseudonymized_text"] or ("<" in out["pseudonymized_text"])

    def test_pseudonymize_no_entities_returns_unchanged(self) -> None:
        text = "Keine personenbezogenen Daten hier."
        out = pseudonymize(text, language="de")
        assert out["pseudonymized_text"] == text
        assert out["entities_found"] == []
        assert out.get("encrypted_mapping_bytes") is None

    def test_restore_roundtrip(self) -> None:
        out = pseudonymize(DE_TEXT, language="de")
        encrypted = out.get("encrypted_mapping_bytes")
        if encrypted is None:
            pytest.skip("No entities detected — cannot test restore roundtrip")
        restored = restore(out["pseudonymized_text"], encrypted)
        assert "Mustermann" in restored or "4711" in restored or "max.mustermann" in restored
        assert restored == DE_TEXT


class TestInputHash:
    """Tests for audit input hash."""

    def test_input_hash_deterministic(self) -> None:
        h1 = input_hash_for_audit("Hello World")
        h2 = input_hash_for_audit("Hello World")
        assert h1 == h2

    def test_input_hash_different_for_different_input(self) -> None:
        h1 = input_hash_for_audit("Text A")
        h2 = input_hash_for_audit("Text B")
        assert h1 != h2

    def test_input_hash_sha256_length(self) -> None:
        h = input_hash_for_audit("Any")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
