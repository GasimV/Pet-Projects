from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from llama_index.core import Document, Settings, VectorStoreIndex
    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.vector_stores.qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover
    Document = None
    Settings = None
    VectorStoreIndex = None
    SentenceSplitter = None
    OllamaEmbedding = None
    QdrantVectorStore = None
    QdrantClient = None


class RagEngine:
    def __init__(self, knowledge_dir: str, qdrant_url: str, ollama_base_url: str, embed_model: str) -> None:
        self._knowledge_dir = Path(knowledge_dir)
        self._qdrant_url = qdrant_url
        self._ollama_base_url = ollama_base_url
        self._embed_model = embed_model
        self._index = None
        self._fallback_docs = self._load_docs()

    def _load_docs(self) -> list[tuple[str, str]]:
        docs: list[tuple[str, str]] = []
        for path in self._knowledge_dir.rglob("*.md"):
            docs.append((str(path.relative_to(self._knowledge_dir)), path.read_text(encoding="utf-8")))
        return docs

    def ensure_index(self):
        if self._index is not None or VectorStoreIndex is None:
            return self._index
        try:
            client = QdrantClient(url=self._qdrant_url)
            vector_store = QdrantVectorStore(client=client, collection_name="voice_platform_knowledge")
            Settings.embed_model = OllamaEmbedding(
                model_name=self._embed_model,
                base_url=self._ollama_base_url,
            )
            Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)
            documents = [Document(text=text, metadata={"source": source}) for source, text in self._fallback_docs]
            self._index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
        except Exception:
            logger.exception("Falling back to local text retrieval")
        return self._index

    def retrieve(self, query: str, top_k: int = 3) -> tuple[str, list[dict[str, object]]]:
        index = self.ensure_index()
        if index is not None:
            retriever = index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            citations = [
                {
                    "source": str(node.metadata.get("source", "unknown")),
                    "excerpt": node.text[:280],
                    "score": float(getattr(node, "score", 0.0) or 0.0),
                }
                for node in nodes
            ]
            context = "\n\n".join(item["excerpt"] for item in citations)
            return context, citations

        lowered = query.lower()
        citations: list[dict[str, object]] = []
        for source, text in self._fallback_docs:
            if lowered in text.lower():
                excerpt = next((line for line in text.splitlines() if lowered in line.lower()), text[:280])
                citations.append({"source": source, "excerpt": excerpt[:280], "score": 1.0})
        if not citations and self._fallback_docs:
            source, text = self._fallback_docs[0]
            citations.append({"source": source, "excerpt": text[:280], "score": 0.1})
        context = "\n\n".join(item["excerpt"] for item in citations[:top_k])
        return context, citations[:top_k]

