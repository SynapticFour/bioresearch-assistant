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
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")

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
    )
    llm_claude_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model ID (e.g. claude-sonnet-4-6)",
    )
    ollama_model: str = Field(
        default="mistral:7b",
        description="Ollama model name for fallback",
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

    # GA4GH WES (Phase 3)
    wes_work_dir: str = Field(
        default="/tmp/wes",
        description="Base directory for WES workflow run working files (e.g. /tmp/wes/{run_id}/)",
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

    @field_validator("pseudonymization_encryption_key")
    @classmethod
    def validate_encryption_key_hex(cls, v: str) -> str:
        """Ensure key is 64 hex characters for AES-256."""
        if len(v) != 64 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError(
                "PSEUDONYMIZATION_ENCRYPTION_KEY must be 64 hex chars (openssl rand -hex 32)"
            )
        return v.lower()

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
