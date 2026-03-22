"""
Qdrant vector-store helpers.

Provides a configured QdrantVectorStore that LlamaIndex ingestion and
query pipelines can use directly.
"""

from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_qdrant_client() -> QdrantClient:
    """Create a Qdrant client pointing at the configured host/port."""
    logger.info("Connecting to Qdrant at %s:%s", settings.qdrant_host, settings.qdrant_port)
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def get_vector_store() -> QdrantVectorStore:
    """Return a QdrantVectorStore ready for use by LlamaIndex."""
    client = get_qdrant_client()
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
    )
