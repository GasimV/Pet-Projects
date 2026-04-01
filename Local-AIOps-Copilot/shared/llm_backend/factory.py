"""Factory for creating LLM clients based on configuration."""

from __future__ import annotations

from shared.config.settings import LLMBackendType, Settings, get_settings
from shared.llm_backend.base import LLMClient


def create_llm_client(
    backend: LLMBackendType | str | None = None,
    settings: Settings | None = None,
) -> LLMClient:
    """Create an LLM client for the specified backend.

    Args:
        backend: Override backend type. If None, uses settings.
        settings: Override settings. If None, uses get_settings().

    Returns:
        An initialized LLMClient instance.
    """
    settings = settings or get_settings()
    backend_type = LLMBackendType(backend) if backend else settings.llm_backend

    if backend_type == LLMBackendType.MOCK:
        from shared.llm_backend.mock_client import MockLLMClient

        return MockLLMClient()

    if backend_type == LLMBackendType.OLLAMA:
        from shared.llm_backend.ollama_client import OllamaLLMClient

        return OllamaLLMClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_timeout,
        )

    if backend_type == LLMBackendType.VLLM:
        from shared.llm_backend.vllm_client import VLLMClient

        return VLLMClient(
            base_url=settings.vllm_base_url,
            model=settings.vllm_model,
            timeout=settings.llm_timeout,
        )

    if backend_type == LLMBackendType.TRITON:
        from shared.llm_backend.triton_client import TritonClient

        return TritonClient(
            http_url=settings.triton_http_url,
            model=settings.triton_model,
            timeout=settings.llm_timeout,
            grpc_url=settings.triton_grpc_url,
        )

    raise ValueError(f"Unknown LLM backend: {backend_type}")


def create_embedding_client(
    settings: Settings | None = None,
) -> LLMClient:
    """Create an embedding client. Re-uses the LLM client since all backends
    support embeddings through the same interface."""
    return create_llm_client(settings=settings)
