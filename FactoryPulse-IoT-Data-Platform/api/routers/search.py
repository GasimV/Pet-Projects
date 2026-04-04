"""Search router — semantic search over incidents and manuals via Qdrant."""

import os
import requests

from fastapi import APIRouter, HTTPException

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

def _get_qdrant_search_url() -> str:
    host = os.environ.get("QDRANT_HOST", "qdrant")
    port = int(os.environ.get("QDRANT_PORT", 6333))
    return f"http://{host}:{port}/collections/incidents/points/search"


@router.post("/semantic", response_model=list[SearchResult])
async def semantic_search(request: SearchRequest):
    """Semantic search over incidents and maintenance manuals.

    Embeds the query using sentence-transformers/all-MiniLM-L6-v2,
    then searches the Qdrant 'incidents' collection for nearest neighbours.
    """
    try:
        model = _get_embedding_model()
        query_vector = model.encode(request.query).tolist()

        response = requests.post(
            _get_qdrant_search_url(),
            json={
                "vector": query_vector,
                "limit": request.limit,
                "with_payload": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        results = response.json().get("result", [])

        return [
            SearchResult(
                id=str(hit.get("id")),
                title=(hit.get("payload") or {}).get("title", ""),
                text=(hit.get("payload") or {}).get("text", ""),
                device_id=(hit.get("payload") or {}).get("device_id"),
                severity=(hit.get("payload") or {}).get("severity"),
                source=(hit.get("payload") or {}).get("source", "unknown"),
                score=float(hit.get("score", 0.0)),
            )
            for hit in results
        ]

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}")
