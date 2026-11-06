from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "EventPulse"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database URLs
    DATABASE_URL: str = "sqlite+aiosqlite:///./eventpulse.db"
    DATABASE_URL_SYNC: str = "sqlite:///./eventpulse.db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Webhook Dispatch Settings
    MAX_RETRIES: int = 5
    DELIVERY_TIMEOUT_SECONDS: float = 3.0
    DEFAULT_HMAC_SECRET: str = "eventpulse_super_secret_signing_key_change_me"

    # Full Jitter & Backoff Cap
    RETRY_CAP_SECONDS: float = 300.0  # 5 minutes maximum retry interval

    # Circuit Breaker Settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 100
    CIRCUIT_BREAKER_RESET_SECONDS: int = 600  # 10 minutes in PAUSED state

    # Security
    ADMIN_API_KEY: str = "eventpulse_admin_secret_token"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

