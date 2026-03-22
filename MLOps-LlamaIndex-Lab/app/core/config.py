"""
Application configuration loaded from environment variables.

Uses pydantic-settings so every value can be overridden via .env or
shell environment variables. Sensible defaults are provided for local
development — the app starts without any .env file at all.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is two levels up from this file (app/core/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration for the RAG application."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM Provider --------------------------------------------------------
    llm_provider: str = "huggingface"
    llm_model: str = "google/gemma-3-1b-it"
    llm_api_key: str = ""
    llm_api_base: str = "http://localhost:11434"

    # --- Embedding Model -----------------------------------------------------
    embedding_provider: str = "huggingface"
    embedding_model: str = "BAAI/bge-m3"

    # --- Qdrant Vector Store -------------------------------------------------
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # --- Chunking ------------------------------------------------------------
    chunk_size: int = 512
    chunk_overlap: int = 50

    # --- App -----------------------------------------------------------------
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    upload_dir: str = "data/uploads"

    # --- Derived helpers (not env vars) --------------------------------------
    @property
    def upload_path(self) -> Path:
        """Absolute path to the upload directory."""
        p = Path(self.upload_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p


# Singleton — import this everywhere
settings = Settings()
