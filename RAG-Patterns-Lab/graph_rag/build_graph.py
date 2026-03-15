"""
Build a knowledge graph in Neo4j from the same chunks used in Qdrant.

Creates Chunk nodes with properties and relationships:
    - NEXT / PREVIOUS  — sequential adjacency
    - SAME_DOCUMENT    — all chunks sharing the same doc_id

Usage:
    python -m graph_rag.build_graph
"""

from __future__ import annotations

from neo4j import GraphDatabase

from utils.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, DOCUMENTS_PATH
from rag_qdrant.ingest import prepare_chunks


def _clear_graph(tx) -> None:
    """Remove all Chunk nodes and their relationships (safe for demo reuse)."""
    tx.run("MATCH (c:Chunk) DETACH DELETE c")


def _create_chunk_node(tx, chunk: dict) -> None:
    """Create a single Chunk node."""
    tx.run(
        """
        CREATE (c:Chunk {
            id:          $id,
            text:        $text,
            chunk_index: $chunk_index,
            source:      $source,
            doc_id:      $doc_id
        })
        """,
        id=chunk["id"],
        text=chunk["text"],
        chunk_index=chunk["chunk_index"],
        source=chunk["source"],
        doc_id=chunk["doc_id"],
    )


def _create_sequential_relationships(tx) -> None:
    """Create NEXT and PREVIOUS edges between adjacent chunks."""
    tx.run(
        """
        MATCH (a:Chunk), (b:Chunk)
        WHERE a.chunk_index = b.chunk_index - 1
          AND a.doc_id = b.doc_id
        CREATE (a)-[:NEXT]->(b)
        CREATE (b)-[:PREVIOUS]->(a)
        """
    )


def _create_same_document_relationships(tx) -> None:
    """Create SAME_DOCUMENT edges between all chunks in the same document."""
    tx.run(
        """
        MATCH (a:Chunk), (b:Chunk)
        WHERE a.doc_id = b.doc_id
          AND a.id < b.id
        CREATE (a)-[:SAME_DOCUMENT]->(b)
        """
    )


def build_graph() -> None:
    """Orchestrate the full graph construction pipeline."""

    # Reuse the same chunking logic as the Qdrant pipeline
    print(f"[build_graph] Loading chunks from {DOCUMENTS_PATH} ...")
    records = prepare_chunks(DOCUMENTS_PATH)
    if not records:
        print("[build_graph] No chunks to process.")
        return
    print(f"[build_graph] Prepared {len(records)} chunks.")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    print(f"[build_graph] Connected to Neo4j at {NEO4J_URI}")

    with driver.session() as session:
        # 1. Clear old demo data
        session.execute_write(_clear_graph)
        print("[build_graph] Cleared previous Chunk nodes.")

        # 2. Create nodes
        for chunk in records:
            session.execute_write(_create_chunk_node, chunk)
        print(f"[build_graph] Created {len(records)} Chunk nodes.")

        # 3. Create relationships
        session.execute_write(_create_sequential_relationships)
        session.execute_write(_create_same_document_relationships)

        # 4. Report summary
        node_count = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt").single()["cnt"]
        rel_count = session.run("MATCH (:Chunk)-[r]->(:Chunk) RETURN count(r) AS cnt").single()["cnt"]
        print(f"[build_graph] Graph summary — nodes: {node_count}, relationships: {rel_count}")

    driver.close()
    print("[build_graph] Done.")


if __name__ == "__main__":
    build_graph()
