"""Search router — semantic search over incidents and manuals via Qdrant."""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient

from models import SearchRequest, SearchResult

router = APIRouter(prefix="/api/v1/search", tags=["search"])

# Lazy-loaded sentence-transformers model
_model = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers model on first request."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        _model = SentenceTransformer(model_name)
    return _model


def _get_qdrant_client():
    return QdrantClient(
        host=os.environ.get("QDRANT_HOST", "qdrant"),
        port=int(os.environ.get("QDRANT_PORT", 6333)),
    )


@router.post("/semantic", response_model=list[SearchResult])
async def semantic_search(request: SearchRequest):
    """Semantic search over incidents and maintenance manuals.

    Embeds the query using sentence-transformers/all-MiniLM-L6-v2,
    then searches the Qdrant 'incidents' collection for nearest neighbours.
    """
    try:
        model = _get_embedding_model()
        query_vector = model.encode(request.query).tolist()

        client = _get_qdrant_client()
        results = client.search(
            collection_name="incidents",
            query_vector=query_vector,
            limit=request.limit,
            with_payload=True,
        )

        return [
            SearchResult(
                id=str(hit.id),
                title=hit.payload.get("title", ""),
                text=hit.payload.get("text", ""),
                device_id=hit.payload.get("device_id"),
                severity=hit.payload.get("severity"),
                source=hit.payload.get("source", "unknown"),
                score=hit.score,
            )
            for hit in results
        ]

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}")
