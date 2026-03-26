from __future__ import annotations

import asyncio
import pathlib
import sys

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
import uvicorn
from temporalio.client import Client

from session_orchestrator_app.clients import ServiceClients
from session_orchestrator_app.http_app import app
from session_orchestrator_app.service import RealtimeSessionService
from session_orchestrator_app.temporal_client import DurableWorkflowLauncher
from shared_config.settings import get_settings
from shared_events.bus import EventPublisher
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing
from voice_platform import session_pb2_grpc


async def serve_grpc(publisher: EventPublisher | None, workflow_launcher: DurableWorkflowLauncher) -> None:
    settings = get_settings()
    clients = ServiceClients()
    server = grpc.aio.server()
    session_pb2_grpc.add_RealtimeSessionOrchestratorServicer_to_server(
        RealtimeSessionService(
            clients, publisher, settings.default_domain_pack, workflow_launcher
        ),
        server,
    )
    server.add_insecure_port(f"[::]:{settings.orchestrator_grpc_port}")
    await server.start()
    await server.wait_for_termination()


async def serve_http() -> None:
    settings = get_settings()
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.orchestrator_http_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing("session-orchestrator", settings.otel_exporter_otlp_endpoint)
    redis_client = None
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=False)
        await redis_client.ping()
    except Exception:
        redis_client = None
    publisher = EventPublisher(redis_client, settings.session_event_channel)
    temporal_client = None
    try:
        temporal_client = await Client.connect(
            settings.temporal_target, namespace=settings.temporal_namespace
        )
    except Exception:
        temporal_client = None
    workflow_launcher = DurableWorkflowLauncher(temporal_client, settings.temporal_task_queue)
    await asyncio.gather(serve_http(), serve_grpc(publisher, workflow_launcher))


if __name__ == "__main__":
    asyncio.run(main())
