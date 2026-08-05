from __future__ import annotations

from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx

from config import get_settings
from token_manager import token_manager
from schemas.auth import ExchangeResponse, UserInfoResponse

settings = get_settings()


class GoogleOAuth:
    """
    Handles all Google OAuth operations.
    """

    def __init__(self) -> None:
        self.settings = settings

    def build_authorization_url(self) -> str:
        """
        Generate Google's OAuth authorization URL.
        """

        params = {
            "client_id": self.settings.CLIENT_ID,
            "redirect_uri": self.settings.REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.settings.GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
        print("REDIRECT_URI =", self.settings.REDIRECT_URI)

        return (
            f"{self.settings.GOOGLE_AUTH_URL}?"
            f"{urlencode(params)}"
        )

    async def exchange_code(self, code: str) -> dict:
        """
        Exchange the authorization code for OAuth tokens.
        """

        payload = {
            "code": code,
            "client_id": self.settings.CLIENT_ID,
            "client_secret": self.settings.CLIENT_SECRET,
            "redirect_uri": self.settings.REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.GOOGLE_TOKEN_URL,
                data=payload,
            )

        response.raise_for_status()

        token_data = response.json()

        await token_manager.set_tokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data["expires_in"],
        )

        return ExchangeResponse(
            message="Authentication successful.",
            access_token=token_data["access_token"],
            expires_in=token_data["expires_in"],
            token_type=token_data["token_type"],
        )

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Refresh the OAuth access token using the stored refresh token."""

        payload = {
            "client_id": self.settings.CLIENT_ID,
            "client_secret": self.settings.CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.GOOGLE_TOKEN_URL,
                data=payload,
            )

        response.raise_for_status()

        token_data = response.json()

        await token_manager.set_tokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get(
                "refresh_token",
                refresh_token,
            ),
            expires_in=token_data["expires_in"],
        )

        return token_data["access_token"]

    async def get_valid_access_token(self) -> str:
        """Return a valid access token, refreshing it if necessary."""

        token_data = await token_manager.get_token_data()
        if token_data is None:
            raise RuntimeError(
                "Gmail authentication required."
            )

        expires_at = token_data["expires_at"]
        now = datetime.now(timezone.utc)

        if expires_at <= now + timedelta(seconds=60):
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                raise RuntimeError(
                    "Refresh token not available; re-authentication required."
                )
            return await self.refresh_access_token(
                refresh_token=refresh_token,
            )

        return token_data["access_token"]

    async def get_user_info(self) -> UserInfoResponse:
        """
        Retrieve the authenticated user's profile.
        """

        access_token = await self.get_valid_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.settings.GOOGLE_USERINFO_URL,
                headers=headers,
            )

        response.raise_for_status()

        return UserInfoResponse(**response.json())

    async def revoke(self) -> None:
        """
        Clear locally stored credentials.

        Google token revocation can be added later.
        """

        await token_manager.clear()


oauth = GoogleOAuth()