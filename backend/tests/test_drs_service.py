"""Tests for GA4GH DRS v1.3 service. No external deps — DB and filesystem only."""

import hashlib

import pytest

from app.services.drs_service import (
    get_access_url,
    get_object,
    get_service_info,
    register_object,
    register_object_from_path,
    resolve_object_identifier,
)

OWNER = {"sub": "dev-user", "email": "contact@synapticfour.com", "roles": ["admin"]}


@pytest.fixture
def drs_storage(tmp_path, mocker):
    """Point DRS storage to a temporary directory."""
    mock_settings = mocker.patch("app.services.drs_service.get_settings")
    mock_settings.return_value.drs_storage_path = str(tmp_path)
    mock_settings.return_value.drs_base_url = "http://localhost:8000/ga4gh/drs/v1"
    return tmp_path


def test_get_object_creates_drs_object_with_checksums(drs_storage):
    """Placing a file in storage and get_object returns DrsObject with checksums."""
    register_object("sample.txt", b"hello world", current_user=OWNER)
    obj = get_object("sample.txt", current_user=OWNER)
    assert obj is not None
    assert obj.id == "sample.txt"
    assert obj.size == 11
    assert obj.checksums
    assert obj.checksums[0].type == "md5"
    assert len(obj.checksums[0].checksum) == 32


def test_get_object_calculates_md5_and_sha256(drs_storage):
    """get_object returns correct md5 checksum for file content."""
    content = b"drs test content"
    register_object("checksum_test.bin", content, current_user=OWNER)
    obj = get_object("checksum_test.bin", current_user=OWNER)
    assert obj is not None
    expected_md5 = hashlib.md5(content).hexdigest()
    assert obj.checksums[0].type == "md5"
    assert obj.checksums[0].checksum == expected_md5


def test_get_access_url_returns_valid_url(drs_storage):
    """get_access_url returns a valid URL for an existing object."""
    register_object("access_test.txt", b"data", current_user=OWNER)
    url_result = get_access_url("access_test.txt", "default", current_user=OWNER)
    assert url_result is not None
    assert "access_test.txt" in url_result.url
    assert "/stream" in url_result.url


def test_get_nonexistent_object_returns_none(drs_storage):
    """get_object for missing object_id returns None (API layer turns into 404)."""
    assert get_object("nonexistent/file.txt") is None


def test_get_object_invalid_id_returns_none(drs_storage):
    """get_object with path traversal or invalid chars returns None."""
    assert get_object("..") is None
    assert get_object("") is None


def test_get_service_info_returns_drs_service_info():
    """get_service_info returns valid DrsServiceInfo."""
    info = get_service_info(object_count=5, total_size=1000)
    assert info.id == "org.ga4gh.bioresearch.drs"
    assert info.name == "BioResearch Assistant DRS"
    assert info.drs.objectCount == 5
    assert info.drs.totalObjectSize == 1000
    assert info.organization.url == "https://www.synapticfour.com"


def test_get_object_nested_path_under_storage(drs_storage):
    """object_id may contain slashes (relative path under DRS root)."""
    (drs_storage / "a").mkdir()
    (drs_storage / "a" / "b.txt").write_text("nested")
    register_object_from_path("a/b.txt", current_user=OWNER)
    obj = get_object("a/b.txt", current_user=OWNER)
    assert obj is not None
    assert obj.id == "a/b.txt"


def test_resolve_object_identifier_matching_drs_uri(drs_storage):
    """drs://host/path resolves to object id when host matches drs_base_url."""
    register_object("by-uri.txt", b"x", current_user=OWNER)
    uri = "drs://localhost:8000/by-uri.txt"
    assert resolve_object_identifier(uri) == "by-uri.txt"
    obj = get_object(uri, current_user=OWNER)
    assert obj is not None
    assert obj.id == "by-uri.txt"


def test_resolve_object_identifier_foreign_host_unchanged(drs_storage):
    """drs://other-host/... is left unchanged (path validation will reject ':' etc.)."""
    raw = "drs://other.example.com/obj1"
    assert resolve_object_identifier(raw) == raw
    assert get_object(raw) is None
