# Database engine and session setup
import asyncio
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_size=5,
    max_overflow=10,
    # Recycle a pooled connection after 30 minutes rather than reusing
    # it indefinitely, so a connection Supabase's own pooler has quietly
    # dropped gets replaced proactively instead of failing (and forcing
    # a retry, or a confusing hang) the next time something tries to use it.
    pool_recycle=1800,
    # Supabase's transaction pooler (PgBouncer) hands out the same backend
    # connection to different client sessions without resetting it, so
    # asyncpg's default auto-incrementing statement names (__asyncpg_stmt_1__,
    # _2__, ...) can collide with a statement a *different* session already
    # prepared on that same backend connection ("prepared statement already
    # exists" / "DuplicatePreparedStatementError"). statement_cache_size=0
    # disables asyncpg's own client-side cache, but SQLAlchemy's asyncpg
    # dialect still calls .prepare() with its own name generator, so it also
    # needs prepared_statement_cache_size=0 and a globally-unique name
    # function (SQLAlchemy dialect-level options, not raw asyncpg ones).
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — gives a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def warm_pool() -> None:
    """
    Opens pool_size connections concurrently at startup instead of
    leaving them to be established lazily by the first real requests.
    Each fresh connection to a remote Postgres host pays a real network
    handshake cost (TCP + TLS + Postgres auth, several round trips), so
    without this the first few users to hit the API right after a
    deploy/restart are the ones who pay it, one at a time, as their
    request happens to be the one that grows the pool. Called once from
    the app's lifespan startup, see app/main.py.
    """
    async def _open_one():
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

    await asyncio.gather(*(_open_one() for _ in range(engine.pool.size())))
