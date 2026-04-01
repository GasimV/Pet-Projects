"""Centralized configuration via environment variables with Pydantic."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMBackendType(str, Enum):
    MOCK = "mock"
    OLLAMA = "ollama"
    VLLM = "vllm"
    TRITON = "triton"


class EmbeddingBackendType(str, Enum):
    MOCK = "mock"
    OLLAMA = "ollama"
    SENTENCE_TRANSFORMERS = "sentence-transformers"


class EnvironmentMode(str, Enum):
    DEV = "dev"
    GPU = "gpu"
    PRODUCTION = "production"


class Settings(BaseSettings):
    # ── Environment ──
    environment: EnvironmentMode = EnvironmentMode.DEV

    # ── LLM Backend ──
    llm_backend: LLMBackendType = LLMBackendType.MOCK
    llm_timeout: int = 60
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7
    llm_stream: bool = True

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:270m"

    # vLLM
    vllm_base_url: str = "http://localhost:8000"
    vllm_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # Triton
    triton_http_url: str = "http://localhost:8001"
    triton_grpc_url: str = "localhost:8002"
    triton_model: str = "llama-3.1-8b"

    # ── Embedding ──
    embedding_backend: EmbeddingBackendType = EmbeddingBackendType.MOCK
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Service Ports ──
    api_gateway_port: int = 8080
    frontend_port: int = 8501
    agent_service_port: int = 50051
    rag_service_port: int = 50052
    mcp_server_port: int = 50053
    eval_service_port: int = 50054
    release_controller_port: int = 50055

    # ── Infrastructure ──
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    postgres_url: str = "postgresql://copilot:copilot@localhost:5432/copilot"
    mlflow_tracking_uri: str = "http://localhost:5000"

    # ── Observability ──
    prometheus_port: int = 9090
    grafana_port: int = 3000
    alertmanager_port: int = 9093
    logstash_port: int = 5044

    # ── Logging ──
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def is_gpu_mode(self) -> bool:
        return self.environment in (EnvironmentMode.GPU, EnvironmentMode.PRODUCTION)

    @property
    def default_llm_backend(self) -> LLMBackendType:
        if self.is_gpu_mode:
            return LLMBackendType.VLLM
        return self.llm_backend


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
