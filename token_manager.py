from __future__ import annotations

from datetime import datetime, timezone, timedelta

from database import get_connection

TOKEN_ROW_ID = 1


class TokenManager:

    def __init__(self) -> None:
        self._cached_token_data: dict | None = None

    async def set_tokens(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_in: int,
    ) -> None:
        """Store OAuth tokens in PostgreSQL."""

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        async with get_connection() as connection:
            await connection.execute(
                """
                INSERT INTO gmail_tokens (
                    id,
                    access_token,
                    refresh_token,
                    expires_in,
                    expires_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_in = EXCLUDED.expires_in,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
                """,
                TOKEN_ROW_ID,
                access_token,
                refresh_token,
                expires_in,
                expires_at,
            )

        self._cached_token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "expires_at": expires_at,
        }

    async def get_token_data(self) -> dict | None:
        """Retrieve the stored token row from PostgreSQL."""

        if self._cached_token_data is not None:
            if self._cached_token_data["expires_at"] > datetime.now(timezone.utc):
                return self._cached_token_data

        async with get_connection() as connection:
            record = await connection.fetchrow(
                "SELECT access_token, refresh_token, expires_in, expires_at FROM gmail_tokens WHERE id = $1",
                TOKEN_ROW_ID,
            )

        if record is None:
            return None

        self._cached_token_data = dict(record)
        return self._cached_token_data

    async def get_access_token(self) -> str | None:
        """Read the current access token from PostgreSQL."""

        token_data = await self.get_token_data()
        if token_data is None:
            return None

        return token_data["access_token"]

    async def clear(self) -> None:
        """Remove stored OAuth credentials."""

        async with get_connection() as connection:
            await connection.execute(
                "DELETE FROM gmail_tokens WHERE id = $1",
                TOKEN_ROW_ID,
            )

        self._cached_token_data = None


token_manager = TokenManager()