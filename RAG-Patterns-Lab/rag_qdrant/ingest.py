"""
Ingest documents into the Qdrant collection.

Reads data/documents.txt, chunks the text, embeds each chunk,
and upserts vectors with rich payload metadata — including
previous/next chunk IDs to demonstrate lightweight graph-like
adjacency via Qdrant payloads.

Usage:
    python -m rag_qdrant.ingest
"""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from tqdm import tqdm

from utils.config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, DOCUMENTS_PATH
from utils.chunking import load_and_chunk
from embeddings.embedder import embed


# ── Shared chunk preparation ──────────────────────────────────────

def prepare_chunks(
    filepath: str,
    chunk_size: int = 128,
    overlap: int = 32,
    source: str = "documents.txt",
) -> list[dict]:
    """Load a text file, chunk it, and return a list of chunk metadata dicts.

    Each dict contains:
        id, text, chunk_index, source, doc_id,
        previous_chunk_id, next_chunk_id

    This function is shared between the Qdrant and Neo4j pipelines so
    both stores work with identical chunk boundaries and IDs.
    """
    chunks = load_and_chunk(str(filepath), chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        print("[prepare_chunks] No chunks produced — is the source file empty?")
        return []

    # Generate a stable document-level ID
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source))

    # Build metadata records with sequential IDs
    records: list[dict] = []
    for idx, text in enumerate(chunks):
        records.append({
            "id": idx,
            "text": text,
            "chunk_index": idx,
            "source": source,
            "doc_id": doc_id,
            "previous_chunk_id": idx - 1 if idx > 0 else None,
            "next_chunk_id": idx + 1 if idx < len(chunks) - 1 else None,
        })

    return records


# ── Qdrant ingestion ──────────────────────────────────────────────

BATCH_SIZE = 32


def ingest() -> None:
    """Run the full ingestion pipeline: chunk → embed → upsert."""

    print(f"[ingest] Reading chunks from {DOCUMENTS_PATH} ...")
    records = prepare_chunks(DOCUMENTS_PATH)
    if not records:
        return

    print(f"[ingest] Produced {len(records)} chunks. Embedding ...")
    texts = [r["text"] for r in records]
    vectors = embed(texts)

    # Connect to Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"[ingest] Connected to Qdrant. Upserting into '{QDRANT_COLLECTION}' ...")

    # Upsert in batches
    points = []
    for rec, vec in zip(records, vectors):
        points.append(
            PointStruct(
                id=rec["id"],
                vector=vec,
                payload={
                    "text": rec["text"],
                    "chunk_index": rec["chunk_index"],
                    "source": rec["source"],
                    "doc_id": rec["doc_id"],
                    "previous_chunk_id": rec["previous_chunk_id"],
                    "next_chunk_id": rec["next_chunk_id"],
                },
            )
        )

    for i in tqdm(range(0, len(points), BATCH_SIZE), desc="Upserting"):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(collection_name=QDRANT_COLLECTION, points=batch)

    print(f"[ingest] Done — {len(points)} points upserted into '{QDRANT_COLLECTION}'.")

    # Show a sample payload
    print("\n── Sample payload (chunk 0) ──")
    sample = client.retrieve(collection_name=QDRANT_COLLECTION, ids=[0])
    if sample:
        for key, val in sample[0].payload.items():
            display = val if key != "text" else val[:80] + "..."
            print(f"  {key}: {display}")


if __name__ == "__main__":
    ingest()
