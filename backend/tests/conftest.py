"""
Zentrale Test-Konfiguration.
Alle Tests laufen in vollständiger Isolation —
keine echte Datenbank (SQLite In-Memory), keine echten HTTP-Calls,
kein echtes Dateisystem nötig (außer ggf. spaCy für Pseudonymisierungs-Tests).
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Set env before any app import (so get_settings() and Paper model use test config)
os.environ["TESTING"] = "1"
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault(
    "PSEUDONYMIZATION_ENCRYPTION_KEY",
    "a" * 64,
)
os.environ.setdefault("ISOLATION_MODE", "open")
os.environ.setdefault("DEPLOYMENT", "test")

from app.core.auth import get_current_user
from app.core.database import Base, get_db, get_engine
from app.main import app


# ── Event loop (session-scoped for async fixtures) ─────────────────────────
@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Single event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ── In-Memory SQLite Engine ───────────────────────────────────────────────
@pytest.fixture(scope="session")
def engine():
    """
    SQLite In-Memory Engine für Tests (app.core.database.get_engine).
    Kein PostgreSQL nötig — läuft überall.
    """
    return get_engine("sqlite+aiosqlite:///:memory:")


@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    """Erstelle alle Tabellen in der In-Memory DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    """
    Isolierte DB-Session pro Test.
    Nutzt Savepoints statt Rollback auf bereits geschlossener Transaktion.
    """
    async with engine.connect() as conn:
        await conn.begin()
        async_session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with async_session_factory() as session:
            yield session
        await conn.rollback()


# ── Dev User Mock ─────────────────────────────────────────────────────────
# Matches app dev-user shape so tests expecting dev mode pass
DEV_USER = {
    "sub": "dev-user",
    "email": "contact@synapticfour.com",
    "name": "Developer",
    "roles": ["admin"],
    "passports": [],
    "visas": [],
}


@pytest.fixture
def mock_current_user():
    """Mock für get_current_user — kein OIDC nötig."""
    return DEV_USER


# ── HTTP Test Client ───────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
    mock_current_user,
    mock_embedding,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP Test Client mit:
    - In-Memory SQLite statt PostgreSQL
    - Mock User statt echtem OIDC Login
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_current_user() -> dict:
        return mock_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthed_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP Client OHNE Auth-Override.
    Für Tests die echte Auth-Logik (z. B. 401) prüfen.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Kein get_current_user Override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ── PubMed Mock ─────────────────────────────────────────────────────────────
@pytest.fixture
def mock_pubmed():
    """
    Mock für PubMed API Calls.
    Kein echtes Internet nötig.
    """
    mock_papers = [
        {
            "pmid": "12345678",
            "title": "BRCA1 Mutations in Breast Cancer",
            "abstract": "This study examines BRCA1...",
            "authors": ["Smith J", "Mueller A"],
            "year": "2024",
            "journal": "Nature Genetics",
            "doi": "10.1038/test",
        }
    ]
    with patch(
        "app.services.pubmed_service.PubMedService.search_pubmed",
        new_callable=AsyncMock,
        return_value=mock_papers,
    ):
        yield mock_papers


# ── LLM Mock ───────────────────────────────────────────────────────────────
@pytest.fixture
def mock_llm():
    """
    Mock für LLM Service (Anthropic/Ollama).
    Kein API Key nötig.
    """
    with patch(
        "app.services.llm_service.LLMService.summarize_paper",
        new_callable=AsyncMock,
        return_value=MagicMock(
            summary="Test Zusammenfassung",
            key_findings=["Finding 1", "Finding 2"],
            methods=[],
            relevance_score=None,
        ),
    ):
        yield


# ── Embedding Mock ─────────────────────────────────────────────────────────
@pytest.fixture
def mock_embedding():
    """
    Mock für Embedding Service.
    Kein ML-Model nötig.
    """
    with patch(
        "app.services.embedding_service.EmbeddingService.embed_text_async",
        new_callable=AsyncMock,
        return_value=[0.1] * 384,
    ):
        yield


# ── BLAST Mock ─────────────────────────────────────────────────────────────
@pytest.fixture
def mock_blast():
    """
    Mock für BLAST Service.
    Kein BLAST-Binary nötig.
    """
    with patch(
        "app.services.blast_service.run_blast_search",
        new_callable=AsyncMock,
        return_value="blast-test-run-001",
    ):
        yield


