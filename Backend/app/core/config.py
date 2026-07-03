"""
Application configuration.

All settings are loaded automatically from the .env file.

Example:
    from app.core.config import settings

    print(settings.DATABASE_URL)
    print(settings.SECRET_KEY)
"""

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

    SECRET_KEY: str

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

    DEBUG: bool = True

    # =====================================================
    # Pydantic Configuration
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()