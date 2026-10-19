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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()