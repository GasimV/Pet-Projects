"""Tests for the in-memory vector store (RAG fallback)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import importlib.util
import pytest

from shared.llm_backend.mock_client import MockLLMClient


def _import_vectorstore():
    spec = importlib.util.spec_from_file_location(
        "vectorstore",
        str(Path(__file__).resolve().parents[2] / "services" / "rag-service" / "app" / "vectorstore.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.InMemoryVectorStore, mod._chunk_text


InMemoryVectorStore, _chunk_text = _import_vectorstore()


def test_chunk_text_short():
    chunks = _chunk_text("short text")
    assert len(chunks) == 1
    assert chunks[0] == "short text"


def test_chunk_text_long():
    text = "word " * 200  # ~1000 chars
    chunks = _chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    # Each chunk should be at most chunk_size
    for c in chunks:
        assert len(c) <= 120  # allow some variance


@pytest.mark.asyncio
async def test_ingest_and_retrieve():
    mock_llm = MockLLMClient()
    store = InMemoryVectorStore(embedding_client=mock_llm)

    count = await store.ingest(
        document_id="doc1",
        content="Kubernetes is a container orchestration platform for managing deployments.",
        metadata={"source": "wiki"},
        collection="test",
    )
    assert count >= 1

    results = await store.retrieve(
        query="container orchestration",
        top_k=3,
        collection="test",
        score_threshold=0.0,
    )
    assert len(results) >= 1
    assert results[0]["document_id"] == "doc1"
    assert results[0]["score"] > 0


@pytest.mark.asyncio
async def test_retrieve_empty_collection():
    mock_llm = MockLLMClient()
    store = InMemoryVectorStore(embedding_client=mock_llm)
    results = await store.retrieve("anything", top_k=5, collection="empty", score_threshold=0.0)
    assert results == []


@pytest.mark.asyncio
async def test_health_check():
    mock_llm = MockLLMClient()
    store = InMemoryVectorStore(embedding_client=mock_llm)
    assert await store.health_check() is True
