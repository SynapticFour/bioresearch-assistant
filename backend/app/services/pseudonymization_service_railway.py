"""Railway-stub: Nur Regex-basierte Pseudonymisierung (kein spaCy)."""

import hashlib
import re
from typing import Any

from app.core.config import get_settings
from app.core.encryption import decrypt_mapping, encrypt_mapping

PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"\b[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}\b",
    "DATE": r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
}


def pseudonymize(text: str, language: str = "de") -> dict[str, Any]:
    """Regex-only pseudonymization; same return shape as full service."""
    plain_mapping: dict[str, str] = {}
    result = text
    entities: list[dict[str, Any]] = []

    for entity_type, pattern in PATTERNS.items():
        for match in re.finditer(pattern, result):
            placeholder = f"<{entity_type}_{len(plain_mapping) + 1}>"
            plain_mapping[placeholder] = match.group()
            result = result.replace(match.group(), placeholder, 1)
            entities.append({"type": entity_type, "start": match.start(), "end": match.end()})

    if not entities:
        return {
            "pseudonymized_text": text,
            "mapping_id": None,
            "entities_found": [],
            "plain_mapping": {},
            "encrypted_mapping_bytes": None,
        }

    settings = get_settings()
    encrypted_bytes = encrypt_mapping(plain_mapping, settings.pseudonymization_encryption_key)
    return {
        "pseudonymized_text": result,
        "mapping_id": None,
        "entities_found": entities,
        "plain_mapping": plain_mapping,
        "encrypted_mapping_bytes": encrypted_bytes,
    }


def restore(pseudonymized_text: str, encrypted_mapping_bytes: bytes) -> str:
    """Restore original text from pseudonymized text and decrypted mapping."""
    settings = get_settings()
    mapping = decrypt_mapping(encrypted_mapping_bytes, settings.pseudonymization_encryption_key)
    result = pseudonymized_text
    for placeholder in sorted(mapping.keys(), key=len, reverse=True):
        result = result.replace(placeholder, mapping[placeholder])
    return result


def input_hash_for_audit(text: str) -> str:
    """SHA256 hash of input text for audit log (never store raw text)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
