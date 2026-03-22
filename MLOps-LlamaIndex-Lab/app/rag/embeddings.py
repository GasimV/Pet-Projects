"""
Pluggable embedding model factory.

Returns a LlamaIndex embedding model based on the configured provider.
- "huggingface": runs BAAI/bge-m3 locally via sentence-transformers (needs torch)
- "ollama": calls Ollama's /api/embeddings endpoint (lightweight, no torch)
"""

from llama_index.core.embeddings import BaseEmbedding

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_embedding_model() -> BaseEmbedding:
    """Instantiate the embedding backend selected via ``EMBEDDING_PROVIDER``."""
    provider = settings.embedding_provider.lower()
    logger.info(
        "Loading embedding model  provider=%s  model=%s",
        provider, settings.embedding_model,
    )

    if provider == "huggingface":
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        return HuggingFaceEmbedding(model_name=settings.embedding_model)

    if provider == "ollama":
        from llama_index.embeddings.ollama import OllamaEmbedding

        return OllamaEmbedding(
            model_name=settings.embedding_model,
            base_url=settings.llm_api_base,
        )

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. "
        "Supported: huggingface, ollama."
    )
