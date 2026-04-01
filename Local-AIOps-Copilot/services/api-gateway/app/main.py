"""API Gateway — FastAPI entrypoint with SSE, WebSocket, and REST endpoints."""

from __future__ import annotations

import json
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is on sys.path for shared module imports
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from sse_starlette.sse import EventSourceResponse

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics
from app.models import ChatRequest, ChatResponse, HealthResponse
from app.agent_client import AgentGRPCClient
from app.ws_manager import ConnectionManager

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "api-gateway")
logger = get_logger(__name__)
metrics = setup_metrics("api-gateway")

agent_client: AgentGRPCClient | None = None
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_client
    agent_client = AgentGRPCClient(
        host="localhost", port=settings.agent_service_port
    )
    logger.info("api_gateway_started", port=settings.api_gateway_port)
    metrics.info.info({"version": "0.1.0", "environment": settings.environment.value})
    yield
    if agent_client:
        await agent_client.close()
    logger.info("api_gateway_stopped")


app = FastAPI(
    title="Local-AIOps-Copilot API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    backend_healthy = False
    if agent_client:
        backend_healthy = await agent_client.health_check()
    return HealthResponse(
        status="healthy" if backend_healthy else "degraded",
        agent_service=backend_healthy,
        environment=settings.environment.value,
        llm_backend=settings.llm_backend.value,
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat endpoint — returns full response."""
    session_id = request.session_id or str(uuid.uuid4())
    metrics.request_count.labels("POST", "/api/v1/chat", "200").inc()

    with metrics.request_latency.labels("POST", "/api/v1/chat").time():
        if agent_client:
            result = await agent_client.chat(
                session_id=session_id,
                message=request.message,
                use_tools=request.use_tools,
                use_rag=request.use_rag,
            )
        else:
            result = {
                "content": "Agent service not available",
                "sources": [],
                "tool_calls": [],
            }

    return ChatResponse(
        session_id=session_id,
        content=result.get("content", ""),
        sources=result.get("sources", []),
        tool_calls=result.get("tool_calls", []),
    )


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint — streams tokens as Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())
    metrics.request_count.labels("POST", "/api/v1/chat/stream", "200").inc()

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"session_id": session_id})}
        try:
            if agent_client:
                async for token in agent_client.stream_chat(
                    session_id=session_id,
                    message=request.message,
                    use_tools=request.use_tools,
                    use_rag=request.use_rag,
                ):
                    yield {"event": "token", "data": json.dumps({"token": token})}
            else:
                yield {
                    "event": "token",
                    "data": json.dumps({"token": "Agent service not available"}),
                }
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
        yield {"event": "done", "data": json.dumps({"session_id": session_id})}

    return EventSourceResponse(event_generator())


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for bidirectional live chat."""
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            use_tools = data.get("use_tools", True)
            use_rag = data.get("use_rag", True)

            await websocket.send_json({"event": "thinking", "session_id": session_id})

            if agent_client:
                async for token in agent_client.stream_chat(
                    session_id=session_id,
                    message=message,
                    use_tools=use_tools,
                    use_rag=use_rag,
                ):
                    await websocket.send_json(
                        {"event": "token", "token": token, "session_id": session_id}
                    )
            else:
                await websocket.send_json(
                    {
                        "event": "token",
                        "token": "Agent service not available",
                        "session_id": session_id,
                    }
                )

            await websocket.send_json({"event": "done", "session_id": session_id})

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
        logger.info("ws_disconnected", session_id=session_id)


@app.get("/api/v1/backend/info")
async def backend_info():
    """Return current LLM backend configuration."""
    return {
        "backend": settings.llm_backend.value,
        "environment": settings.environment.value,
        "is_gpu_mode": settings.is_gpu_mode,
    }
