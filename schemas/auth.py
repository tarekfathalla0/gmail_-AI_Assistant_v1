from pydantic import BaseModel, Field


class ExchangeRequest(BaseModel):
    """
    Request body used to exchange an authorization code
    for Google OAuth tokens.
    """

    code: str = Field(
        ...,
        description="Google authorization code",
        examples=["4/0AQSTgQFxxxxxxxxxxxxxxxx"],
    )


class LoginResponse(BaseModel):
    """
    Response returned by GET /login.
    """

    authorization_url: str


class CallbackResponse(BaseModel):
    """
    Response returned by Google's callback.
    """

    message: str
    authorization_code: str
    next_step: str


class ExchangeResponse(BaseModel):
    """
    Response after exchanging an authorization code.
    """

    message: str
    access_token: str
    expires_in: int
    token_type: str


class UserInfoResponse(BaseModel):
    """
    Google profile information.
    """

    sub: str
    email: str
    email_verified: bool
    name: str
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None