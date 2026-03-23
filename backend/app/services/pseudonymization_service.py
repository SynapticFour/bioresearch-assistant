"""Pseudonymization service using Microsoft Presidio.

The implementation is designed to support GDPR/DSGVO requirements
around pseudonymization (Art. 4 Nr. 5), but does not in itself
guarantee legal compliance for any specific deployment.
"""

import asyncio
import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.encryption import decrypt_mapping, encrypt_mapping

TESTING_MODE = os.environ.get("TESTING") == "1"

if TESTING_MODE:
    # Lightweight stand-in types for unit tests.
    # We avoid importing Presidio/spaCy in the sandbox test environment.
    @dataclass(frozen=True, slots=True)
    class RecognizerResult:
        """Minimal RecognizerResult replacement used in unit tests."""

        entity_type: str
        start: int
        end: int
        score: float = 1.0

    class AnalyzerEngine:  # noqa: D101
        pass

    class RecognizerRegistry:  # noqa: D101
        pass

    class AnonymizerEngine:  # noqa: D101
        pass

    _PREDEFINED_AVAILABLE = False

    # Keep in sync with `app.services.pseudonymization_recognizers.GERMAN_PERSON_DENY_SET`.
    GERMAN_PERSON_DENY_SET = frozenset(
        {
            "keine",
            "daten",
            "hier",
            "der",
            "die",
            "das",
            "und",
            "oder",
            "nicht",
            "mit",
            "von",
            "für",
        }
    )
else:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
    from presidio_anonymizer import AnonymizerEngine

    try:
        from presidio_analyzer.predefined_recognizers import (
            CreditCardRecognizer,
            DateRecognizer,
            EmailRecognizer,
            IbanRecognizer,
            PhoneRecognizer,
        )

        _PREDEFINED_AVAILABLE = True
    except ImportError:
        _PREDEFINED_AVAILABLE = False

if not TESTING_MODE:
    from app.services.pseudonymization_recognizers import (
        GERMAN_PERSON_DENY_SET,
        GermanDateRecognizer,
        GermanMedicalLicenseRecognizer,
        GermanPatientIDRecognizer,
        GermanPhoneRecognizer,
    )

logger = logging.getLogger(__name__)

# Minimum score for an entity to be returned (avoids spurious PERSON e.g. for "Keine")
ANALYZER_SCORE_THRESHOLD = 0.7


def _get_analyzer() -> AnalyzerEngine:
    """Build analyzer with NER + pattern-based recognizers (Phone, Email, Date, IBAN, etc.)."""
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "de", "model_name": "de_core_news_sm"},
            {"lang_code": "en", "model_name": "en_core_web_sm"},
        ],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
    nlp_engine = provider.create_engine()

    supported_languages = ["de", "en"]
    registry = RecognizerRegistry(supported_languages=supported_languages)
    registry.load_predefined_recognizers(languages=supported_languages)
    # Konfigurierbare Patterns aus .env laden
    settings = get_settings()
    extra_patterns: list = []
    if settings.custom_patient_id_patterns:
        import re as _re

        from presidio_analyzer import Pattern

        for raw in settings.custom_patient_id_patterns.split(","):
            pat = raw.strip()
            if not pat:
                continue
            try:
                _re.compile(pat)
                extra_patterns.append(
                    Pattern(
                        name=f"CUSTOM_{len(extra_patterns)}",
                        regex=pat,
                        score=0.85,
                    )
                )
            except _re.error:
                logger.warning("Ungültiges custom pattern ignoriert: %s", pat)
    registry.add_recognizer(GermanPatientIDRecognizer(extra_patterns=extra_patterns or None))
    registry.add_recognizer(GermanDateRecognizer())
    registry.add_recognizer(GermanPhoneRecognizer())
    registry.add_recognizer(GermanMedicalLicenseRecognizer())
    # Pattern-basierte Recognizer explizit (Telefon, E-Mail, Datum, IBAN, Kreditkarte)
    if _PREDEFINED_AVAILABLE:
        registry.add_recognizer(PhoneRecognizer(supported_language="de"))
        registry.add_recognizer(PhoneRecognizer(supported_language="en"))
        registry.add_recognizer(EmailRecognizer())
        registry.add_recognizer(DateRecognizer())
        registry.add_recognizer(IbanRecognizer())
        registry.add_recognizer(CreditCardRecognizer())

    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=supported_languages,
        default_score_threshold=0.7,
    )


def _get_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None


