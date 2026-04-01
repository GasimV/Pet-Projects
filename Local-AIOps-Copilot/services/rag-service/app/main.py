"""RAG Service — document ingestion and retrieval with Qdrant vector store."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import grpc

from shared.config import get_settings
from shared.llm_backend import create_llm_client
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics
from app.vectorstore import VectorStore, InMemoryVectorStore

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "rag-service")
logger = get_logger(__name__)
metrics = setup_metrics("rag-service")


class RAGServicer:
    """gRPC servicer for RAG operations."""

    def __init__(self):
        self.llm_client = create_llm_client()
        try:
            from qdrant_client import QdrantClient

            qdrant = QdrantClient(url=settings.qdrant_url)
            self.store = VectorStore(
                qdrant_client=qdrant,
                embedding_client=self.llm_client,
                collection_name="copilot_docs",
            )
            logger.info("qdrant_connected", url=settings.qdrant_url)
        except Exception as e:
            logger.warning("qdrant_unavailable", error=str(e), msg="Using in-memory fallback")
            self.store = InMemoryVectorStore(embedding_client=self.llm_client)

    async def Ingest(self, request, context):
        from shared.grpc_common import rag_pb2

        try:
            chunks_created = await self.store.ingest(
                document_id=request.document_id,
                content=request.content,
                metadata=dict(request.metadata),
                collection=request.collection or "copilot_docs",
            )
            return rag_pb2.IngestResponse(
                document_id=request.document_id,
                chunks_created=chunks_created,
                success=True,
            )
        except Exception as e:
            logger.error("ingest_error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return rag_pb2.IngestResponse(
                document_id=request.document_id, chunks_created=0, success=False
            )

    async def Retrieve(self, request, context):
        from shared.grpc_common import rag_pb2

        try:
            results = await self.store.retrieve(
                query=request.query,
                top_k=request.top_k or 5,
                collection=request.collection or "copilot_docs",
                score_threshold=request.score_threshold or 0.0,
            )
            chunks = [
                rag_pb2.RetrievedChunk(
                    document_id=r["document_id"],
                    content=r["content"],
                    score=r["score"],
                    metadata=r.get("metadata", {}),
                )
                for r in results
            ]
            return rag_pb2.RetrieveResponse(chunks=chunks)
        except Exception as e:
            logger.error("retrieve_error", error=str(e))
            return rag_pb2.RetrieveResponse(chunks=[])

    async def HealthCheck(self, request, context):
        from shared.grpc_common import rag_pb2

        healthy = await self.store.health_check()
        return rag_pb2.HealthResponse(healthy=healthy, status="ok" if healthy else "degraded")


async def serve():
    server = grpc.aio.server()
    servicer = RAGServicer()

    try:
        from shared.grpc_common import rag_pb2_grpc

        rag_pb2_grpc.add_RAGServiceServicer_to_server(servicer, server)
    except ImportError:
        logger.error("grpc_stubs_missing")
        return

    port = settings.rag_service_port
    server.add_insecure_port(f"[::]:{port}")
    logger.info("rag_service_starting", port=port)
    await server.start()
    logger.info("rag_service_started", port=port)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
