from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncpg

from config import get_settings

settings = get_settings()
_pool: asyncpg.Pool | None = None

CREATE_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS gmail_tokens (
    id BIGINT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_in INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


async def connect() -> None:
    """Initialize the asyncpg pool and ensure required tables exist."""

    global _pool
    if _pool is not None:
        return

    _pool = await asyncpg.create_pool(settings.DATABASE_URL)

    async with _pool.acquire() as connection:
        await connection.execute(CREATE_TOKENS_TABLE)
        await connection.execute(
            "ALTER TABLE gmail_tokens ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
        )


async def close() -> None:
    """Close the asyncpg pool."""

    global _pool
    if _pool is None:
        return

    await _pool.close()
    _pool = None


@asynccontextmanager
async def get_connection() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a connection from the pool for a transactional operation."""

    if _pool is None:
        await connect()

    assert _pool is not None
    async with _pool.acquire() as connection:
        yield connection
