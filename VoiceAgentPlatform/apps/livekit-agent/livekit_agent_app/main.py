from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-observability",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

from fastapi import FastAPI

from shared_config.settings import get_settings
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing

settings = get_settings()
configure_logging(settings.log_level)
configure_tracing("livekit-agent", settings.otel_exporter_otlp_endpoint)

app = FastAPI(title="livekit-agent")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/capabilities")
async def capabilities() -> dict[str, object]:
    return {
        "status": "stubbed",
        "notes": [
            "Room token wiring is enabled in the gateway.",
            "Browser-to-orchestrator PCM over WebSocket is the verified MVP path in this repo.",
            "This service is the production insertion point for full LiveKit participant bridging.",
        ],
    }
