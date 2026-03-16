"""
Embedding helper for RAG-Patterns-Lab.

Uses SentenceTransformers with the model specified in the project
config (default: BAAI/bge-m3). Uses CUDA only when the installed
PyTorch build and GPU capability are compatible; otherwise falls
back to CPU.
"""

from __future__ import annotations

import torch
from sentence_transformers import SentenceTransformer

from utils.config import EMBEDDING_MODEL


def _detect_device() -> str:
    """Choose a safe device for embedding.

    Returns:
        "cuda" only if CUDA is available and the GPU capability is
        supported by this project/runtime; otherwise "cpu".
    """
    if not torch.cuda.is_available():
        return "cpu"

    try:
        major, minor = torch.cuda.get_device_capability(0)
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[embedder] Detected CUDA GPU: {gpu_name} (sm_{major}{minor})")

        # Your installed PyTorch build only supports newer GPUs.
        # Keep the threshold conservative.
        if major >= 7:
            return "cuda"

        print(
            f"[embedder] CUDA is available, but GPU compute capability "
            f"sm_{major}{minor} is too old for this PyTorch build. Falling back to CPU."
        )
        return "cpu"

    except Exception as e:
        print(f"[embedder] CUDA check failed ({e}). Falling back to CPU.")
        return "cpu"


DEVICE = _detect_device()

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the SentenceTransformer model once and cache it."""
    global _model
    if _model is None:
        print(f"[embedder] Loading model '{EMBEDDING_MODEL}' on {DEVICE} ...")
        _model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        print(
            f"[embedder] Model loaded. Embedding dimension: "
            f"{_model.get_sentence_embedding_dimension()}"
        )
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts and return a list of float vectors."""
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings.tolist()


def embed_one(text: str) -> list[float]:
    """Embed a single text string."""
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


if __name__ == "__main__":
    sample_texts = [
        "Qdrant is a vector database.",
        "Neo4j is a graph database.",
    ]
    vectors = embed(sample_texts)
    print(f"\nEmbedded {len(vectors)} texts.")
    print(f"Vector dimension: {len(vectors[0])}")