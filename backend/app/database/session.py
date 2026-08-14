"""Async SQLAlchemy engine/session.

The only thing allowed to import this outside of `app/repositories/` and
Alembic is `app/api/v1/health.py` (it needs the raw engine for a
connectivity check) — API routes and services get their data through a
repository, never through a session directly (Part 3 §21/§23).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped DB session, injected
    into repositories (see app/api/deps.py)."""
    async with async_session_maker() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """DB session for use outside a request, e.g. inside a Celery task."""
    async with async_session_maker() as session:
        yield session
