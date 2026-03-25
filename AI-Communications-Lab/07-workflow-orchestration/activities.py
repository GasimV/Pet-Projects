"""
Temporal Activities — individual steps in the document processing pipeline.

Each activity is a single, retriable unit of work. Temporal handles
retry policies, timeouts, and failure tracking automatically.
"""

import hashlib
import random
import time
from dataclasses import dataclass

from temporalio import activity


@dataclass
class DocumentInfo:
    document_id: str
    filename: str
    content: str = ""
    chunks: list[str] | None = None
    embeddings: list[list[float]] | None = None


@activity.defn
async def parse_document(doc: DocumentInfo) -> DocumentInfo:
    """Extract text content from the uploaded document."""
    activity.logger.info(f"Parsing {doc.filename}")
    time.sleep(0.5)  # simulate I/O

    # Simulate occasional transient failure (Temporal will retry)
    if random.random() < 0.1:
        raise RuntimeError(f"Transient parse error for {doc.filename}")

    doc.content = f"Extracted text content from {doc.filename}. " * 5
    return doc


@activity.defn
async def chunk_document(doc: DocumentInfo) -> DocumentInfo:
    """Split document content into chunks for embedding."""
    activity.logger.info(f"Chunking {doc.filename} ({len(doc.content)} chars)")
    time.sleep(0.3)

    # Simple fixed-size chunking
    words = doc.content.split()
    chunk_size = 10
    doc.chunks = [
        " ".join(words[i : i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]
    activity.logger.info(f"Created {len(doc.chunks)} chunks")
    return doc


@activity.defn
async def embed_chunks(doc: DocumentInfo) -> DocumentInfo:
    """Generate embeddings for each chunk (mock)."""
    activity.logger.info(f"Embedding {len(doc.chunks)} chunks")
    time.sleep(0.5)

    # Mock embedding: hash-based deterministic vectors
    doc.embeddings = []
    for chunk in doc.chunks:
        h = hashlib.sha256(chunk.encode()).hexdigest()
        vec = [int(h[i : i + 2], 16) / 255.0 for i in range(0, 32, 2)]
        doc.embeddings.append(vec)

    return doc


@activity.defn
async def store_embeddings(doc: DocumentInfo) -> str:
    """Store embeddings in vector database (simulated)."""
    activity.logger.info(
        f"Storing {len(doc.embeddings)} vectors for {doc.filename}"
    )
    time.sleep(0.3)
    return f"stored_{doc.document_id}"


@activity.defn
async def notify_completion(doc: DocumentInfo) -> str:
    """Send completion notification."""
    msg = (
        f"Pipeline complete: {doc.filename} — "
        f"{len(doc.chunks)} chunks, {len(doc.embeddings)} embeddings"
    )
    activity.logger.info(msg)
    return msg
