"""
Query engine factory.

Builds a LlamaIndex query engine from the vector store, using the
configured LLM for answer generation.
"""

from llama_index.core import Settings as LlamaSettings, VectorStoreIndex, StorageContext

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.embeddings import build_embedding_model
from app.rag.llm_factory import build_llm
from app.rag.vector_store import get_vector_store

logger = get_logger(__name__)


def get_query_engine():
    """
    Return a query engine wired to the Qdrant vector store and the
    configured LLM.  Each call rebuilds from the store so newly
    ingested documents are always visible.
    """
    embed_model = build_embedding_model()
    LlamaSettings.embed_model = embed_model

    llm = build_llm()
    LlamaSettings.llm = llm

    vector_store = get_vector_store()
    storage_ctx = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_ctx,
    )

    logger.info("Query engine ready  provider=%s  model=%s", settings.llm_provider, settings.llm_model)
    return index.as_query_engine(similarity_top_k=3)
