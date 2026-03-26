from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="rag-service")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    return {"status": "ok"}

