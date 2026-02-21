"""AES-256-GCM encryption for pseudonymization mappings (DSGVO)."""

import base64
import logging

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# Nonce size for GCM (96 bits recommended)
NONCE_SIZE = 12


def _get_key_bytes(hex_key: str) -> bytes:
    """Decode 64-char hex string to 32 bytes for AES-256."""
    return bytes.fromhex(hex_key)


def encrypt_mapping(plain_mapping: dict[str, str], hex_key: str) -> bytes:
    """Encrypt a reversible mapping (original -> placeholder) with AES-256-GCM.

    Args:
        plain_mapping: Dict mapping placeholder strings to original PII values.
        hex_key: 64-character hexadecimal encryption key.

    Returns:
        Base64-encoded ciphertext (nonce + ciphertext) for storage.
    """
    import json
    import os

    key = _get_key_bytes(hex_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    plaintext = json.dumps(plain_mapping, ensure_ascii=False).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    payload = nonce + ciphertext
    return base64.b64encode(payload)


def decrypt_mapping(encrypted_payload: bytes, hex_key: str) -> dict[str, str]:
    """Decrypt a stored mapping back to original -> placeholder dict.

    Args:
        encrypted_payload: Base64-encoded bytes (nonce + ciphertext).
        hex_key: 64-character hexadecimal encryption key.

    Returns:
        Dict mapping placeholder strings to original PII values.

    Raises:
        ValueError: If decryption fails (wrong key or tampered data).
    """
    import json

    key = _get_key_bytes(hex_key)
    aesgcm = AESGCM(key)
    try:
        payload = base64.b64decode(encrypted_payload)
    except Exception as e:
        raise ValueError("Invalid base64 payload") from e
    if len(payload) < NONCE_SIZE:
        raise ValueError("Payload too short")
    nonce = payload[:NONCE_SIZE]
    ciphertext = payload[NONCE_SIZE:]
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError("Decryption failed (wrong key or tampered data)") from e
    data: dict[str, str] = json.loads(plaintext.decode("utf-8"))
    return data
