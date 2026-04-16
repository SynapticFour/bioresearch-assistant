"""MII IG manifest + mapping matrix are present and parseable."""

import json
from pathlib import Path

MII_DIR = Path(__file__).resolve().parent.parent / "app" / "interoperability" / "mii"


def test_ig_manifest_loads() -> None:
    from app.interoperability.mii.ig_loader import ig_package_spec, load_ig_manifest

    m = load_ig_manifest()
    assert m["fhir_version"] == "4.0.1"
    assert "implementation_guide" in m
    assert ig_package_spec().count("#") == 1


def test_mapping_matrix_json() -> None:
    p = MII_DIR / "mapping_matrix.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"]
    assert len(data["mappings"]) >= 1
    for row in data["mappings"]:
        assert "module" in row
        assert "fhir_resource" in row
