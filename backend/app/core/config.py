from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    frontend_url: str = "http://localhost:5173"
    max_result_rows: int = 100
    query_timeout_seconds: int = 10
    session_ttl_minutes: int = 60
    vanna_data_dir: str = "./.vanna_data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
