"""gRPC server for the agent-service."""

from __future__ import annotations

import asyncio
import sys
from concurrent import futures
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import grpc

from shared.config import get_settings
from shared.llm_backend import create_llm_client
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics
from app.graph import AgentGraph
from app.memory import ConversationMemory, InMemoryConversationMemory

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "agent-service")
logger = get_logger(__name__)
metrics = setup_metrics("agent-service")


class AgentServicer:
    """gRPC servicer that wraps the LangGraph agent."""

    def __init__(self):
        self.llm_client = create_llm_client()
        self.agent = AgentGraph(llm_client=self.llm_client)
        try:
            self.memory = ConversationMemory(settings.redis_url)
        except Exception:
            logger.warning("redis_unavailable", msg="Using in-memory fallback")
            self.memory = InMemoryConversationMemory()

    async def Chat(self, request, context):
        try:
            from shared.grpc_common import agent_pb2

            history = await self.memory.get_history(request.session_id)
            result = await self.agent.run(
                session_id=request.session_id,
                message=request.user_message,
                history=history,
                use_tools=request.use_tools,
                use_rag=request.use_rag,
            )
            await self.memory.add_message(request.session_id, "user", request.user_message)
            await self.memory.add_message(request.session_id, "assistant", result["content"])

            metrics.llm_request_count.labels(
                self.llm_client.backend_name, self.llm_client.model_name
            ).inc()

            return agent_pb2.ChatResponse(
                session_id=request.session_id,
                content=result["content"],
                tool_calls=[
                    agent_pb2.ToolCall(
                        tool_name=tc.get("tool_name", ""),
                        arguments=tc.get("arguments", ""),
                        result=tc.get("result", ""),
                    )
                    for tc in result.get("tool_calls", [])
                ],
                sources=result.get("sources", []),
            )
        except Exception as e:
            logger.error("chat_error", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            from shared.grpc_common import agent_pb2

            return agent_pb2.ChatResponse(
                session_id=request.session_id,
                content=f"Error: {e}",
            )

    async def StreamChat(self, request, context):
        try:
            from shared.grpc_common import agent_pb2

            history = await self.memory.get_history(request.session_id)
            async for token in self.agent.run_stream(
                session_id=request.session_id,
                message=request.user_message,
                history=history,
                use_tools=request.use_tools,
                use_rag=request.use_rag,
            ):
                yield agent_pb2.ChatToken(token=token, is_final=False)
            yield agent_pb2.ChatToken(token="", is_final=True)
        except Exception as e:
            logger.error("stream_chat_error", error=str(e))
            from shared.grpc_common import agent_pb2

            yield agent_pb2.ChatToken(token=f"Error: {e}", is_final=True)

    async def HealthCheck(self, request, context):
        from shared.grpc_common import agent_pb2

        healthy = await self.llm_client.health_check()
        return agent_pb2.HealthResponse(
            healthy=healthy,
            backend=self.llm_client.backend_name,
            model=self.llm_client.model_name,
        )


async def serve():
    server = grpc.aio.server()
    servicer = AgentServicer()

    try:
        from shared.grpc_common import agent_pb2_grpc

        agent_pb2_grpc.add_AgentServiceServicer_to_server(servicer, server)
    except ImportError:
        logger.error(
            "grpc_stubs_missing",
            msg="Run 'python -m grpc_tools.protoc' to generate stubs",
        )
        return

    port = settings.agent_service_port
    server.add_insecure_port(f"[::]:{port}")
    logger.info("agent_service_starting", port=port, backend=settings.llm_backend.value)
    metrics.info.info({
        "version": "0.1.0",
        "backend": settings.llm_backend.value,
        "environment": settings.environment.value,
    })
    await server.start()
    logger.info("agent_service_started", port=port)
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
