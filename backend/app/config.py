from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./pharmarca.db"
    secret_key: str = "change-this-before-production"
    groq_api_key: str | None = None
    groq_model: str = "qwen/qwen3.8-27b"
    demo_mode: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
