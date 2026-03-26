from __future__ import annotations

from pathlib import Path

from rag_service_app.service import RagEngine


def test_rag_engine_fallback_retrieval(tmp_path: Path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    doc = knowledge / "starship.md"
    doc.write_text("Bridge checklist: stabilize propulsion before navigation changes.", encoding="utf-8")

    engine = RagEngine(
        knowledge_dir=str(knowledge),
        qdrant_url="http://localhost:6333",
        ollama_base_url="http://localhost:11434",
        embed_model="bge-m3:latest",
    )
    context, citations = engine.retrieve("propulsion", top_k=1)

    assert "propulsion" in context.lower()
    assert citations[0]["source"] == "starship.md"
