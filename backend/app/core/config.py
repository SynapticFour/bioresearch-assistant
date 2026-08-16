"""Application configuration using pydantic-settings."""

import warnings
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
        default="0.2.0",
        description="Application version (e.g. for /health and UI)",
        validation_alias="APP_VERSION",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    deployment: str = Field(
        default="",
        description="Deployment target e.g. 'railway' for demo limitations",
    )

    # Solum subject bridge (optional; org plan F3)
    solum_base_url: str | None = Field(
        default=None,
        description="Solum sidecar base URL for subject-link upsert",
        validation_alias="SOLUM_BASE_URL",
    )
    solum_sidecar_token: str | None = Field(
        default=None,
        description="Solum sidecar bearer / shared token",
        validation_alias="SOLUM_SIDECAR_TOKEN",
    )
    solum_subject_bridge_upsert: bool = Field(
        default=True,
        description="When Solum URL+token set, POST subject-link on demand",
        validation_alias="SOLUM_SUBJECT_BRIDGE_UPSERT",
    )
    solum_subject_purpose: str = Field(
        default="research",
        description="Default Solum purpose for subject-link upserts",
        validation_alias="SOLUM_SUBJECT_PURPOSE",
    )
    solum_subject_capability: str = Field(
        default="solum:cdr:write",
        description="Default Solum capability (comma-separated) for subject-link writes",
        validation_alias="SOLUM_SUBJECT_CAPABILITY",
    )

    # Ferrum institutional DRS/WES (optional). Empty = BRA's local GA4GH surface.
    ferrum_drs_url: str | None = Field(
        default=None,
        description="Ferrum DRS base including /ga4gh/drs/v1; when set, BRA proxies DRS to Ferrum",
        validation_alias="FERRUM_DRS_URL",
    )
    ferrum_wes_url: str | None = Field(
        default=None,
        description="Ferrum WES base including /ga4gh/wes/v1; when set, BRA proxies WES to Ferrum",
        validation_alias="FERRUM_WES_URL",
    )
    ferrum_bearer_token: str | None = Field(
        default=None,
        description="Optional bearer for Ferrum DRS/WES (Passport or operator token)",
        validation_alias="FERRUM_BEARER_TOKEN",
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

    # LLM: anthropic (cloud) | ollama | openai_compatible (local OpenAI API, e.g. SGLang/vLLM)
    llm_provider: str = Field(
        default="auto",
        description=(
            "LLM routing: auto (Anthropic key → Claude, else Ollama), "
            "anthropic, ollama, openai_compatible (requires OPENAI_*)."
        ),
        validation_alias="LLM_PROVIDER",
    )
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
    openai_api_base: str | None = Field(
        default=None,
        description=(
            "OpenAI-compatible API base URL including /v1, e.g. "
            "http://localhost:30000/v1 or http://inference:30000/v1"
        ),
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(
        default="",
        description="Model id for OpenAI-compatible endpoint (e.g. MiniMaxAI/MiniMax-M2)",
        validation_alias="OPENAI_MODEL",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="Optional bearer token for OpenAI-compatible server (use EMPTY for none)",
        validation_alias="OPENAI_API_KEY",
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
    frontend_base_url: str = Field(
        default="http://localhost:5173",
        description="SPA origin for post-login redirect (OIDC callback)",
        validation_alias="FRONTEND_BASE_URL",
    )
    session_cookie_name: str = Field(
        default="bra_access_token",
        description="httpOnly session cookie name",
        validation_alias="SESSION_COOKIE_NAME",
    )
    jwt_secret: str = Field(default="", description="JWT secret for session (optional)")
    jwt_algorithm: str = Field(default="RS256", description="JWT algorithm")
    microsoft_tenant_id: str = Field(
        default="common",
        description="Microsoft Entra ID / Azure AD tenant ID (e.g. for institution-specific login)",
    )
    oidc_profile: str = Field(
        default="auto",
        description=(
            "IdP claims-map: auto | keycloak | entra | ls-login | broker. "
            "auto picks from OIDC_ISSUER. BRA never issues Passports."
        ),
        validation_alias="OIDC_PROFILE",
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
    wes_allow_remote_workflows: bool = Field(
        default=False,
        description=(
            "Allow Nextflow to fetch http(s) workflow_url values. Off by default; "
            "HelixTest TRS stubs and local *.nf / allowlisted names still work."
        ),
        validation_alias="WES_ALLOW_REMOTE_WORKFLOWS",
    )
    wes_allowed_workflow_hosts: list[str] = Field(
        default_factory=list,
        description="If remote workflows are enabled, restrict to these hostnames.",
        validation_alias="WES_ALLOWED_WORKFLOW_HOSTS",
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

    def resolved_llm_backend(self) -> str:
        """Which LLM backend is active: anthropic | openai_compatible | ollama."""
        p = (self.llm_provider or "auto").strip().lower()
        if p == "openai_compatible":
            return "openai_compatible"
        if p == "anthropic":
            return "anthropic"
        if p == "ollama":
            return "ollama"
        # auto: same gate as /health LLM probe — invalid keys fall back to Ollama
        k = (self.anthropic_api_key or "").strip()
        if k and k != "dummy" and k.startswith("sk-ant-") and len(k) > 20:
            return "anthropic"
        return "ollama"

    def effective_llm_model_label(self) -> str:
        """Human-readable model id for logs / API responses."""
        b = self.resolved_llm_backend()
        if b == "anthropic":
            return self.llm_claude_model
        if b == "openai_compatible":
            return self.openai_model or "openai-compatible"
        return self.ollama_model

    @property
    def auth_enabled(self) -> bool:
        """True if OIDC is configured (production auth)."""
        return bool(self.oidc_issuer and self.oidc_client_id)

    @property
    def allows_unauthenticated_dev(self) -> bool:
        """True only for explicit local/test deploys — not the empty default."""
        dep = (self.deployment or "").strip().lower()
        return dep in ("local", "development", "test")

    @property
    def is_production_runtime(self) -> bool:
        """True when ENVIRONMENT or DEPLOYMENT indicates a production target."""
        env = (self.environment or "").strip().lower()
        dep = (self.deployment or "").strip().lower()
        return env == "production" or dep in {
            "production",
            "prod",
            "azure",
            "otc",
            "dfn",
            "k8s",
        }

    def assert_runtime_hardened(self) -> None:
        """Refuse production start with lab/demo defaults (Uniklinik bar)."""
        if not self.is_production_runtime:
            return
        if self.allows_unauthenticated_dev:
            raise RuntimeError(
                "DEPLOYMENT=local|development|test is forbidden when ENVIRONMENT=production"
            )
        if (self.isolation_mode or "").strip().lower() == "open":
            raise RuntimeError("ISOLATION_MODE=open is forbidden in production")
        if "*" in self.cors_origins:
            raise RuntimeError("CORS_ORIGINS=* is forbidden in production")
        if not self.auth_enabled:
            raise RuntimeError("OIDC_ISSUER and OIDC_CLIENT_ID are required in production")
        url = (self.database_url or "").lower()
        if ":bioresearch@" in url or url.endswith(":bioresearch/") or "/bioresearch:" in url:
            raise RuntimeError(
                "Default database password 'bioresearch' is forbidden in production. "
                "Set DB_PASSWORD to a unique secret."
            )

    @property
    def is_user_isolation(self) -> bool:
        """True when each user sees only their own data."""
        return (self.isolation_mode or "").strip().lower() == "user"

    @property
    def is_team_isolation(self) -> bool:
        """True when users share data by institution/team."""
        return (self.isolation_mode or "").strip().lower() == "team"

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

    @field_validator("isolation_mode")
    @classmethod
    def validate_isolation_mode(cls, v: str) -> str:
        """Only user | team | open are valid; unknown values fail closed to user."""
        mode = (v or "user").strip().lower()
        if mode not in ("user", "team", "open"):
            warnings.warn(
                f"Unknown ISOLATION_MODE={v!r}; failing closed to 'user'",
                stacklevel=2,
            )
            return "user"
        return mode

    @field_validator("wes_allowed_workflow_hosts", mode="before")
    @classmethod
    def parse_workflow_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [h.strip().lower() for h in v.split(",") if h.strip()]
        return [str(h).strip().lower() for h in v if str(h).strip()]

    @field_validator("ferrum_drs_url", "ferrum_wes_url", "ferrum_bearer_token", mode="before")
    @classmethod
    def empty_optional_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = str(v).strip()
        return stripped or None

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
