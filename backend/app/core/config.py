from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    frontend_url: str = "http://localhost:5173"
    max_result_rows: int = 100
    query_timeout_seconds: int = 10
    session_ttl_minutes: int = 60
    # Write mode (INSERT only). OFF unless the server operator turns it on.
    allow_writes: bool = False
    max_write_rows: int = 50
    write_confirm_ttl_seconds: int = 300
    vanna_data_dir: str = "./.vanna_data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
