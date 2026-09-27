"""Optional variant-interpretation module: inactive unless Locus and Ferrum are set."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.variant_interpretation import DISCLAIMER, is_active, summarize  # noqa: E402


def test_inactive_when_nothing_is_configured():
    summary = summarize(
        {
            "answer": "treat this variant",
            "sources": [{"title": "x", "source_ref": "y", "corpus_id": "z"}],
        },
        {"drs_id": "obj", "patient_id": "secret"},
        locus_enabled=False,
        ferrum_drs_url=None,
        ferrum_wes_url=None,
    )
    assert summary.active is False
    assert summary.literature == ()
    assert summary.technical_metadata == {}
    assert summary.disclaimer == DISCLAIMER


@pytest.mark.parametrize(
    ("locus", "drs", "wes"),
    [
        (True, None, None),
        (True, "http://ferrum/ga4gh/drs/v1", None),
        (True, None, "http://ferrum/ga4gh/wes/v1"),
        (True, "  ", "http://ferrum/ga4gh/wes/v1"),
        (False, "http://ferrum/ga4gh/drs/v1", "http://ferrum/ga4gh/wes/v1"),
    ],
)
def test_inactive_unless_locus_and_both_ferrum_urls(locus, drs, wes):
    assert is_active(locus_enabled=locus, ferrum_drs_url=drs, ferrum_wes_url=wes) is False
    summary = summarize(None, None, locus_enabled=locus, ferrum_drs_url=drs, ferrum_wes_url=wes)
    assert summary.active is False


def test_active_summary_is_literature_beside_technical_metadata():
    summary = summarize(
        {
            "answer": "Pathogenic. Recommend treatment.",
            "sources": [
                {
                    "chunk_id": 1,
                    "corpus_id": "guidelines",
                    "source_ref": "pmid:1",
                    "title": "A paper",
                    "similarity_score": 90,
                }
            ],
        },
        {
            "drs_id": "drs-1",
            "name": "variants.vcf",
            "size": 12,
            "checksums": [{"type": "sha256", "checksum": "abc", "extra": "drop"}],
            "wes_run_id": "run-1",
            "wes_state": "COMPLETE",
            "patient_id": "must-not-appear",
            "subject_id": "must-not-appear",
            "description": "clinical note",
        },
        locus_enabled=True,
        ferrum_drs_url="http://ferrum/ga4gh/drs/v1",
        ferrum_wes_url="http://ferrum/ga4gh/wes/v1",
    )
    assert summary.active is True
    assert summary.literature == (
        {"source_ref": "pmid:1", "title": "A paper", "corpus_id": "guidelines"},
    )
    assert summary.technical_metadata == {
        "drs_id": "drs-1",
        "name": "variants.vcf",
        "size": 12,
        "checksums": [{"type": "sha256", "checksum": "abc"}],
        "wes_run_id": "run-1",
        "wes_state": "COMPLETE",
    }
    blob = repr(summary)
    assert "Pathogenic" not in blob
    assert "Recommend" not in blob
    assert "must-not-appear" not in blob
    assert "clinical note" not in blob
    assert "recommendation" not in summary.__dict__
    assert "diagnosis" not in summary.__dict__


def test_module_opens_no_network_client():
    source = (_REPO_ROOT / "modules" / "variant_interpretation" / "summary.py").read_text()
    for banned in ("httpx", "requests", "AsyncSession", "ferrum_backend", "urllib"):
        assert banned not in source