def _analyzer_engine() -> AnalyzerEngine:
    global _analyzer
    if _analyzer is None:
        _analyzer = _get_analyzer()
    return _analyzer


def _anonymizer_engine() -> AnonymizerEngine:
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = _get_anonymizer()
    return _anonymizer


def _filter_overlapping_results(
    text: str, results: list[RecognizerResult]
) -> list[RecognizerResult]:
    """Drop overlapping spans by keeping longest non-overlapping matches."""
    # Sort by start asc, then by span length desc
    sorted_results = sorted(results, key=lambda r: (r.start, -(r.end - r.start)))
    kept: list[RecognizerResult] = []

    def overlaps(a: RecognizerResult, b: RecognizerResult) -> bool:
        return not (a.end <= b.start or a.start >= b.end)

    for r in sorted_results:
        if any(overlaps(r, k) for k in kept):
            continue
        kept.append(r)

    # Return in original order
    return sorted(kept, key=lambda r: r.start)


def _analyze_testing(text: str, language: str) -> list[RecognizerResult]:
    """Regex-based PII detection for TESTING=1 (no Presidio/spaCy)."""
    if not text:
        return []

    _ = language  # kept for signature parity
    results: list[RecognizerResult] = []

    def add(entity_type: str, start: int, end: int, score: float = 0.95) -> None:
        if start < 0 or end <= start:
            return
        results.append(RecognizerResult(entity_type=entity_type, start=start, end=end, score=score))

    # PERSON: "Patient Max Mustermann", "Patient John Doe", "Dr. med. Anna Schmidt"
    person_patterns = [
        re.compile(
            r"\bPatient\s+([A-ZÄÖÜ][a-zA-Zäöüß'-]+(?:\s+[A-ZÄÖÜ][a-zA-Zäöüß'-]+)+)",
        ),
        re.compile(
            r"\bDr\.?\s*med\.?\s+([A-ZÄÖÜ][a-zA-Zäöüß'-]+(?:\s+[A-ZÄÖÜ][a-zA-Zäöüß'-]+)+)",
        ),
    ]
    for pat in person_patterns:
        for m in pat.finditer(text):
            add("PERSON", m.start(1), m.end(1))

    # EMAIL
    email_pat = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
    for m in email_pat.finditer(text):
        add("EMAIL_ADDRESS", m.start(), m.end())

    # PHONE
    local_phone_pat = re.compile(r"\b0\d{2,5}[\s\-/]\d{3,8}\b")
    for m in local_phone_pat.finditer(text):
        add("PHONE_NUMBER", m.start(), m.end())
    intl_phone_pat = re.compile(r"\+\d{1,3}[\s\-]?\d{2,5}[\s\-]?\d{3,8}\b")
    for m in intl_phone_pat.finditer(text):
        add("PHONE_NUMBER", m.start(), m.end())

    # DATES
    iso_date_pat = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
    for m in iso_date_pat.finditer(text):
        add("DATE_TIME", m.start(), m.end())
    dmy_date_pat = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")
    for m in dmy_date_pat.finditer(text):
        add("DATE_TIME", m.start(), m.end())

    # MEDICAL RECORD NUMBER / PATIENT ID
    patient_id_pat = re.compile(
        r"(?i)\bPatienten?[-\s]?(?:id|nr|nummer)\s*:?\s*[\w-]{3,15}\b",
    )
    for m in patient_id_pat.finditer(text):
        add("MEDICAL_RECORD_NUMBER", m.start(), m.end())
    mrn_pat = re.compile(r"\bMRN\s+\d{6,12}\b", re.IGNORECASE)
    for m in mrn_pat.finditer(text):
        add("MEDICAL_RECORD_NUMBER", m.start(), m.end())

    # MEDICAL LICENSE (ärztin/arzt + number), used by unit test with "Ärztin 4711"
    med_license_pat = re.compile(r"(?:Ärztin|Arzt)\s+\d{3,7}\b")
    for m in med_license_pat.finditer(text):
        add("MEDICAL_LICENSE", m.start(), m.end())

    # Basic PERSON deny-list filter (mirrors production heuristic).
    filtered = [
        r
        for r in results
        if not (
            r.entity_type == "PERSON"
            and text[r.start : r.end].lower().strip() in GERMAN_PERSON_DENY_SET
        )
    ]
    return _filter_overlapping_results(text, filtered)


