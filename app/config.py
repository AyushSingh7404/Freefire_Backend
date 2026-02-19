from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    database_hostname: str
    database_port: str = "5432"
    database_password: str
    database_name: str
    database_username: str

    # ── JWT ───────────────────────────────────────────────────
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Gmail SMTP ────────────────────────────────────────────
    mail_username: str
    mail_password: str
    mail_from: str
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587

    # ── Cloudinary ────────────────────────────────────────────
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # ── Razorpay ──────────────────────────────────────────────
    razorpay_key_id: str
    razorpay_key_secret: str

    # ── App ───────────────────────────────────────────────────
    cors_origins: str = "http://localhost:4200"

    @property
    def cors_origins_list(self) -> list[str]:
        """Split comma-separated origins into a list, stripping whitespace."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.database_username}:{self.database_password}"
            f"@{self.database_hostname}:{self.database_port}/{self.database_name}"
        )

    class Config:
        env_file = ".env"
        # Case-insensitive so DATABASE_HOSTNAME and database_hostname both work
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings loader — reads .env once and reuses.
    Use this everywhere instead of instantiating Settings() directly.
    """
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()
