"""
GraphRAG query pipeline.

Demonstrates the full GraphRAG workflow:
  1. Semantic search in Qdrant → retrieve the most relevant chunk
  2. Use the chunk's ID to traverse Neo4j for expanded context
  3. Display both the primary hit and the graph-expanded context

Usage:
    python -m graph_rag.query_graph_rag
"""

from __future__ import annotations

from rag_qdrant.query import query_qdrant
from graph_rag.graph_retrieval import get_related_context


# ── Configuration ──────────────────────────────────────────────────
SAMPLE_QUERY = "How does GraphRAG improve retrieval compared to standard RAG?"


def query_graph_rag(query_text: str, top_k: int = 1) -> None:
    """Execute the GraphRAG pipeline and print results."""

    # ── Step 1: Semantic search via Qdrant ─────────────────────────
    print("=" * 70)
    print("  GRAPH-RAG QUERY")
    print("=" * 70)
    print(f"\n  Query: {query_text}\n")

    print("── Step 1: Qdrant semantic search ──")
    hits = query_qdrant(query_text, top_k=top_k)

    if not hits:
        print("  No results from Qdrant. Is data ingested?")
        return

    primary = hits[0]
    primary_id = primary["id"]
    print(f"  Top hit   : chunk {primary_id}  (score: {primary['score']:.4f})")
    text_preview = primary["text"][:200] + " ..." if len(primary["text"]) > 200 else primary["text"]
    print(f"  Text      : {text_preview}")
    print(f"  Prev/Next : {primary.get('previous_chunk_id')} / {primary.get('next_chunk_id')}")

    # ── Step 2: Graph-based context expansion via Neo4j ────────────
    print("\n── Step 2: Neo4j graph expansion ──")
    context = get_related_context(primary_id, neighbor_depth=2)

    for direction in ("previous", "next"):
        chunks = context[direction]
        print(f"\n  {direction.upper()} chunks ({len(chunks)}):")
        if not chunks:
            print("    (none)")
        for c in chunks:
            snippet = c["text"][:120] + " ..." if len(c["text"]) > 120 else c["text"]
            print(f"    chunk {c['id']}: {snippet}")

    # Show count of same-document siblings (can be many)
    siblings = context["same_document"]
    print(f"\n  SAME_DOCUMENT siblings: {len(siblings)} chunk(s)")

    # ── Step 3: Combined context summary ──────────────────────────
    all_context_ids = (
        [primary_id]
        + [c["id"] for c in context["previous"]]
        + [c["id"] for c in context["next"]]
    )
    print(f"\n── Combined context chunk IDs: {sorted(set(all_context_ids))}")

    # In a real system, you would concatenate these chunk texts and
    # send them to an LLM as grounding context for the answer.
    print("\n  In a production system, the texts from these chunks would be")
    print("  concatenated and sent to an LLM as grounding context.")
    print("=" * 70)


if __name__ == "__main__":
    query_graph_rag(SAMPLE_QUERY)
