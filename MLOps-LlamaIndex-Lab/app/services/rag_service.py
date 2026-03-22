"""
RAG orchestration service.

Wraps ingestion and querying so the API layer stays free of
LlamaIndex-specific logic.
"""

from typing import Dict, List

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.ingestion import ingest_documents, load_all_documents
from app.rag.vector_store import get_qdrant_client

logger = get_logger(__name__)


def run_ingestion() -> Dict:
    """Ingest all documents from the uploads folder. Returns a summary."""
    docs = load_all_documents()
    index = ingest_documents(docs)
    return {
        "status": "ok",
        "documents_ingested": len(docs),
        "collection": settings.qdrant_collection,
    }


def query_knowledge_base(question: str) -> Dict:
    """
    Query the RAG pipeline and return the answer with source references.

    We import get_query_engine here (not at module level) to avoid
    loading the LLM at import time.
    """
    from app.rag.query_engine import get_query_engine

    engine = get_query_engine()
    response = engine.query(question)

    # Extract source references from response metadata
    sources: List[Dict] = []
    for node in response.source_nodes:
        sources.append({
            "text": node.node.get_content()[:300],
            "score": round(node.score or 0.0, 4),
            "source": node.node.metadata.get("source", "unknown"),
        })

    return {
        "answer": str(response),
        "sources": sources,
    }


def get_index_status() -> Dict:
    """Return metadata about the current vector store state."""
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(settings.qdrant_collection)
        return {
            "qdrant_reachable": True,
            "collection": settings.qdrant_collection,
            "vectors_count": collection_info.vectors_count,
            "points_count": collection_info.points_count,
        }
    except Exception as exc:
        logger.warning("Could not reach Qdrant: %s", exc)
        return {
            "qdrant_reachable": False,
            "error": str(exc),
        }
