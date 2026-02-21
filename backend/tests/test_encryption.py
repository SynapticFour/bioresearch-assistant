"""Tests for AES-256 mapping encryption."""

import os

os.environ.setdefault("PSEUDONYMIZATION_ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/d")

import pytest

from app.core.encryption import decrypt_mapping, encrypt_mapping


def test_encrypt_decrypt_roundtrip() -> None:
    key = "a" * 64
    mapping = {"<PERSON_1>": "Max Mustermann", "<DATE_TIME_1>": "15.03.1980"}
    encrypted = encrypt_mapping(mapping, key)
    assert isinstance(encrypted, bytes)
    decrypted = decrypt_mapping(encrypted, key)
    assert decrypted == mapping


def test_decrypt_wrong_key_fails() -> None:
    key = "a" * 64
    mapping = {"<PERSON_1>": "Test"}
    encrypted = encrypt_mapping(mapping, key)
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_mapping(encrypted, "b" * 64)


def test_decrypt_tampered_fails() -> None:
    key = "a" * 64
    encrypted = encrypt_mapping({"<X>": "y"}, key)
    tampered = bytearray(encrypted)
    if len(tampered) > 20:
        tampered[-1] ^= 1
    with pytest.raises(ValueError):
        decrypt_mapping(bytes(tampered), key)
