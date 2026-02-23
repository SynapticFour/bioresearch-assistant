"""DSGVO-compliant pseudonymization service using Microsoft Presidio."""

import asyncio
import hashlib
import logging
from typing import Any

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

from app.core.config import get_settings
from app.core.encryption import decrypt_mapping, encrypt_mapping
from app.services.pseudonymization_recognizers import (
    GERMAN_PATIENT_ID_ENTITY,
    GERMAN_PERSON_DENY_SET,
    GermanPatientIDRecognizer,
)

logger = logging.getLogger(__name__)

# Entities to detect (Presidio built-in + our custom ID)
DEFAULT_ENTITIES = [
    "PERSON",
    "DATE_TIME",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "MEDICAL_LICENSE",
    GERMAN_PATIENT_ID_ENTITY,
]

# Minimum score for an entity to be returned (avoids spurious PERSON e.g. for "Keine")
ANALYZER_SCORE_THRESHOLD = 0.7


def _get_analyzer() -> AnalyzerEngine:
    """Build analyzer with default recognizers plus German patient ID recognizer."""
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
    registry.add_recognizer(GermanPatientIDRecognizer())
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
    engine = _analyzer_engine()
    try:
        raw = engine.analyze(
            text=text,
            language=language,
            entities=DEFAULT_ENTITIES,
        )
    except KeyError:
        logger.warning("Language %r not available for Presidio, falling back to 'en'", language)
        raw = engine.analyze(
            text=text,
            language="en",
            entities=DEFAULT_ENTITIES,
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
