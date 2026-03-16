"""
Query the Qdrant collection with a sample question.

Embeds the query, performs semantic search, and prints the
top-k results with scores and metadata.

Usage:
    python -m rag_qdrant.query
"""

from __future__ import annotations

from qdrant_client import QdrantClient

from utils.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from embeddings.embedder import embed_one


SAMPLE_QUERY = "How does GraphRAG improve retrieval compared to standard RAG?"
TOP_K = 5


def query_qdrant(query_text: str, top_k: int = TOP_K) -> list[dict]:
    """Embed query_text and search Qdrant for the closest chunks."""
    query_vector = embed_one(query_text)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )

    hits: list[dict] = []
    for hit in response.points:
        hits.append(
            {
                "id": hit.id,
                "score": hit.score,
                **(hit.payload or {}),
            }
        )
    return hits


def print_results(query_text: str, hits: list[dict]) -> None:
    """Pretty-print search results."""
    print("=" * 70)
    print(f"  QUERY: {query_text}")
    print("=" * 70)

    if not hits:
        print("  No results found.")
        return

    for rank, hit in enumerate(hits, start=1):
        print(f"\n── Result {rank}  (score: {hit['score']:.4f}) ──")
        print(f"  Chunk ID    : {hit['id']}")
        print(f"  Chunk Index : {hit.get('chunk_index')}")
        print(f"  Source      : {hit.get('source')}")
        print(f"  Prev / Next : {hit.get('previous_chunk_id')} / {hit.get('next_chunk_id')}")
        text = hit.get("text", "")
        display = text[:300] + " ..." if len(text) > 300 else text
        print(f"  Text        : {display}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    hits = query_qdrant(SAMPLE_QUERY)
    print_results(SAMPLE_QUERY, hits)