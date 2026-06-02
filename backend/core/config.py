"""Diaa Store — Backend Configuration"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Service Hub"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me"
    API_V1_PREFIX: str = "/api/v1"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_IDS: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_USE_WEBHOOK: bool = False
    ADMIN_GROUP_ID: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/diaastore"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # Crypto
    CRYPTO_PAYMENT_TIMEOUT_MINUTES: int = 30
    USDT_TRC20_ADDRESS: str = ""
    USDT_BEP20_ADDRESS: str = ""
    BTC_ADDRESS: str = ""
    ETH_ADDRESS: str = ""
    SOL_ADDRESS: str = ""

    # Storage
    STORAGE_BACKEND: str = "local"
    MEDIA_DIR: str = "./media"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @property
    def admin_ids(self) -> list[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(",") if x.strip()]

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    class Config:
        env_file = ("../.env", ".env")
        case_sensitive = True
        extra = "ignore"


settings = Settings()
