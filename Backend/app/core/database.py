# Database engine and session setup
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
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
