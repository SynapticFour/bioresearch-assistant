"""Assemble FHIR R4 Bundle (collection)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings


def build_collection_bundle(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a transaction-style collection Bundle with fullUrl + resource."""
    bundle_id = str(uuid.uuid4())
    bundle: dict[str, Any] = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "collection",
        "timestamp": datetime.now(UTC).isoformat(),
        "entry": [],
    }
    settings = get_settings()
    bundle["meta"] = {
        "tag": [
            {
                "system": "https://www.medizininformatik-initiative.de/fhir/sid/release",
                "code": settings.mii_kds_release,
                "display": f"MII KDS {settings.mii_kds_release}",
            }
        ]
    }
    for res in entries:
        rid = res.get("id")
        full_url = f"urn:uuid:{rid}" if rid else f"urn:uuid:{uuid.uuid4()}"
        bundle["entry"].append({"fullUrl": full_url, "resource": res})
    return bundle


def fhir_reference(resource_type: str, id_part: str) -> dict[str, str]:
    return {"reference": f"{resource_type}/{id_part}"}
