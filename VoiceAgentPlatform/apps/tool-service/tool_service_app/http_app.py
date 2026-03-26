from __future__ import annotations

from fastapi import FastAPI

from tool_service_app.tools import list_capabilities

app = FastAPI(title="tool-service")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
async def tools() -> dict[str, object]:
    return list_capabilities()

