"""
Create (or recreate) the Qdrant collection for RAG-Patterns-Lab.

Run this once before ingestion to set up the vector collection
with the correct dimensionality and distance metric.

Usage:
    python -m rag_qdrant.create_collection
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from utils.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
from embeddings.embedder import _get_model


def create_collection() -> None:
    """Create (or recreate) the Qdrant collection."""

    # Determine embedding dimension from the model
    model = _get_model()
    vector_size = model.get_sentence_embedding_dimension()
    print(f"[create_collection] Embedding dimension: {vector_size}")

    # Connect to Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"[create_collection] Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")

    # Recreate the collection (drops existing data if any)
    client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )
    print(f"[create_collection] Collection '{QDRANT_COLLECTION}' created with cosine distance.")

    # Verify
    info = client.get_collection(QDRANT_COLLECTION)
    print(f"[create_collection] Verified — status: {info.status}, points: {info.points_count}")


if __name__ == "__main__":
    create_collection()
