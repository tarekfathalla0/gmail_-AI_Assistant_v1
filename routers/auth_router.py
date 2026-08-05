from fastapi import APIRouter

from auth import oauth
from schemas.auth import (
    CallbackResponse,
    ExchangeRequest,
    ExchangeResponse,
    LoginResponse,
    UserInfoResponse,
)

router = APIRouter(
    prefix="",
    tags=["Authentication"],
)


@router.get(
    "/login",
    response_model=LoginResponse,
)
async def login():
    """
    Generate Google OAuth URL.
    """

    return LoginResponse(
        authorization_url=oauth.build_authorization_url()
    )


@router.get(
    "/callback",
    response_model=CallbackResponse,
)
async def callback(code: str):
    """
    Google redirects here after authentication.
    """

    return CallbackResponse(
        message="Authorization code received successfully.",
        authorization_code=code,
        next_step="POST /exchange",
    )


@router.post(
    "/exchange",
    response_model=ExchangeResponse,
)
async def exchange(
    request: ExchangeRequest,
):
    """
    Exchange authorization code for OAuth tokens.
    """

    return await oauth.exchange_code(
        request.code
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
)
async def me():
    """
    Return authenticated Google user.
    """

    return await oauth.get_user_info()