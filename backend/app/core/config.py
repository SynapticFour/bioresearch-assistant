"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All sensitive values and environment-specific config are read from .env
    or environment. See .env.example for required variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="BioResearch Assistant", description="Application name")
    version: str = Field(
        default="1.0.0",
        description="Application version (e.g. for /health and UI)",
        validation_alias="APP_VERSION",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    deployment: str = Field(
        default="",
        description="Deployment target e.g. 'railway' for demo limitations",
    )

    # API
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 URL prefix")

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL with async driver (asyncpg)",
    )

    # CORS (in .env: comma-separated string, e.g. "http://localhost:5173,http://127.0.0.1:5173")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        description="Allowed CORS origins",
    )

    # LLM (optional: Claude primary, Ollama fallback)
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key for Claude (primary LLM)",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama base URL when ANTHROPIC_API_KEY is not set",
        validation_alias="OLLAMA_URL",
    )
    llm_claude_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model ID (e.g. claude-sonnet-4-6)",
    )
    ollama_model: str = Field(
        default="mistral:7b",
        description="Ollama model name for fallback",
    )

    # Locus (curated on-prem RAG; optional module — see docs/LOCUS-MODULE.md)
    locus_enabled: bool = Field(
        default=False,
        description="Expose POST /locus/rag and status when Locus index rows exist",
        validation_alias="LOCUS_ENABLED",
    )

    # Pseudonymization (DSGVO)
    pseudonymization_encryption_key: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="AES-256 key as 64 hex chars; use: openssl rand -hex 32",
    )
    restore_api_key: str | None = Field(
        default=None,
        description="Optional API key for restore (X-Restore-API-Key). If unset, restore disabled.",
    )
    depseudo_access: str = Field(
        default="owner",
        description="Who may de-pseudonymize: owner (only pseudonymizing user), team, admin",
        validation_alias="DEPSEUDO_ACCESS",
    )
    custom_patient_id_patterns: str = Field(
        default="",
        validation_alias="CUSTOM_PATIENT_ID_PATTERNS",
        description=(
            "Comma-separated regex patterns for custom "
            "patient IDs. Example: "
            r"L-\d{4}-\d{5},P-\d{4,8},\d{8}"
        ),
    )

    # GA4GH WES (Phase 3)
    wes_work_dir: str = Field(
        default="/tmp/wes",
        description="Base directory for WES workflow run working files (e.g. /tmp/wes/{run_id}/)",
    )
    wes_subprocess_timeout_seconds: float | None = Field(
        default=None,
        description=(
            "Optional wall-clock limit for Nextflow subprocess communicate(); "
            "None = no limit (long HPC-style runs). Set e.g. 86400 for 24h cap."
        ),
    )

    # BLAST pipeline (Nextflow path; default: pipelines/blast/blast_search.nf from project root)
    blast_workflow_path: str | None = Field(
        default=None,
        description="Path to blast_search.nf; if unset, resolved from backend parent.",
    )

    # GA4GH DRS v1.3 (data repository: object_id -> files under this path)
    drs_storage_path: str = Field(
        default="/tmp/drs",
        description="Root directory for DRS objects (object_id = relative path under this dir)",
    )
    drs_base_url: str = Field(
        default="http://localhost:8000/ga4gh/drs/v1",
        description="Base URL for DRS (self_uri and access_url; no trailing slash)",
    )

    # OAuth2 / OIDC
    oidc_issuer: str = Field(default="", description="OIDC issuer URL (e.g. Keycloak realm)")
    oidc_client_id: str = Field(default="", description="OIDC client ID")
    oidc_client_secret: str = Field(default="", description="OIDC client secret")
    oidc_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/callback",
        description="OIDC redirect URI after login",
    )
    jwt_secret: str = Field(default="", description="JWT secret for session (optional)")
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    microsoft_tenant_id: str = Field(
        default="common",
        description="Microsoft Entra ID / Azure AD tenant ID (e.g. for institution-specific login)",
    )

    # FAIR Export: optional Zenodo upload
    zenodo_token: str | None = Field(
        default=None,
        description="Zenodo API token for FAIR export upload (optional)",
    )

    # Isolation: user = per-user, team = by institution, open = all (dev/demo)
    isolation_mode: str = Field(
        default="user",
        description="Data isolation: user (own only), team (institution), open (all)",
    )

    # MII-KDS / FHIR export (FDPG/DIZ-oriented defaults; override via env)
    mii_kds_release: str = Field(
        default="2026",
        description=(
            "MII Kerndatensatz release label for Bundle.meta and artifacts (align with ig_manifest)"
        ),
        validation_alias="MII_KDS_RELEASE",
    )
    mii_bundle_attach_meta_profile: bool = Field(
        default=False,
        description="If true, add meta.profile canonicals to resources (stricter validation)",
        validation_alias="MII_BUNDLE_ATTACH_META_PROFILE",
    )
    mii_default_consent_policy_id: str = Field(
        default="mii-broad-consent",
        description="Default MII broad consent policy_id for export checks",
        validation_alias="MII_DEFAULT_CONSENT_POLICY_ID",
    )
    # Pinned IG (keep in sync with app/interoperability/mii/ig_manifest.json)
    mii_ig_package_id: str = Field(
        default="de.medizininformatikinitiative.kerndatensatz.meta",
        description="MII Kerndatensatz Meta package id for FHIR validator -ig",
        validation_alias="MII_IG_PACKAGE_ID",
    )
    mii_ig_package_version: str = Field(
        default="2026.0.0",
        description="MII Kerndatensatz Meta package version (pin with manifest)",
        validation_alias="MII_IG_PACKAGE_VERSION",
    )
    mii_export_max_attempts: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Max retries for async MII export jobs (transient failures only)",
        validation_alias="MII_EXPORT_MAX_ATTEMPTS",
    )
    mii_export_retry_base_seconds: float = Field(
        default=2.0,
        ge=0.5,
        le=3600.0,
        description="Base delay for exponential backoff between export job retries",
        validation_alias="MII_EXPORT_RETRY_BASE_SECONDS",
    )

    @property
    def auth_enabled(self) -> bool:
        """True if OIDC is configured (production auth)."""
        return bool(self.oidc_issuer and self.oidc_client_id)

    @property
    def is_user_isolation(self) -> bool:
        """True when each user sees only their own data."""
        return self.isolation_mode == "user"

    @property
    def is_team_isolation(self) -> bool:
        """True when users share data by institution/team."""
        return self.isolation_mode == "team"

    @field_validator("pseudonymization_encryption_key")
    @classmethod
    def validate_encryption_key_hex(cls, v: str) -> str:
        """Ensure key is 64 hex characters for AES-256."""
        if len(v) != 64 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError(
                "PSEUDONYMIZATION_ENCRYPTION_KEY must be 64 hex chars (openssl rand -hex 32)"
            )
        return v.lower()

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret_length(cls, v: str) -> str:
        """When JWT secret is set (non-empty), require at least 32 characters."""
        if v and len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters when set")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings: Loaded and validated settings instance.
    """
    return Settings()
