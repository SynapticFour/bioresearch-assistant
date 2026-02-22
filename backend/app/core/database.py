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

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy models."""

    pass


def get_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine for PostgreSQL with pgvector.

    Uses DATABASE_URL from settings. Requires asyncpg driver and
    pgvector extension enabled in the database.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine = get_engine()

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session.

    Session is closed and committed/rolled back after request.
    Use as FastAPI Depends(get_db).

    Yields:
        AsyncSession: SQLAlchemy async session.
    """
    async with async_session_maker() as session:
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
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database error: %s: %s", type(e).__name__, e)
            raise
        finally:
            await session.close()
