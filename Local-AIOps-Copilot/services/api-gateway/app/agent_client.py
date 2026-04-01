"""gRPC client for communicating with the agent-service."""

from __future__ import annotations

from typing import AsyncIterator

import grpc

from shared.logging import get_logger

logger = get_logger(__name__)


class AgentGRPCClient:
    """Client that connects to agent-service over gRPC.

    Falls back to direct HTTP calls if gRPC is unavailable.
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        self._host = host
        self._port = port
        self._channel: grpc.aio.Channel | None = None
        self._stub = None

    async def _ensure_channel(self):
        if self._channel is None:
            target = f"{self._host}:{self._port}"
            self._channel = grpc.aio.insecure_channel(target)
            try:
                # Dynamic import of generated stubs
                from shared.grpc_common import agent_pb2_grpc

                self._stub = agent_pb2_grpc.AgentServiceStub(self._channel)
            except ImportError:
                logger.warning("grpc_stubs_not_found", msg="Using fallback mode")
                self._stub = None

    async def health_check(self) -> bool:
        try:
            await self._ensure_channel()
            if self._stub is None:
                return False
            from shared.grpc_common import agent_pb2

            resp = await self._stub.HealthCheck(agent_pb2.HealthRequest())
            return resp.healthy
        except Exception as e:
            logger.debug("agent_health_check_failed", error=str(e))
            return False

    async def chat(
        self,
        session_id: str,
        message: str,
        use_tools: bool = True,
        use_rag: bool = True,
    ) -> dict:
        try:
            await self._ensure_channel()
            if self._stub is None:
                return self._fallback_response(message)
            from shared.grpc_common import agent_pb2

            request = agent_pb2.ChatRequest(
                session_id=session_id,
                user_message=message,
                use_tools=use_tools,
                use_rag=use_rag,
            )
            response = await self._stub.Chat(request)
            return {
                "content": response.content,
                "sources": list(response.sources),
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "result": tc.result,
                    }
                    for tc in response.tool_calls
                ],
            }
        except Exception as e:
            logger.error("agent_chat_error", error=str(e))
            return self._fallback_response(message)

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        use_tools: bool = True,
        use_rag: bool = True,
    ) -> AsyncIterator[str]:
        try:
            await self._ensure_channel()
            if self._stub is None:
                yield self._fallback_response(message)["content"]
                return
            from shared.grpc_common import agent_pb2

            request = agent_pb2.ChatRequest(
                session_id=session_id,
                user_message=message,
                use_tools=use_tools,
                use_rag=use_rag,
            )
            async for token in self._stub.StreamChat(request):
                yield token.token
        except Exception as e:
            logger.error("agent_stream_error", error=str(e))
            yield f"Error: {e}"

    def _fallback_response(self, message: str) -> dict:
        return {
            "content": (
                f"[Fallback] Received: {message}. "
                "Agent service is not connected via gRPC."
            ),
            "sources": [],
            "tool_calls": [],
        }

    async def close(self):
        if self._channel:
            await self._channel.close()
            self._channel = None
