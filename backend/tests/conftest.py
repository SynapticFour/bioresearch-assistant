"""Pytest configuration and shared fixtures.

Single session-scoped event loop so asyncpg and SQLAlchemy share one stable loop.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set env before importing app (so get_settings() gets test config)
os.environ.setdefault("PSEUDONYMIZATION_ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Einen einzigen Event Loop für die gesamte Test-Session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
def load_spacy_models() -> None:
    """Ensure German spaCy model is loaded before tests (for Presidio)."""
    import spacy

    try:
        spacy.load("de_core_news_sm")
    except OSError:
        spacy.cli.download("de_core_news_sm")


@pytest.fixture(scope="session")
async def test_engine(
    event_loop: asyncio.AbstractEventLoop,
) -> AsyncGenerator[AsyncEngine, None]:
    """Session-scoped Engine — gleicher Loop wie event_loop."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        pool_reset_on_return=None,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Session Factory — session-scoped damit kein Loop-Wechsel."""
    return async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Jeder Test bekommt eine frische Session mit Rollback."""
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient mit DB Override für jeden Test."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ─── Test-Daten Fixtures ─────────────────────────────────────────


@pytest.fixture
def test_patient_text() -> str:
    """Sample patient text for pseudonymization tests."""
    return "Patient Max Mustermann, geboren 01.01.1980, Patienten-ID: P-12345"


@pytest.fixture
def test_plain_text() -> str:
    """Plain text without PII."""
    return "Keine personenbezogenen Daten hier."
