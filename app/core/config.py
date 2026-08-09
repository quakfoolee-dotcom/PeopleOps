from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import SYNTHETIC_AS_OF_DATE

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "PeopleOps Assistant"
    app_version: str = "0.5.1"
    app_env: str = "development"
    log_level: str = "INFO"
    policy_corpus_directory: Path = PROJECT_ROOT / "policy_corpus"
    rag_index_path: Path = PROJECT_ROOT / "policy_corpus" / "index" / "phase5_index.json"
    rag_embedding_dimensions: int = Field(default=384, ge=64, le=2048)
    rag_chunk_target_words: int = Field(default=240, ge=80, le=1000)
    rag_chunk_overlap_words: int = Field(default=40, ge=0, le=200)
    rag_top_k: int = Field(default=8, ge=1, le=20)
    mcp_server_url: str = "http://127.0.0.1:8000/mcp"
    llm_provider: str = "not-configured"
    llm_model: str = "not-configured"
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    tool_timeout_seconds: int = Field(default=20, ge=1, le=120)
    mcp_confirmation_secret: str = Field(
        default="peopleops-local-demo-confirmation-secret",
        min_length=32,
    )
    mcp_confirmation_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    synthetic_as_of_date: date = SYNTHETIC_AS_OF_DATE

    def model_post_init(self, __context: object) -> None:
        if self.rag_chunk_overlap_words >= self.rag_chunk_target_words:
            raise ValueError("RAG chunk overlap must be smaller than the target chunk size")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
