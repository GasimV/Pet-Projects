"""In-memory seed data for the GraphQL demo.

In production this would be a database; for a learning demo, module-level
dicts are enough to exercise nested queries, batching (DataLoader),
pagination, and mutations without infrastructure setup.
"""

from datetime import datetime, timezone


# ---- Users -----------------------------------------------------------------
USERS: dict[str, dict] = {
    "u1": {"id": "u1", "name": "Alice", "email": "alice@example.com"},
    "u2": {"id": "u2", "name": "Bob", "email": "bob@example.com"},
}

# ---- Model catalog (interface + two implementations) -----------------------
CHAT_MODELS: dict[str, dict] = {
    "m-gemma": {
        "id": "m-gemma",
        "name": "gemma4:e2b",
        "provider": "ollama",
        "context_window": 8192,
        "supports_streaming": True,
    },
}

EMBEDDING_MODELS: dict[str, dict] = {
    "m-bge": {
        "id": "m-bge",
        "name": "bge-m3:latest",
        "provider": "ollama",
        "dimensions": 1024,
    },
}

# ---- Conversations ---------------------------------------------------------
CONVERSATIONS: dict[str, dict] = {
    "c1": {
        "id": "c1",
        "title": "What is RAG?",
        "user_id": "u1",
        "created_at": datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc),
    },
    "c2": {
        "id": "c2",
        "title": "Embeddings explained",
        "user_id": "u1",
        "created_at": datetime(2026, 4, 11, 9, 30, tzinfo=timezone.utc),
    },
    "c3": {
        "id": "c3",
        "title": "GraphQL vs REST",
        "user_id": "u2",
        "created_at": datetime(2026, 4, 12, 16, 15, tzinfo=timezone.utc),
    },
}

# ---- Messages indexed by conversation_id (natural batching key) ------------
MESSAGES_BY_CONVERSATION: dict[str, list[dict]] = {
    "c1": [
        {
            "id": "msg1",
            "role": "user",
            "content": "What is RAG?",
            "tokens_used": None,
            "model_id": None,
            "created_at": datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc),
        },
        {
            "id": "msg2",
            "role": "assistant",
            "content": "Retrieval-Augmented Generation grounds an LLM in retrieved documents.",
            "tokens_used": 42,
            "model_id": "m-gemma",
            "created_at": datetime(2026, 4, 10, 14, 0, 5, tzinfo=timezone.utc),
        },
    ],
    "c2": [
        {
            "id": "msg3",
            "role": "user",
            "content": "What is an embedding?",
            "tokens_used": None,
            "model_id": None,
            "created_at": datetime(2026, 4, 11, 9, 30, tzinfo=timezone.utc),
        },
        {
            "id": "msg4",
            "role": "assistant",
            "content": "A vector representation of text in a high-dimensional space.",
            "tokens_used": 28,
            "model_id": "m-gemma",
            "created_at": datetime(2026, 4, 11, 9, 30, 5, tzinfo=timezone.utc),
        },
    ],
    "c3": [
        {
            "id": "msg5",
            "role": "user",
            "content": "When should I use GraphQL?",
            "tokens_used": None,
            "model_id": None,
            "created_at": datetime(2026, 4, 12, 16, 15, tzinfo=timezone.utc),
        },
    ],
}

# ---- Documents -------------------------------------------------------------
DOCUMENTS: dict[str, dict] = {
    "d1": {"id": "d1", "title": "Intro to RAG", "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc)},
    "d2": {"id": "d2", "title": "Embedding fundamentals", "created_at": datetime(2026, 3, 5, tzinfo=timezone.utc)},
    "d3": {"id": "d3", "title": "GraphQL design patterns", "created_at": datetime(2026, 3, 12, tzinfo=timezone.utc)},
    "d4": {"id": "d4", "title": "Vector databases", "created_at": datetime(2026, 3, 20, tzinfo=timezone.utc)},
    "d5": {"id": "d5", "title": "Prompt engineering", "created_at": datetime(2026, 3, 25, tzinfo=timezone.utc)},
}

# ---- Chunks indexed by document --------------------------------------------
CHUNKS_BY_DOCUMENT: dict[str, list[dict]] = {
    "d1": [
        {"id": "ch1", "document_id": "d1", "content": "RAG retrieves documents before generating."},
        {"id": "ch2", "document_id": "d1", "content": "Retrieval reduces hallucination."},
    ],
    "d2": [
        {"id": "ch3", "document_id": "d2", "content": "Embeddings encode semantic similarity."},
        {"id": "ch4", "document_id": "d2", "content": "Cosine similarity measures distance."},
    ],
    "d3": [
        {"id": "ch5", "document_id": "d3", "content": "GraphQL has one endpoint and a typed schema."},
    ],
    "d4": [
        {"id": "ch6", "document_id": "d4", "content": "Qdrant and Pinecone store vector embeddings."},
    ],
    "d5": [
        {"id": "ch7", "document_id": "d5", "content": "Few-shot prompting steers model behavior."},
    ],
}

# ---- Tags ------------------------------------------------------------------
TAGS: dict[str, dict] = {
    "t1": {"id": "t1", "name": "rag"},
    "t2": {"id": "t2", "name": "embeddings"},
    "t3": {"id": "t3", "name": "graphql"},
    "t4": {"id": "t4", "name": "vector-db"},
}

DOCUMENT_TAGS: dict[str, list[str]] = {
    "d1": ["t1", "t2"],
    "d2": ["t2"],
    "d3": ["t3"],
    "d4": ["t2", "t4"],
    "d5": ["t1"],
}

# ---- Embeddings indexed by chunk_id (mock vectors for the demo) ------------
EMBEDDINGS_BY_CHUNK: dict[str, dict] = {
    chunk_id: {
        "vector": [round(0.01 * i + 0.001 * idx, 4) for i in range(8)],
        "dimensions": 8,
        "metadata": {"source_chunk": chunk_id, "version": 1},
    }
    for idx, chunk_id in enumerate(["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7"])
}
