"""Tests for GA4GH DRS v1.3 service. No external deps — DB and filesystem only."""

import hashlib

import pytest

from app.services.drs_service import (
    get_access_url,
    get_object,
    get_service_info,
)


@pytest.fixture
def drs_storage(tmp_path, mocker):
    """Point DRS storage to a temporary directory."""
    mock_settings = mocker.patch("app.services.drs_service.get_settings")
    mock_settings.return_value.drs_storage_path = str(tmp_path)
    mock_settings.return_value.drs_base_url = "http://localhost:8000/ga4gh/drs/v1"
    return tmp_path


def test_get_object_creates_drs_object_with_checksums(drs_storage):
    """Placing a file in storage and get_object returns DrsObject with checksums."""
    test_file = drs_storage / "sample.txt"
    test_file.write_text("hello world")
    obj = get_object("sample.txt")
    assert obj is not None
    assert obj.id == "sample.txt"
    assert obj.size == 11
    assert obj.checksums
    assert obj.checksums[0].type == "md5"
    assert len(obj.checksums[0].checksum) == 32


def test_get_object_calculates_md5_and_sha256(drs_storage):
    """get_object returns correct md5 checksum for file content."""
    content = b"drs test content"
    (drs_storage / "checksum_test.bin").write_bytes(content)
    obj = get_object("checksum_test.bin")
    assert obj is not None
    expected_md5 = hashlib.md5(content).hexdigest()
    assert obj.checksums[0].type == "md5"
    assert obj.checksums[0].checksum == expected_md5


def test_get_access_url_returns_valid_url(drs_storage):
    """get_access_url returns a valid URL for an existing object."""
    (drs_storage / "access_test.txt").write_text("data")
    url_result = get_access_url("access_test.txt", "default")
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
    obj = get_object("a/b.txt")
    assert obj is not None
    assert obj.id == "a/b.txt"
