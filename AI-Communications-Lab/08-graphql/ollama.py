"""Ollama proxy with mock fallback.

Probes Ollama at startup; falls back to deterministic mock generation /
embedding when not reachable, so the demo always works regardless of host
state. Configurable via the OLLAMA_BASE env var (set to
http://host.docker.internal:11434 when the demo runs in Docker).
"""

import asyncio
import json
import os
from typing import AsyncIterator

import httpx

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
CHAT_MODEL = "gemma4:e2b"
EMBED_MODEL = "bge-m3:latest"

_state = {"available": False}


async def probe() -> bool:
    """One-shot connectivity check, run during the FastAPI lifespan startup."""
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            _state["available"] = r.status_code == 200
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        _state["available"] = False
    return _state["available"]


def is_available() -> bool:
    return _state["available"]


async def chat(message: str, model: str = CHAT_MODEL) -> str:
    if _state["available"]:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{OLLAMA_BASE}/api/generate",
                json={"model": model, "prompt": message, "stream": False},
            )
            r.raise_for_status()
            return r.json().get("response", "")
    return f'[mock] You asked: "{message}". This is a mock response.'


async def embed(text: str) -> list[float]:
    if _state["available"]:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{OLLAMA_BASE}/api/embed",
                json={"model": EMBED_MODEL, "input": text},
            )
            r.raise_for_status()
            return r.json()["embeddings"][0]
    return [round(0.01 * i, 4) for i in range(64)]


async def stream_tokens(
    message: str, model: str = CHAT_MODEL
) -> AsyncIterator[tuple[str, bool]]:
    """Yield (token, done) tuples — backs the GraphQL token-stream subscription."""
    if _state["available"]:
        async with httpx.AsyncClient(timeout=120) as c:
            async with c.stream(
                "POST",
                f"{OLLAMA_BASE}/api/generate",
                json={"model": model, "prompt": message, "stream": True},
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token, False
                    if chunk.get("done"):
                        yield "", True
                        return
        return
    # Mock streaming: word-by-word
    words = f"This is a mock streamed response to: {message}".split()
    for w in words:
        yield w + " ", False
        await asyncio.sleep(0.08)
    yield "", True
