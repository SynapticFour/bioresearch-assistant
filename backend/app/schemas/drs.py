"""GA4GH Data Repository Service (DRS) v1.3 Pydantic schemas.

Reference: https://ga4gh.github.io/data-repository-service-schemas/
"""

from typing import Any

from pydantic import BaseModel, Field

# ----- Service Info (extends GA4GH Service with DRS) -----


class ServiceType(BaseModel):
    """GA4GH service type (group, artifact, version)."""

    group: str = Field(default="org.ga4gh", description="Namespace, e.g. org.ga4gh")
    artifact: str = Field(..., description="API name, e.g. drs")
    version: str = Field(..., description="Schema version, e.g. 1.3")


class ServiceOrganization(BaseModel):
    """Organization providing the service."""

    name: str
    url: str = Field(..., description="URL of the organization (RFC 3986)")


class DrsServiceStats(BaseModel):
    """DRS-specific stats in service-info."""

    maxBulkRequestLength: int = Field(
        default=1, ge=1, description="Max length for bulk request arrays"
    )
    objectCount: int | None = Field(default=None, description="Total number of objects")
    totalObjectSize: int | None = Field(default=None, description="Total size in bytes")


class DrsServiceInfo(BaseModel):
    """DRS service-info response (GET /service-info).

    Extends GA4GH Service Info; type.artifact MUST be 'drs'.
    """

    id: str = Field(..., description="Unique service ID, e.g. org.ga4gh.bioresearch.drs")
    name: str = Field(..., description="Human-readable name")
    type: ServiceType = Field(..., description="type.artifact must be 'drs'")
    organization: ServiceOrganization
    version: str = Field(..., description="Service implementation version")
    description: str | None = None
    contactUrl: str | None = None
    documentationUrl: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    environment: str | None = None
    # DRS extension
    drs: DrsServiceStats | dict[str, Any] = Field(
        default_factory=lambda: DrsServiceStats(),
        description="DRS-specific: maxBulkRequestLength, objectCount, totalObjectSize",
    )


# ----- List (extension) -----


class DrsObjectSummary(BaseModel):
    """Minimal object info for list (GET /objects)."""

    id: str = Field(..., description="Object id (path)")
    name: str | None = Field(default=None, description="File name")
    size: int = Field(..., ge=0, description="Size in bytes")
    created_time: str | None = Field(default=None, description="RFC3339")
    mime_type: str | None = Field(default=None, description="MIME type")


class DrsObjectListResponse(BaseModel):
    """Response for GET /objects (list all)."""

    objects: list[DrsObjectSummary] = Field(
        default_factory=list,
        description="List of DRS object summaries",
    )


# ----- DrsObject -----


class Checksum(BaseModel):
    """Checksum of the object (required in DrsObject)."""

    checksum: str = Field(..., description="Hex-encoded checksum")
    type: str = Field(..., description="Digest method, e.g. md5, sha-256")


class AccessURL(BaseModel):
    """URL that can be used to fetch object bytes (response of GET .../access/{access_id})."""

    url: str = Field(..., description="Fully resolvable URL to fetch bytes")
    headers: list[str] | None = Field(
        default=None, description="Optional HTTP headers for the request"
    )


class AccessMethod(BaseModel):
    """Access method for a DrsObject (at least one of access_url or access_id)."""

    type: str = Field(
        ...,
        description="One of: s3, gs, ftp, gsiftp, globus, htsget, https, file",
    )
    access_url: AccessURL | None = Field(default=None, description="Direct URL to fetch bytes")
    access_id: str | None = Field(
        default=None, description="ID to pass to GET .../access/{access_id}"
    )


class ContentsObject(BaseModel):
    """Child object in a bundle (optional for flat blobs)."""

    name: str = Field(..., description="Name when materialising the object")
    id: str | None = Field(default=None, description="DRS id of the object")
    drs_uri: list[str] | None = Field(default=None, description="Full DRS URIs for the object")
    contents: list["ContentsObject"] | None = Field(
        default=None, description="Nested bundle contents"
    )


ContentsObject.model_rebuild()


class DrsObject(BaseModel):
    """DRS object metadata (GET /objects/{object_id})."""

    id: str = Field(..., description="Identifier unique to this object")
    self_uri: str = Field(..., description="drs:// hostname-based URI for this object")
    size: int = Field(..., ge=0, description="Size in bytes (blob or cumulative for bundle)")
    created_time: str = Field(..., description="RFC3339 creation timestamp")
    checksums: list[Checksum] = Field(..., min_length=1, description="At least one checksum")
    name: str | None = None
    updated_time: str | None = None
    version: str | None = None
    mime_type: str | None = None
    access_methods: list[AccessMethod] | None = Field(
        default=None, description="Required for blobs"
    )
    contents: list[ContentsObject] | None = Field(default=None, description="If bundle")
    description: str | None = None
    aliases: list[str] | None = None
