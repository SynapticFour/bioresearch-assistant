"""GA4GH Data Repository Service (DRS) v1.3 API endpoints.

Reference: https://ga4gh.github.io/data-repository-service-schemas/
"""

import logging
import re
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from starlette.responses import StreamingResponse

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.schemas.drs import (
    AccessURL,
    DrsObject,
    DrsObjectListResponse,
    DrsObjectSummary,
    DrsServiceInfo,
)
from app.services.drs_service import (
    _safe_object_id,
    get_access_url,
    get_object,
    get_service_info,
)
from app.services.drs_service import (
    list_objects as service_list_objects,
)
from app.services.drs_service import (
    register_object as service_register_object,
)
from app.services.drs_service import (
    register_object_from_path as service_register_from_path,
)
from app.services.drs_streaming import iter_object_bytes
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["DRS"])


@router.get("/service-info", response_model=DrsServiceInfo, status_code=status.HTTP_200_OK)
async def drs_service_info() -> DrsServiceInfo:
    """Return DRS service metadata (type.artifact=drs, optional object count/size)."""
    return get_service_info(object_count=None, total_size=None)


@router.get(
    "/objects",
    response_model=DrsObjectListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_drs_objects(
    current_user: dict = Depends(get_current_user),
) -> DrsObjectListResponse:
    """List all DRS objects (files under storage)."""
    raw = service_list_objects()
    objects = [DrsObjectSummary(**x) for x in raw]
    return DrsObjectListResponse(objects=objects)


MAX_DRS_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
MAX_EXTRACT_METADATA_SIZE = 50 * 1024 * 1024  # 50 MB
RANGE_HEADER_RE = re.compile(r"bytes=(\d+)-(\d*)", re.IGNORECASE)


def _client_ip_for_audit(request: Request) -> str | None:
    """Best-effort client IP (proxy headers first), for structured DRS access logs."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or None
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip() or None
    if request.client:
        return request.client.host
    return None


def _log_drs_event(
    event: str,
    *,
    object_id: str,
    request: Request,
    detail: str | None = None,
) -> None:
    """Structured INFO log for DRS byte/metadata access (audit-friendly, no file contents)."""
    logger.info(
        "drs.%s object_id=%s client_ip=%s%s",
        event,
        object_id,
        _client_ip_for_audit(request) or "-",
        f" {detail}" if detail else "",
        extra={
            "drs_event": event,
            "object_id": object_id,
            "client_ip": _client_ip_for_audit(request),
            "detail": detail,
        },
    )


@router.post(
    "/objects",
    response_model=DrsObject,
    status_code=status.HTTP_201_CREATED,
    summary="DRS-Objekt registrieren",
    description="Upload (bis 500MB) oder Server-Pfad für große Dateien.",
)
async def register_drs_object(
    name: str = Form(..., min_length=1),
    file: UploadFile | None = File(default=None),
    path: str | None = Form(default=None),
    server_path: str | None = Form(default=None),
    description: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> DrsObject:
    """Register a DRS object: upload (max 500MB) or register existing path.

    Either `file` (direct upload) or `path` (relative under DRS storage) or
    `server_path` (absolute path on server; must be under drs_storage_path).
    """
    settings = get_settings()
    base_root = Path(settings.drs_storage_path).resolve()

    if file is not None and file.filename:
        filename = (name or file.filename or "upload").strip()
        if filename in (".", ".."):
            filename = "upload"
        content = await file.read()
        if len(content) > MAX_DRS_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"Datei zu groß ({len(content) // 1024 // 1024}MB). "
                    "Maximum: 500MB. Für größere Dateien Server-Pfad angeben."
                ),
            )
        try:
            object_id = service_register_object(filename, content)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
    elif server_path and server_path.strip():
        resolved = Path(server_path.strip()).resolve()
        if not resolved.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Datei nicht gefunden: {server_path}",
            )
        try:
            rel = resolved.relative_to(base_root)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pfad nicht erlaubt (muss unter DRS-Speicher liegen)",
            ) from err
        object_id = str(rel).replace("\\", "/")
        if ".." in object_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pfad nicht erlaubt",
            )
        if not resolved.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server-Pfad muss eine Datei sein",
            )
    elif path:
        try:
            object_id = service_register_from_path(path.strip())
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entweder file, path oder server_path angeben",
        )
    obj = get_object(object_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Object registered but metadata could not be read",
        )
    return obj


@router.post(
    "/objects/extract-metadata",
    status_code=status.HTTP_200_OK,
    summary="Datei-Metadaten extrahieren",
    description="Extrahiert Metadaten aus FASTA- oder VCF-Dateiinhalt (Header-Parsing).",
)
async def extract_file_metadata(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Extract metadata from file content (FASTA, VCF). Max 50 MB.

    Registered before ``/objects/{object_id:path}`` so ``extract-metadata`` is not
    interpreted as an object id (GA4GH clients may use path-style object ids).
    """
    content = await file.read()
    if len(content) > MAX_EXTRACT_METADATA_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Datei zu groß (max. 50 MB für Metadaten-Extraktion)",
        )
    try:
        content_str = content.decode("utf-8", errors="ignore")
    except Exception:
        content_str = ""
    service = MetadataService()
    filename = file.filename or ""
    if filename.endswith((".fasta", ".fa", ".fna")):
        metadata = await service.extract_from_fasta(content_str)
    elif filename.endswith(".vcf"):
        metadata = await service.extract_from_vcf_header(content_str)
    else:
        metadata = {
            "name": filename,
            "size": len(content),
            "format": "unknown",
        }
    return metadata


