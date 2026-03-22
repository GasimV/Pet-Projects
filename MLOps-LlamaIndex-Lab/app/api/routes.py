"""
FastAPI route definitions for the RAG application.

Endpoints:
    GET  /health          — liveness check
    GET  /api/status      — index & provider status
    POST /api/upload      — upload one or more documents
    GET  /api/documents   — list uploaded documents
    POST /api/ingest      — run the ingestion pipeline
    POST /api/query       — ask a question
"""

from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.services import document_service, rag_service

logger = get_logger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list


class IngestResponse(BaseModel):
    status: str
    documents_ingested: int
    collection: str


# ── Health / Status ──────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Simple liveness probe."""
    return {"status": "ok"}


@router.get("/api/status")
async def status():
    """Show index stats and current provider configuration."""
    index_info = rag_service.get_index_status()
    return {
        **index_info,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }


# ── Document Management ─────────────────────────────────────────────────────

@router.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload one or more documents."""
    saved = []
    errors = []
    for f in files:
        try:
            path = await document_service.save_uploaded_file(f)
            saved.append(path.name)
        except ValueError as exc:
            errors.append({"file": f.filename, "error": str(exc)})
    return {"saved": saved, "errors": errors}


@router.get("/api/documents")
async def list_documents():
    """List all uploaded documents."""
    return {"documents": document_service.list_uploaded_files()}


# ── Ingestion ────────────────────────────────────────────────────────────────

@router.post("/api/ingest", response_model=IngestResponse)
async def ingest():
    """Parse, chunk, embed, and store all uploaded documents."""
    try:
        result = rag_service.run_ingestion()
        return result
    except Exception as exc:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Query ────────────────────────────────────────────────────────────────────

@router.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a question against the indexed knowledge base."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    try:
        result = rag_service.query_knowledge_base(req.question)
        return result
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc))
