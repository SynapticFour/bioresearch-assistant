"""Load pinned MII IG and mapping matrix data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_MANIFEST_PATH = Path(__file__).resolve().parent / "ig_manifest.json"
_MAPPING_MATRIX_PATH = Path(__file__).resolve().parent / "mapping_matrix.json"


@lru_cache
def load_ig_manifest() -> dict:
    """Return ig_manifest.json contents (cached)."""
    with _MANIFEST_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def ig_package_spec() -> str:
    """FHIR CLI `-ig` argument: `{package_id}#{version}`."""
    m = load_ig_manifest()
    ig = m["implementation_guide"]
    return f"{ig['package_id']}#{ig['package_version']}"


@lru_cache
def load_mapping_matrix() -> dict:
    """Return mapping_matrix.json contents (cached)."""
    with _MAPPING_MATRIX_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def profile_by_module(module: str) -> str | None:
    """Lookup target profile canonical for module key."""
    matrix = load_mapping_matrix()
    for row in matrix.get("mappings", []):
        if row.get("module") == module:
            return row.get("target_profile_canonical")
    return None
