"""Tests for DRS access_url normalization (Ferrum-style string vs object)."""

from app.services.drs_access_url import access_url_for_json_listing, extract_download_url


def test_extract_download_url_string() -> None:
    assert extract_download_url("https://x/y") == "https://x/y"
    assert extract_download_url("") is None
    assert extract_download_url("  ") is None


def test_extract_download_url_object() -> None:
    assert extract_download_url({"url": "https://a/b"}) == "https://a/b"
    assert extract_download_url({}) is None
    assert extract_download_url({"url": 1}) is None


def test_access_url_for_json_listing() -> None:
    assert access_url_for_json_listing("https://z") == "https://z"
    m = access_url_for_json_listing({"url": "https://z", "headers": []})
    assert isinstance(m, dict)
    assert m.get("url") == "https://z"
