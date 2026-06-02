"""Bot configuration"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    TELEGRAM_BOT_TOKEN: str = ""  # Alias
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # Database (direct connection for bot queries)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/diaastore"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Admin IDs (Telegram user IDs that can use /admin)
    ADMIN_IDS: str = ""  # Comma separated
    TELEGRAM_ADMIN_IDS: str = ""  # Alias

    # Store settings
    STORE_NAME: str = "Service Hub"
    DEFAULT_CURRENCY: str = "USD"
    DEFAULT_LANGUAGE: str = "en"
    SUPPORT_USERNAME: str = ""
    CHANNEL_URL: str = ""

    # Payment
    PAYMENT_TIMEOUT_MINUTES: int = 30
    AUTO_DELIVERY: bool = True

    # Reseller API (VEX)
    RESELLER_API_BASE_URL: str = ""
    RESELLER_API_KEY: str = ""

    class Config:
        env_file = ("../.env", ".env")
        extra = "ignore"

    @property
    def bot_token(self) -> str:
        """Get bot token from either field"""
        return self.BOT_TOKEN or self.TELEGRAM_BOT_TOKEN

    @property
    def admin_ids_list(self) -> list[int]:
        ids_str = self.ADMIN_IDS or self.TELEGRAM_ADMIN_IDS
        if not ids_str:
            return []
        return [int(x.strip()) for x in ids_str.split(",") if x.strip()]


settings = Settings()
