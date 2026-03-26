from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import sys
import uuid
from contextlib import asynccontextmanager

ROOT = pathlib.Path(__file__).resolve().parents[3]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-events",
    ROOT / "libs" / "shared-observability",
    ROOT / "libs" / "proto" / "generated",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

import grpc
import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from gateway_app.livekit_utils import issue_token
from shared_config.settings import get_settings
from shared_events.bus import EventSubscriber
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing
from voice_platform import common_pb2, session_pb2, session_pb2_grpc

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    configure_tracing("gateway", settings.otel_exporter_otlp_endpoint)
    yield


app = FastAPI(title="gateway", lifespan=lifespan)
static_root = ROOT / "apps" / "web-ui" / "src"
app.mount("/static", StaticFiles(directory=static_root), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_root / "index.html")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
async def config() -> dict[str, object]:
    return {
        "runtime_profile": settings.runtime_profile,
        "ws_path": "/ws/session",
        "default_domain": settings.default_domain_pack,
        "livekit_url": settings.livekit_url,
        "livekit_enabled": True,
    }


@app.get("/api/livekit/token")
async def livekit_token(room: str = "voice-room", identity: str | None = None):
    token = issue_token(
        settings.livekit_api_key,
        settings.livekit_api_secret,
        room=room,
        identity=identity or f"browser-{uuid.uuid4().hex[:8]}",
    )
    if token is None:
        return JSONResponse({"token": None, "reason": "livekit-api package unavailable"}, status_code=503)
    return {"token": token}


@app.get("/sse/{session_id}")
async def sse(session_id: str):
    redis_client = None
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
    except Exception:
        redis_client = None

    async def stream():
        if redis_client is None:
            yield "event: message\ndata: " + json.dumps({"warning": "redis unavailable"}) + "\n\n"
            return
        subscriber = EventSubscriber(redis_client, settings.session_event_channel)
        async for event in subscriber.iter_events():
            if event.session_id != session_id:
                continue
            yield f"event: {event.event_type}\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.websocket("/ws/session")
async def websocket_session(websocket: WebSocket) -> None:
    await websocket.accept()
    channel = grpc.aio.insecure_channel(
        f"{settings.orchestrator_grpc_host}:{settings.orchestrator_grpc_port}"
    )
    stub = session_pb2_grpc.RealtimeSessionOrchestratorStub(channel)
    outgoing: asyncio.Queue[session_pb2.SessionMessage | None] = asyncio.Queue()

    async def request_stream():
        while True:
            message = await outgoing.get()
            if message is None:
                return
            yield message

    async def receive_browser() -> None:
        try:
            while True:
                payload = await websocket.receive_json()
                event_type = payload.get("type")
                meta = common_pb2.RequestMeta(
                    session_id=payload.get("session_id", ""),
                    turn_id=payload.get("turn_id", "turn-0"),
                    request_id=payload.get("request_id", str(uuid.uuid4())),
                    domain=payload.get("domain", settings.default_domain_pack),
                )
                if event_type == "audio":
                    await outgoing.put(
                        session_pb2.SessionMessage(
                            audio=session_pb2.AudioFrame(
                                meta=meta,
                                pcm=base64.b64decode(payload["audio_b64"]),
                                sample_rate=payload.get("sample_rate", 16000),
                                channels=1,
                                end_of_turn=payload.get("end_of_turn", False),
                                sequence_id=payload.get("sequence_id", 0),
                            )
                        )
                    )
                else:
                    await outgoing.put(
                        session_pb2.SessionMessage(
                            control=session_pb2.ClientControl(
                                meta=meta,
                                command=payload.get("command", event_type or "unknown"),
                                value=payload.get("value", ""),
                            )
                        )
                    )
        except WebSocketDisconnect:
            await outgoing.put(None)

    receiver = asyncio.create_task(receive_browser())
    try:
        async for message in stub.Connect(request_stream()):
            if not message.HasField("event"):
                continue
            event = message.event
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            try:
                await websocket.send_json(
                    {
                        "type": event.event_type,
                        "text": event.text,
                        "is_final": event.is_final,
                        "sequence_id": event.sequence_id,
                        "mime_type": event.mime_type,
                        "audio_b64": base64.b64encode(event.audio).decode("utf-8") if event.audio else None,
                        "payload": json.loads(event.json_payload or "{}"),
                        "session_id": event.meta.session_id,
                        "turn_id": event.meta.turn_id,
                    }
                )
            except (RuntimeError, WebSocketDisconnect):
                break
    except grpc.aio.AioRpcError as exc:
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "text": "",
                        "payload": {"stage": "gateway", "error": exc.details() or str(exc)},
                        "is_final": True,
                        "sequence_id": 0,
                        "mime_type": "",
                        "audio_b64": None,
                        "session_id": "",
                        "turn_id": "",
                    }
                )
            except (RuntimeError, WebSocketDisconnect):
                pass
    finally:
        await outgoing.put(None)
        receiver.cancel()
        try:
            await receiver
        except asyncio.CancelledError:
            pass
        await channel.close()