@router.get(
    "/objects/{object_id:path}/access/{access_id}",
    response_model=AccessURL,
    status_code=status.HTTP_200_OK,
)
async def get_drs_access(
    request: Request,
    object_id: str,
    access_id: str,
    current_user: dict = Depends(get_current_user),
) -> AccessURL:
    """Return a URL (and optional headers) that can be used to fetch the object bytes."""
    access = get_access_url(object_id, access_id)
    if access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object or access method was not found.",
        )
    _log_drs_event(
        "get_access",
        object_id=object_id,
        request=request,
        detail=f"access_id={access_id}",
    )
    return access


@router.get(
    "/objects/{object_id:path}/stream",
    status_code=status.HTTP_200_OK,
    response_model=None,
)
async def stream_drs_object(
    request: Request,
    object_id: str,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream object bytes (used by the URL returned in access_methods.access_url).

    Reads in fixed-size chunks with per-read timeouts (backpressure-friendly, Ferrum-style).
    Supports ``Range: bytes=START-END`` for conformance (HTTP 206 + ``Content-Range``).
    """
    path = _safe_object_id(object_id)
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object was not found.",
        )
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    if range_header:
        match = RANGE_HEADER_RE.match(range_header.strip())
        if not match:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Invalid Range header",
            )
        start = int(match.group(1))
        end_part = match.group(2)
        end = int(end_part) if end_part else file_size - 1
        end = min(max(end, 0), file_size - 1)
        if start < 0 or start >= file_size or start > end:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Range not satisfiable",
            )
        content_range = f"bytes {start}-{end}/{file_size}"
        _log_drs_event(
            "stream_range",
            object_id=object_id,
            request=request,
            detail=content_range,
        )

        async def ranged_body() -> AsyncIterator[bytes]:
            async for chunk in iter_object_bytes(path, start=start, end_inclusive=end):
                yield chunk

        return StreamingResponse(
            ranged_body(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type="application/octet-stream",
            headers={
                "Content-Range": content_range,
                "Accept-Ranges": "bytes",
            },
        )

    _log_drs_event("stream_full", object_id=object_id, request=request, detail=f"bytes={file_size}")

    async def full_body() -> AsyncIterator[bytes]:
        async for chunk in iter_object_bytes(path):
            yield chunk

    return StreamingResponse(
        full_body(),
        media_type="application/octet-stream",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'attachment; filename="{path.name}"',
        },
    )


@router.get("/objects/{object_id:path}", response_model=DrsObject, status_code=status.HTTP_200_OK)
async def get_drs_object(
    request: Request,
    object_id: str,
    current_user: dict = Depends(get_current_user),
) -> DrsObject:
    """Get metadata for a DRS object by id.

    Registered after ``/access/`` and ``/stream`` so literal path segments like
    ``stream`` are not absorbed by ``{object_id:path}`` (GA4GH Range downloads).
    """
    obj = get_object(object_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object was not found.",
        )
    _log_drs_event("get_object", object_id=object_id, request=request)
    return obj
