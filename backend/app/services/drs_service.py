"""GA4GH Data Repository Service (DRS) v1.3 backend.

Maps object_id to files under drs_storage_path. object_id is a relative path
(allowed chars [A-Za-z0-9.-_~/]). Access URLs point to the stream endpoint.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.isolation import get_scope_filter, get_scope_values, object_visible_to_scope
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
_ACL_NAME = ".drs-acl.json"
_acl_lock = threading.Lock()


def resolve_object_identifier(raw: str) -> str:
    """Resolve ``drs://authority/object/path`` to ``object/path`` when authority matches this DRS.

    If the URI targets another host or is not a ``drs://`` URI, returns ``raw`` unchanged
    (validation may then reject invalid characters). Aligns with GA4GH clients that pass
    ``self_uri`` / drs URIs as object identifiers.
    """
    s = raw.strip()
    if not s or not s.lower().startswith("drs://"):
        return s
    rest = s[6:]
    sep = rest.find("/")
    if sep < 0:
        return raw
    authority = rest[:sep]
    object_part = rest[sep + 1 :]
    if not object_part.strip():
        return raw
    settings = get_settings()
    base = settings.drs_base_url.rstrip("/")
    configured_host = base.split("//")[-1].split("/")[0].lower()
    if authority.lower() != configured_host:
        return raw
    return object_part


# Safe filename chars for uploads (no path separators or ..)
_SAFE_NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-_")


def _acl_path() -> Path:
    return Path(get_settings().drs_storage_path).resolve() / _ACL_NAME


def _load_acl() -> dict[str, Any]:
    path = _acl_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_acl(acl: dict[str, Any]) -> None:
    path = _acl_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(acl, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _record_acl(
    object_id: str,
    *,
    user_id: str | None,
    team_id: str | None,
    md5: str | None = None,
    size: int | None = None,
) -> None:
    with _acl_lock:
        acl = _load_acl()
        entry = dict(acl.get(object_id) or {})
        if user_id is not None:
            entry["user_id"] = user_id
        if team_id is not None:
            entry["team_id"] = team_id
        if md5 is not None:
            entry["md5"] = md5
        if size is not None:
            entry["size"] = size
        acl[object_id] = entry
        _save_acl(acl)


def _acl_entry(object_id: str) -> dict[str, Any]:
    with _acl_lock:
        raw = _load_acl().get(object_id) or {}
    return raw if isinstance(raw, dict) else {}


def object_allowed_for_user(object_id: str, current_user: dict[str, Any] | None) -> bool:
    """True if isolation scope may see this object. Legacy (no ACL) hidden unless open."""
    if current_user is None:
        return True
    scope = get_scope_filter(current_user)
    if not scope:
        return True
    entry = _acl_entry(object_id)
    if not entry:
        return False
    return object_visible_to_scope(entry.get("user_id"), entry.get("team_id"), scope)


def _safe_object_id(object_id: str) -> Path | None:
    """Resolve object_id to a Path under drs_storage_path; None if invalid."""
    if not object_id or not object_id.strip():
        return None
    raw = resolve_object_identifier(object_id.strip())
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
    h = hashlib.md5(usedforsecurity=False) if algorithm == "md5" else hashlib.sha256()
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


def list_objects(
    current_user: dict[str, Any] | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[dict]:
    """List DRS objects visible to the caller (files under drs_storage_path)."""
    root = Path(get_settings().drs_storage_path).resolve()
    if not root.is_dir():
        return []
    result: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == _ACL_NAME or path.name.endswith(".tmp"):
            continue
        try:
            rel = path.relative_to(root)
            object_id = str(rel).replace("\\", "/")
            if ".." in object_id or not object_id:
                continue
            if not object_allowed_for_user(object_id, current_user):
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
    start = max(0, skip)
    if limit is None:
        return result[start:]
    return result[start : start + max(0, limit)]


def get_object(object_id: str, current_user: dict[str, Any] | None = None) -> DrsObject | None:
    """Resolve object_id to file metadata; None if missing or not visible."""
    path = _safe_object_id(object_id)
    if path is None or not path.is_file():
        return None
    root = Path(get_settings().drs_storage_path).resolve()
    canonical_probe = str(path.relative_to(root)).replace("\\", "/")
    if not object_allowed_for_user(canonical_probe, current_user):
        return None

    stat = path.stat()
    size = stat.st_size
    created_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = _acl_entry(canonical_probe)
    checksum_hex = entry.get("md5") if entry.get("size") == size else None
    if not checksum_hex:
        checksum_hex = _checksum_file(path, "md5")
        _record_acl(
            canonical_probe,
            user_id=entry.get("user_id"),
            team_id=entry.get("team_id"),
            md5=checksum_hex,
            size=size,
        )
    checksums = [Checksum(checksum=checksum_hex, type="md5")]

    settings = get_settings()
    root = Path(settings.drs_storage_path).resolve()
    canonical_id = str(path.relative_to(root)).replace("\\", "/")
    base = settings.drs_base_url.rstrip("/")
    # drs:// hostname-based URI per spec (e.g. drs://drs.example.org/314159)
    authority = base.split("//")[-1].split("/")[0] if "//" in base else base.split("/")[0]
    self_uri = f"drs://{authority}/{canonical_id}"

    stream_url = f"{base}/objects/{canonical_id}/stream"
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
        id=canonical_id,
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


def register_object(
    name: str,
    content: bytes,
    current_user: dict[str, Any] | None = None,
) -> str:
    """Write content to DRS storage under a safe name; return object_id."""
    safe = "".join(c for c in (name or "").strip() if c in _SAFE_NAME_CHARS)
    if not safe:
        raise ValueError("Invalid or empty file name")
    root = Path(get_settings().drs_storage_path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / safe
    path.write_bytes(content)
    md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
    if current_user:
        scope_vals = get_scope_values(current_user)
    else:
        scope_vals = {"user_id": None, "team_id": None}
    _record_acl(
        safe,
        user_id=scope_vals.get("user_id"),
        team_id=scope_vals.get("team_id"),
        md5=md5,
        size=len(content),
    )
    return safe


def register_object_from_path(
    relative_path: str,
    current_user: dict[str, Any] | None = None,
) -> str:
    """Register an existing file under DRS storage by relative path."""
    path = _safe_object_id(relative_path.strip())
    if path is None or not path.is_file():
        raise ValueError("Path not found or not under DRS storage")
    object_id = str(path.relative_to(Path(get_settings().drs_storage_path).resolve())).replace(
        "\\", "/"
    )
    md5 = _checksum_file(path, "md5")
    if current_user:
        scope_vals = get_scope_values(current_user)
    else:
        scope_vals = {"user_id": None, "team_id": None}
    _record_acl(
        object_id,
        user_id=scope_vals.get("user_id"),
        team_id=scope_vals.get("team_id"),
        md5=md5,
        size=path.stat().st_size,
    )
    return object_id


def get_access_url(
    object_id: str,
    access_id: str,
    current_user: dict[str, Any] | None = None,
) -> AccessURL | None:
    """Return AccessURL for object_id and access_id; None if object or access_id invalid."""
    obj = get_object(object_id, current_user=current_user)
    if obj is None or not obj.access_methods:
        return None
    for am in obj.access_methods:
        if am.access_id == access_id and am.access_url:
            return am.access_url
        if am.access_id == access_id:
            base = get_settings().drs_base_url.rstrip("/")
            return AccessURL(url=f"{base}/objects/{obj.id}/stream")
    return None
