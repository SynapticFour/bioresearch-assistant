"""GA4GH Data Repository Service (DRS) v1.3 backend.

Maps object_id to files under drs_storage_path. object_id is a relative path
(allowed chars [A-Za-z0-9.-_~/]). Access URLs point to the stream endpoint.
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.schemas.drs import (
    AccessMethod,
    AccessURL,
    Checksum,
    DrsObject,
    DrsServiceInfo,
    DrsServiceStats,
    ServiceOrganization,
    ServiceType,
)

logger = logging.getLogger(__name__)

# DRS ID allowed chars per spec [A-Za-z0-9.-_~]; we allow / for path segments
_ALLOWED_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-_~/")

# Safe filename chars for uploads (no path separators or ..)
_SAFE_NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-_")


def _safe_object_id(object_id: str) -> Path | None:
    """Resolve object_id to a Path under drs_storage_path; None if invalid."""
    if not object_id or not object_id.strip():
        return None
    raw = object_id.strip()
    if ".." in raw or any(c not in _ALLOWED_CHARS for c in raw):
        return None
    root = Path(get_settings().drs_storage_path).resolve()
    path = (root / raw).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def _checksum_file(path: Path, algorithm: str = "md5") -> str:
    """Compute hex checksum of file (md5 or sha-256)."""
    h = hashlib.md5() if algorithm == "md5" else hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_service_info(
    object_count: int | None = None,
    total_size: int | None = None,
) -> DrsServiceInfo:
    """Build DRS service-info response."""
    return DrsServiceInfo(
        id="org.ga4gh.bioresearch.drs",
        name="BioResearch Assistant DRS",
        type=ServiceType(group="org.ga4gh", artifact="drs", version="1.3"),
        organization=ServiceOrganization(
            name="Synaptic Four",
            url="https://www.synapticfour.com",
        ),
        version="0.1.0",
        description="GA4GH DRS v1.3 for on-premise data objects (file-backed).",
        drs=DrsServiceStats(
            maxBulkRequestLength=1,
            objectCount=object_count if object_count is not None else None,
            totalObjectSize=total_size if total_size is not None else None,
        ),
    )


def list_objects() -> list[dict]:
    """List all DRS objects (files under drs_storage_path).

    Returns list of DrsObjectSummary-like dicts.
    """
    root = Path(get_settings().drs_storage_path).resolve()
    if not root.is_dir():
        return []
    result: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
            object_id = str(rel).replace("\\", "/")
            if ".." in object_id or not object_id:
                continue
            stat = path.stat()
            created_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            mime_type = None
            if path.suffix in (".xml",):
                mime_type = "application/xml"
            elif path.suffix in (".json",):
                mime_type = "application/json"
            elif path.suffix in (".vcf", ".vcf.gz"):
                mime_type = "text/vcf"
            elif path.suffix in (".fasta", ".fa", ".fna"):
                mime_type = "text/x-fasta"
            elif path.suffix in (".bam", ".sam"):
                mime_type = "application/octet-stream"
            result.append(
                {
                    "id": object_id,
                    "name": path.name,
                    "size": stat.st_size,
                    "created_time": created_time,
                    "mime_type": mime_type,
                }
            )
        except (ValueError, OSError):
            continue
    result.sort(key=lambda x: (x.get("created_time") or "", x["id"]))
    return result


def get_object(object_id: str) -> DrsObject | None:
    """Resolve object_id to a file and return DrsObject metadata; None if not found or invalid."""
    path = _safe_object_id(object_id)
    if path is None or not path.is_file():
        return None

    stat = path.stat()
    size = stat.st_size
    created_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    checksum_hex = _checksum_file(path, "md5")
    checksums = [Checksum(checksum=checksum_hex, type="md5")]

    settings = get_settings()
    base = settings.drs_base_url.rstrip("/")
    # drs:// hostname-based URI per spec (e.g. drs://drs.example.org/314159)
    authority = base.split("//")[-1].split("/")[0] if "//" in base else base.split("/")[0]
    self_uri = f"drs://{authority}/{object_id}"

    stream_url = f"{base}/objects/{object_id}/stream"
    access_methods = [
        AccessMethod(
            type="https",
            access_url=AccessURL(url=stream_url),
            access_id="default",
        ),
    ]

    name = path.name
    mime_type = None
    if name.endswith(".xml"):
        mime_type = "application/xml"
    elif name.endswith(".json"):
        mime_type = "application/json"
    elif name.endswith(".tsv") or name.endswith(".txt"):
        mime_type = "text/plain"

    return DrsObject(
        id=object_id,
        self_uri=self_uri,
        size=size,
        created_time=created_time,
        checksums=checksums,
        name=name,
        updated_time=created_time,
        version=checksum_hex[:12],
        mime_type=mime_type,
        access_methods=access_methods,
    )


def register_object(name: str, content: bytes) -> str:
    """Write content to DRS storage under a safe name; return object_id.

    Args:
        name: Requested file name (e.g. patient001.vcf). Path separators stripped.
        content: File bytes to store.

    Returns:
        object_id (relative path) for the stored file.

    Raises:
        ValueError: If name is invalid or empty after sanitization.
    """
    safe = "".join(c for c in (name or "").strip() if c in _SAFE_NAME_CHARS)
    if not safe:
        raise ValueError("Invalid or empty file name")
    root = Path(get_settings().drs_storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / safe
    path.write_bytes(content)
    return safe


def register_object_from_path(relative_path: str) -> str:
    """Register an existing file under DRS storage by relative path.

    The path must be relative and within drs_storage_path (no ..).
    Returns object_id (relative path).
    """
    path = _safe_object_id(relative_path.strip())
    if path is None or not path.is_file():
        raise ValueError("Path not found or not under DRS storage")
    return str(path.relative_to(Path(get_settings().drs_storage_path).resolve())).replace("\\", "/")


def get_access_url(object_id: str, access_id: str) -> AccessURL | None:
    """Return AccessURL for object_id and access_id; None if object or access_id invalid."""
    obj = get_object(object_id)
    if obj is None or not obj.access_methods:
        return None
    for am in obj.access_methods:
        if am.access_id == access_id and am.access_url:
            return am.access_url
        if am.access_id == access_id:
            base = get_settings().drs_base_url.rstrip("/")
            return AccessURL(url=f"{base}/objects/{object_id}/stream")
    return None
