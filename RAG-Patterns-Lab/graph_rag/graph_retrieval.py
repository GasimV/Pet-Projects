"""
Graph traversal helpers for the GraphRAG pipeline.

Provides functions to expand context around a chunk using
Neo4j relationship traversal.

Usage (as a library):
    from graph_rag.graph_retrieval import get_related_context
    context = get_related_context(chunk_id=3)
"""

from __future__ import annotations

from neo4j import GraphDatabase

from utils.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD


def _get_driver():
    """Create a Neo4j driver instance."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def _record_to_dict(record, key: str = "c") -> dict:
    """Convert a Neo4j node record to a plain dict."""
    node = record[key]
    return dict(node)


# ── Traversal helpers ──────────────────────────────────────────────

def get_next_chunks(chunk_id: int, limit: int = 2) -> list[dict]:
    """Return up to *limit* chunks following the given chunk (via NEXT edges)."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (start:Chunk {id: $chunk_id})-[:NEXT*1..%d]->(c:Chunk)
            RETURN c ORDER BY c.chunk_index ASC
            """ % limit,
            chunk_id=chunk_id,
        )
        chunks = [_record_to_dict(r) for r in result]
    driver.close()
    return chunks


def get_previous_chunks(chunk_id: int, limit: int = 2) -> list[dict]:
    """Return up to *limit* chunks preceding the given chunk (via PREVIOUS edges)."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (start:Chunk {id: $chunk_id})-[:PREVIOUS*1..%d]->(c:Chunk)
            RETURN c ORDER BY c.chunk_index ASC
            """ % limit,
            chunk_id=chunk_id,
        )
        chunks = [_record_to_dict(r) for r in result]
    driver.close()
    return chunks


def get_same_document_chunks(chunk_id: int) -> list[dict]:
    """Return all other chunks that share the same document as *chunk_id*."""
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (start:Chunk {id: $chunk_id})-[:SAME_DOCUMENT]-(c:Chunk)
            WHERE c.id <> $chunk_id
            RETURN c ORDER BY c.chunk_index ASC
            """,
            chunk_id=chunk_id,
        )
        chunks = [_record_to_dict(r) for r in result]
    driver.close()
    return chunks


def get_related_context(chunk_id: int, neighbor_depth: int = 2) -> dict:
    """Gather expanded context around *chunk_id* by combining traversals.

    Returns a dict with keys:
        - previous: list of preceding chunks
        - next: list of following chunks
        - same_document: list of sibling chunks in the same document

    This combined view gives the language model richer context
    than the single chunk retrieved by vector search.
    """
    return {
        "previous": get_previous_chunks(chunk_id, limit=neighbor_depth),
        "next": get_next_chunks(chunk_id, limit=neighbor_depth),
        "same_document": get_same_document_chunks(chunk_id),
    }


# ── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    test_id = 3
    print(f"Testing graph retrieval around chunk {test_id}:\n")

    ctx = get_related_context(test_id)
    for direction, chunks in ctx.items():
        print(f"  {direction}: {len(chunks)} chunk(s)")
        for c in chunks:
            snippet = c.get("text", "")[:80] + "..."
            print(f"    - chunk {c['id']}: {snippet}")
        print()
