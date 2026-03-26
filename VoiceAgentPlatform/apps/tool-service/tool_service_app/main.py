from __future__ import annotations

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-observability",
    ROOT / "libs" / "proto" / "generated",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

import grpc
import uvicorn

from shared_config.settings import get_settings
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing
from tool_service_app.grpc_server import ToolRuntimeService
from tool_service_app.http_app import app
from voice_platform import tool_pb2_grpc


async def serve_grpc() -> None:
    settings = get_settings()
    server = grpc.aio.server()
    tool_pb2_grpc.add_ToolRuntimeServicer_to_server(ToolRuntimeService(), server)
    server.add_insecure_port("[::]:50055")
    await server.start()
    await server.wait_for_termination()


async def serve_http() -> None:
    settings = get_settings()
    config = uvicorn.Config(app, host="0.0.0.0", port=8095, log_level=settings.log_level.lower())
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing("tool-service", settings.otel_exporter_otlp_endpoint)
    await asyncio.gather(serve_http(), serve_grpc())


if __name__ == "__main__":
    asyncio.run(main())
