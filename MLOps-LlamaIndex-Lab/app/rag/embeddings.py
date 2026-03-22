"""
Embedding model initialisation.

Defaults to BAAI/bge-m3 running locally via HuggingFace.
"""

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_embedding_model() -> HuggingFaceEmbedding:
    """Return a HuggingFace embedding model instance."""
    logger.info("Loading embedding model: %s", settings.embedding_model)
    return HuggingFaceEmbedding(model_name=settings.embedding_model)
