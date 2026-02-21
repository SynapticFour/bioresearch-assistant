"""GA4GH Data Repository Service (DRS) v1.3 API endpoints.

Reference: https://ga4gh.github.io/data-repository-service-schemas/
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

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
async def list_drs_objects() -> DrsObjectListResponse:
    """List all DRS objects (files under storage)."""
    raw = service_list_objects()
    objects = [DrsObjectSummary(**x) for x in raw]
    return DrsObjectListResponse(objects=objects)


@router.get("/objects/{object_id}", response_model=DrsObject, status_code=status.HTTP_200_OK)
async def get_drs_object(object_id: str) -> DrsObject:
    """Get metadata for a DRS object by id. object_id is a relative path under DRS storage."""
    obj = get_object(object_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object was not found.",
        )
    return obj


@router.get(
    "/objects/{object_id}/access/{access_id}",
    response_model=AccessURL,
    status_code=status.HTTP_200_OK,
)
async def get_drs_access(object_id: str, access_id: str) -> AccessURL:
    """Return a URL (and optional headers) that can be used to fetch the object bytes."""
    access = get_access_url(object_id, access_id)
    if access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object or access method was not found.",
        )
    return access


@router.get("/objects/{object_id}/stream", status_code=status.HTTP_200_OK)
async def stream_drs_object(object_id: str) -> FileResponse:
    """Stream object bytes (used by the URL returned in access_methods.access_url)."""
    path = _safe_object_id(object_id)
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested DRS object was not found.",
        )
    return FileResponse(path, filename=path.name, media_type="application/octet-stream")
