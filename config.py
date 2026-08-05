from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================
    # Application
    # =========================
    APP_NAME: str = "AI Email Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # =========================
    # Google OAuth
    # =========================
    CLIENT_ID: str = Field(...)
    CLIENT_SECRET: str = Field(...)
    REDIRECT_URI: str = Field(...)

    # =========================
    # OAuth Scopes
    # =========================
    GMAIL_SCOPES: list[str] = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    # =========================
    # OpenRouter
    # =========================
    OPENROUTER_API_KEY: str | None = None
    MODEL_NAME: str = "openai/gpt-oss-120b"
    GROQ_API_KEY: str 
    GEMINI_API_KEY: str | None = None

    # =========================
    # OAuth Endpoints
    # =========================
    GOOGLE_AUTH_URL: str = (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )

    GOOGLE_TOKEN_URL: str = (
        "https://oauth2.googleapis.com/token"
    )

    GOOGLE_USERINFO_URL: str = (
        "https://www.googleapis.com/oauth2/v3/userinfo"
    )

    # =========================
    # LangSmith
    # =========================
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "AI Email Assistant"
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    # =========================
    # PostgreSQL Database
    # =========================
    DATABASE_URL: str

    
@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    This ensures environment variables are loaded only once.
    """
    return Settings()