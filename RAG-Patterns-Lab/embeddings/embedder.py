"""
Embedding helper for RAG-Patterns-Lab.

Uses SentenceTransformers with the model specified in the project
config (default: BAAI/bge-m3). Automatically uses GPU if a
CUDA-enabled PyTorch installation is detected; falls back to CPU.
"""

from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer

from utils.config import EMBEDDING_MODEL

# ── Detect device ──────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── Lazy-loaded singleton model ────────────────────────────────────
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the SentenceTransformer model once and cache it."""
    global _model
    if _model is None:
        print(f"[embedder] Loading model '{EMBEDDING_MODEL}' on {DEVICE} ...")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        print(f"[embedder] Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts and return a list of float vectors.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings.tolist()


def embed_one(text: str) -> list[float]:
    """Embed a single text string.

    Args:
        text: The string to embed.

    Returns:
        A single embedding vector as a list of floats.
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


# ── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    sample_texts = [
        "Qdrant is a vector database.",
        "Neo4j is a graph database.",
    ]
    vectors = embed(sample_texts)
    print(f"\nEmbedded {len(vectors)} texts.")
    print(f"Vector dimension: {len(vectors[0])}")
