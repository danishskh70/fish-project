from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    cors_origins: str = (
    "http://localhost:5173,"
    "http://localhost:8080,"
    "http://127.0.0.1:5173,"
    "https://8e593bea-3720-587a-8e86-f0fc26cf1c79.lovableproject.com"
)
    cors_origin_regex: str = r"https://.*\.(lovable\.app|lovableproject\.com)"

    app_env: str = "development"
    session_cookie_name: str = "session"
    session_cookie_secure: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_idle_hours: int = 8
    session_absolute_days: int = 7
    login_max_failures: int = 5
    login_lock_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()