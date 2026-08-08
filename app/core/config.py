from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "PeopleOps Assistant"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"
    policy_corpus_directory: Path = PROJECT_ROOT / "policy_corpus"
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    llm_provider: str = "not-configured"
    llm_model: str = "not-configured"
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    tool_timeout_seconds: int = Field(default=20, ge=1, le=120)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
