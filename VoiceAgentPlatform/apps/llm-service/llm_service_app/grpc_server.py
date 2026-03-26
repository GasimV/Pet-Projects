from __future__ import annotations

import grpc

from llm_service_app.providers import BaseProvider
from llm_service_app.tool_planner import ToolPlanner
from voice_platform import common_pb2, llm_pb2, llm_pb2_grpc


class LanguageModelService(llm_pb2_grpc.LanguageModelServicer):
    def __init__(self, provider: BaseProvider, planner: ToolPlanner) -> None:
        self._provider = provider
        self._planner = planner

    async def StreamGenerate(
        self, request: llm_pb2.GenerateRequest, context: grpc.aio.ServicerContext
    ):
        messages = [{"role": item.role, "content": item.content} for item in request.messages]
        latest_user = next((item.content for item in reversed(request.messages) if item.role == "user"), "")

        if request.enable_tools:
            tool_intent = await self._planner.plan(latest_user)
            if tool_intent:
                yield llm_pb2.GenerateChunk(
                    meta=request.meta,
                    token="",
                    is_final=False,
                    tool_intent=llm_pb2.ToolIntent(**tool_intent),
                )
                yield llm_pb2.GenerateChunk(meta=request.meta, token="", is_final=True)
                return

        async for piece in self._provider.stream(messages, request.system_prompt, request.context):
            yield llm_pb2.GenerateChunk(meta=request.meta, token=piece.token, is_final=piece.is_final)

    async def Health(self, request: common_pb2.Empty, context: grpc.aio.ServicerContext):
        return common_pb2.HealthReply(status="ok")

