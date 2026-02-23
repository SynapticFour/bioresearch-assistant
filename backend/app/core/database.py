"""SQLAlchemy async database setup with pgvector support."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Lazy engine — not created at import (avoids PostgreSQL params when using SQLite in tests)
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy models."""

    pass


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Create async SQLAlchemy engine (SQLite or PostgreSQL).

    SQLite uses StaticPool and check_same_thread=False; PostgreSQL uses
    pool_pre_ping, pool_size, max_overflow. Use for production (no args)
    or tests (pass sqlite+aiosqlite:///:memory:).

    Args:
        database_url: Override URL; if None, uses settings.database_url.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance.
    """
    settings = get_settings()
    url = database_url or settings.database_url

    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug,
        )
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_engine_instance() -> AsyncEngine:
    """Return the app's engine (lazy-created, not at import)."""
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the app's session maker (lazy-created, bound to engine)."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine_instance(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session.

    Session is closed and committed/rolled back after request.
    Use as FastAPI Depends(get_db).

    Yields:
        AsyncSession: SQLAlchemy async session.
    """
    async with get_async_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database error: %s: %s", type(e).__name__, e)
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database session (e.g. in scripts or workers).

    Yields:
        AsyncSession: SQLAlchemy async session.
    """
    async with get_async_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database error: %s: %s", type(e).__name__, e)
            raise
        finally:
            await session.close()
