"""Vector store abstraction with Qdrant and in-memory fallback."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from shared.llm_backend.base import LLMClient
from shared.logging import get_logger

logger = get_logger(__name__)


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class BaseVectorStore(ABC):
    @abstractmethod
    async def ingest(self, document_id: str, content: str, metadata: dict, collection: str) -> int:
        ...

    @abstractmethod
    async def retrieve(self, query: str, top_k: int, collection: str, score_threshold: float) -> list[dict]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class VectorStore(BaseVectorStore):
    """Qdrant-backed vector store."""

    def __init__(self, qdrant_client, embedding_client: LLMClient, collection_name: str = "copilot_docs"):
        self._qdrant = qdrant_client
        self._embedder = embedding_client
        self._default_collection = collection_name
        self._ensure_collection(collection_name)

    def _ensure_collection(self, name: str):
        try:
            from qdrant_client.models import Distance, VectorParams

            collections = [c.name for c in self._qdrant.get_collections().collections]
            if name not in collections:
                self._qdrant.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info("collection_created", name=name)
        except Exception as e:
            logger.error("collection_create_error", error=str(e))

    async def ingest(self, document_id: str, content: str, metadata: dict, collection: str) -> int:
        chunks = _chunk_text(content)
        embeddings_resp = await self._embedder.embeddings(chunks)
        vectors = embeddings_resp.embeddings

        from qdrant_client.models import PointStruct

        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={
                        "document_id": document_id,
                        "content": chunk,
                        "chunk_index": i,
                        **metadata,
                    },
                )
            )

        self._ensure_collection(collection)
        self._qdrant.upsert(collection_name=collection, points=points)
        logger.info("ingested", document_id=document_id, chunks=len(points))
        return len(points)

    async def retrieve(self, query: str, top_k: int, collection: str, score_threshold: float) -> list[dict]:
        embeddings_resp = await self._embedder.embeddings([query])
        query_vec = embeddings_resp.embeddings[0]

        results = self._qdrant.search(
            collection_name=collection or self._default_collection,
            query_vector=query_vec,
            limit=top_k,
            score_threshold=score_threshold if score_threshold > 0 else None,
        )

        return [
            {
                "document_id": r.payload.get("document_id", ""),
                "content": r.payload.get("content", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k not in ("document_id", "content")},
            }
            for r in results
        ]

    async def health_check(self) -> bool:
        try:
            self._qdrant.get_collections()
            return True
        except Exception:
            return False


class InMemoryVectorStore(BaseVectorStore):
    """Fallback in-memory vector store for dev mode without Qdrant."""

    def __init__(self, embedding_client: LLMClient):
        self._embedder = embedding_client
        self._docs: dict[str, list[dict]] = {}  # collection -> [doc_records]

    async def ingest(self, document_id: str, content: str, metadata: dict, collection: str) -> int:
        chunks = _chunk_text(content)
        embeddings_resp = await self._embedder.embeddings(chunks)
        vectors = embeddings_resp.embeddings

        if collection not in self._docs:
            self._docs[collection] = []

        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            self._docs[collection].append({
                "document_id": document_id,
                "content": chunk,
                "vector": vec,
                "metadata": {**metadata, "chunk_index": i},
            })

        return len(chunks)

    async def retrieve(self, query: str, top_k: int, collection: str, score_threshold: float) -> list[dict]:
        docs = self._docs.get(collection, [])
        if not docs:
            return []

        embeddings_resp = await self._embedder.embeddings([query])
        query_vec = embeddings_resp.embeddings[0]

        scored = []
        for doc in docs:
            score = self._cosine_similarity(query_vec, doc["vector"])
            if score >= score_threshold:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "document_id": doc["document_id"],
                "content": doc["content"],
                "score": score,
                "metadata": doc["metadata"],
            }
            for score, doc in scored[:top_k]
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def health_check(self) -> bool:
        return True
