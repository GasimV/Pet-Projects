from __future__ import annotations

import grpc

from rag_service_app.service import RagEngine
from voice_platform import common_pb2, rag_pb2, rag_pb2_grpc


class RetrievalAugmentationService(rag_pb2_grpc.RetrievalAugmentationServicer):
    def __init__(self, engine: RagEngine) -> None:
        self._engine = engine

    async def Retrieve(self, request: rag_pb2.RagRequest, context: grpc.aio.ServicerContext):
        assembled_context, citations = self._engine.retrieve(request.query, top_k=request.top_k or 3)
        return rag_pb2.RagReply(
            meta=request.meta,
            assembled_context=assembled_context,
            citations=[rag_pb2.Citation(**item) for item in citations],
        )

    async def Health(self, request: common_pb2.Empty, context: grpc.aio.ServicerContext):
        return common_pb2.HealthReply(status="ok")

