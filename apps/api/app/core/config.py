from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ContentFlow CN API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://contentflow:contentflow@db:5432/contentflow"
    ai_provider: str = "mock"
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    provider_timeout_seconds: float = 30.0
    provider_max_retries: int = 2
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
