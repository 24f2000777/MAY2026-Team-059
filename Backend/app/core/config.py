"""
Application configuration.

All settings are loaded automatically from the .env file.

Example:
    from app.core.config import settings

    print(settings.DATABASE_URL)
    print(settings.SECRET_KEY)
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings

    Values are automatically loaded from the .env file
    and can be accessed anywhere using:

        from app.core.config import settings
    """

    # =====================================================
    # Database
    # =====================================================

    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # =====================================================
    # JWT Authentication
    # =====================================================

    SECRET_KEY: str = Field(min_length=32)

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # =====================================================
    # Email (SMTP)
    # =====================================================

    SMTP_HOST: str

    SMTP_PORT: int

    SMTP_USERNAME: str

    SMTP_PASSWORD: str

    SMTP_FROM_EMAIL: str

    SMTP_FROM_NAME: str = "NAGRIK AI"

    # =====================================================
    # Redis
    # =====================================================

    REDIS_URL: str = "redis://localhost:6379/0"
    
    OTP_EXPIRE_SECONDS: int = 300

    # Reset-password OTPs get a longer window than verify-email
    # OTPs (per the API design doc: 10 minutes vs 5 minutes),
    # since a user recovering a locked-out account may take
    # longer to find the email than someone mid-registration.
    RESET_PASSWORD_OTP_EXPIRE_SECONDS: int = 600

    # Caps how many times forgot-password can be requested for
    # the same email in a rolling window, to stop an email
    # address from being spammed with reset OTPs.
    PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS: int = 3

    PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # Caps how many times a caller can attempt to verify an
    # already-issued OTP (verify-email or reset-password) within
    # its lifetime, so a 6-digit code can't just be brute-forced
    # by guessing repeatedly before it expires.
    OTP_VERIFY_RATE_LIMIT_MAX_ATTEMPTS: int = 5

    OTP_VERIFY_RATE_LIMIT_WINDOW_SECONDS: int = 900
    
    OTP_SECRET_KEY: str = Field(min_length=32)

    # =====================================================
    # Celery
    # =====================================================

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # =====================================================
    # AI
    # =====================================================

    GROQ_API_KEY: str

    # =====================================================
    # Application
    # =====================================================

    ENVIRONMENT: str = "development"

    DEBUG: bool = False
    
    FRONTEND_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # =====================================================
    # Pydantic Configuration
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()