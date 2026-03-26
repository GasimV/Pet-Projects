from __future__ import annotations

import json

import grpc

from tool_service_app.tools import TOOL_REGISTRY
from voice_platform import common_pb2, tool_pb2, tool_pb2_grpc


class ToolRuntimeService(tool_pb2_grpc.ToolRuntimeServicer):
    async def Execute(
        self, request: tool_pb2.ToolRequest, context: grpc.aio.ServicerContext
    ) -> tool_pb2.ToolReply:
        handler = TOOL_REGISTRY.get(request.name)
        if handler is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"Unknown tool: {request.name}")
        args = json.loads(request.arguments_json or "{}")
        result = handler(**args)
        return tool_pb2.ToolReply(meta=request.meta, output_json=json.dumps(result), retriable=False)

    async def Health(
        self, request: common_pb2.Empty, context: grpc.aio.ServicerContext
    ) -> common_pb2.HealthReply:
        return common_pb2.HealthReply(status="ok")