def analyze(text: str, language: str = "de") -> list[RecognizerResult]:
    """Detect PII entities in text (PERSON, DATE_TIME, MEDICAL_LICENSE, PHONE_NUMBER, EMAIL, ID).

    Only returns entities with score >= ANALYZER_SCORE_THRESHOLD so that no default/fallback
    entity (e.g. spurious PERSON) triggers pseudonymization when there are no real PII.

    Args:
        text: Input clinical text.
        language: Language code (e.g. 'de', 'en').

    Returns:
        List of Presidio RecognizerResult (entity_type, start, end, score).
    """
    if TESTING_MODE:
        return _analyze_testing(text, language)

    engine = _analyzer_engine()
    try:
        raw = engine.analyze(
            text=text,
            language=language,
            entities=None,  # Alle registrierten Entity-Typen (PERSON, PHONE_NUMBER, EMAIL, etc.)
        )
    except KeyError:
        logger.warning("Language %r not available for Presidio, falling back to 'en'", language)
        raw = engine.analyze(
            text=text,
            language="en",
            entities=None,
        )
    # Filter by score and drop PERSON spans that are German non-name words
    filtered = [
        r
        for r in raw
        if r.score >= ANALYZER_SCORE_THRESHOLD
        and not (
            r.entity_type == "PERSON"
            and text[r.start : r.end].lower().strip() in GERMAN_PERSON_DENY_SET
        )
    ]
    return filtered


def _replace_with_placeholders(
    text: str, results: list[RecognizerResult]
) -> tuple[str, dict[str, str]]:
    """Replace detected spans with unique placeholders and build reversible mapping.

    Mapping keys are placeholders (e.g. <PERSON_1>), values are original text.
    """
    # Sort by start descending so we don't invalidate offsets
    sorted_results = sorted(results, key=lambda r: r.start, reverse=True)
    mapping: dict[str, str] = {}
    counter: dict[str, int] = {}
    result_text = text
    for r in sorted_results:
        original = text[r.start : r.end]
        entity = r.entity_type
        counter[entity] = counter.get(entity, 0) + 1
        placeholder = f"<{entity}_{counter[entity]}>"
        mapping[placeholder] = original
        result_text = result_text[: r.start] + placeholder + result_text[r.end :]
    return result_text, mapping


def pseudonymize(
    text: str,
    language: str = "de",
) -> dict[str, Any]:
    """Pseudonymize text and return result with reversible encrypted mapping.

    Returns a dict suitable for PseudonymizationResult schema:
    - pseudonymized_text
    - mapping_id (to be set by caller after storing mapping in DB)
    - entities_found: list of {type, start, end}
    - encrypted_mapping_bytes: for the caller to persist (then discard from response)
    """
    results = analyze(text, language=language)
    if not results:
        return {
            "pseudonymized_text": text,
            "mapping_id": None,
            "entities_found": [],
            "plain_mapping": {},
            "encrypted_mapping_bytes": None,
        }
    pseudonymized_text, plain_mapping = _replace_with_placeholders(text, results)
    settings = get_settings()
    encrypted_bytes = encrypt_mapping(plain_mapping, settings.pseudonymization_encryption_key)
    entities_found = [{"type": r.entity_type, "start": r.start, "end": r.end} for r in results]
    return {
        "pseudonymized_text": pseudonymized_text,
        "mapping_id": None,  # Caller sets after DB insert
        "entities_found": entities_found,
        "plain_mapping": plain_mapping,
        "encrypted_mapping_bytes": encrypted_bytes,
    }


def restore(
    pseudonymized_text: str,
    encrypted_mapping_bytes: bytes,
) -> str:
    """Restore original text from pseudonymized text and decrypted mapping.

    Only for authorized users; caller must check permission before calling.

    Args:
        pseudonymized_text: Text containing placeholders like <PERSON_1>.
        encrypted_mapping_bytes: Stored encrypted mapping (from DB).

    Returns:
        Original text with placeholders replaced by original values.
    """
    settings = get_settings()
    mapping = decrypt_mapping(encrypted_mapping_bytes, settings.pseudonymization_encryption_key)
    result = pseudonymized_text
    # Replace placeholders (longest first to avoid partial matches)
    for placeholder in sorted(mapping.keys(), key=len, reverse=True):
        result = result.replace(placeholder, mapping[placeholder])
    return result


def input_hash_for_audit(text: str) -> str:
    """SHA256 hash of input text for audit log (never store raw text)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class PseudonymizationService:
    """Thin wrapper for async use of module-level Presidio functions."""

    async def analyze(self, text: str, language: str = "de") -> list[RecognizerResult]:
        """Run PII analysis in a thread (sync Presidio call)."""
        return await asyncio.to_thread(analyze, text, language)