# ── Nextflow / WES Mock ────────────────────────────────────────────────────
@pytest.fixture
def mock_nextflow():
    """
    Mock für Nextflow/WES Service.
    Kein Nextflow-Binary nötig.
    """
    with patch(
        "app.services.wes_service._execute_nextflow",
        new_callable=AsyncMock,
        return_value=None,
    ):
        yield


# ── Encryption / Env Mock ───────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_encryption_key(monkeypatch):
    """
    Setze Test-Encryption-Key.
    Kein echter Key in Umgebung nötig.
    """
    monkeypatch.setenv(
        "PSEUDONYMIZATION_ENCRYPTION_KEY",
        "a" * 64,
    )
    monkeypatch.setenv("ISOLATION_MODE", "open")
    monkeypatch.setenv("DEPLOYMENT", "test")


# ── spaCy (optional, für Pseudonymisierungs-Service-Tests) ──────────────────
@pytest.fixture(autouse=True, scope="session")
def load_spacy_models() -> None:
    """Lade spaCy-Modelle für Presidio (Pseudonymisierung). Optional, Skip wenn nicht vorhanden."""
    # In the sandboxed execution environment, loading the spaCy model can
    # crash the interpreter (native dependency incompatibility).
    # Our `TESTING=1` mode uses a regex-based pseudonymization fallback, so
    # spaCy models are not required for unit tests.
    if os.environ.get("ENABLE_SPACY_MODELS", "0") != "1":
        return
    try:
        import spacy

        spacy.load("de_core_news_sm")
    except (OSError, ImportError):
        pass  # In CI/ohne Modelle laufen nur API-Tests mit Mocks


# ── Test-Daten Fixtures ────────────────────────────────────────────────────
@pytest.fixture
def test_patient_text() -> str:
    """Sample patient text for pseudonymization tests."""
    return "Patient Max Mustermann, geboren 01.01.1980, Patienten-ID: P-12345"


@pytest.fixture
def test_plain_text() -> str:
    """Plain text without PII."""
    return "Keine personenbezogenen Daten hier."


# ── Extended fixtures for coverage tests ────────────────────────────────────
@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService — kein ML Model nötig."""
    with patch("app.services.embedding_service.EmbeddingService") as mock:
        instance = MagicMock()
        instance.embed_text = MagicMock(return_value=[0.1] * 768)
        instance.embed_text_async = AsyncMock(return_value=[0.1] * 768)
        instance.find_similar = AsyncMock(return_value=[])
        instance.store_paper = AsyncMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_llm_service():
    """Mock LLMService — kein Ollama/Anthropic nötig."""
    with patch("app.services.llm_service.LLMService") as mock:
        instance = MagicMock()
        from app.schemas.llm import PaperSummary

        instance.summarize_paper = AsyncMock(
            return_value=PaperSummary(
                summary="Mock summary",
                key_findings=[],
                methods=[],
                relevance_score=None,
            )
        )
        from app.schemas.llm import BiologicalEntities

        instance.extract_entities = AsyncMock(return_value=BiologicalEntities())
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_pubmed_service():
    """Mock PubMedService — kein NCBI API nötig."""
    with patch("app.services.pubmed_service.PubMedService") as mock:
        instance = MagicMock()
        instance.search = AsyncMock(return_value=[])
        instance.fetch_article = AsyncMock(return_value=None)
        instance.search_pubmed = AsyncMock(return_value=[])
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_ollama_available():
    """Mock Ollama als verfügbar mit geladenem Modell."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "mistral:latest"}]}
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value.get = AsyncMock(return_value=mock_resp)
        yield mock_client


@pytest.fixture
def sample_paper():
    """Beispiel Paper für Tests."""
    return {
        "pmid": "12345678",
        "title": "Test Paper über BRCA1",
        "abstract": "Dies ist ein Test Abstract.",
        "authors": ["Mustermann Max"],
        "year": 2024,
        "journal": "Test Journal",
        "doi": "10.1234/test",
    }


@pytest.fixture
def sample_papers(sample_paper):
    """Liste von Beispiel Papers."""
    papers = [dict(sample_paper) for _ in range(5)]
    for i, p in enumerate(papers):
        p["pmid"] = f"1234567{i}"
        p["title"] = f"Test Paper {i}"
    return papers
