"""
AI Inference Gateway — HTTP/HTTPS Demo

A minimal REST API that proxies requests to an AI model (Ollama)
with fallback to mock responses. Demonstrates the request/response
pattern that underpins most AI APIs.
"""

import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_BASE = "http://localhost:11434"
CHAT_MODEL = "gemma3:1b"

# ---------------------------------------------------------------------------
# Ollama health probe (runs once at startup)
# ---------------------------------------------------------------------------
ollama_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ollama_available
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            ollama_available = r.status_code == 200
    except httpx.ConnectError:
        ollama_available = False
    status = "connected" if ollama_available else "mock mode"
    print(f"[gateway] Ollama {status}")
    yield


app = FastAPI(title="AI Inference Gateway", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    model: str = CHAT_MODEL


class ChatResponse(BaseModel):
    reply: str
    model: str
    latency_ms: float
    source: str  # "ollama" or "mock"


class EmbedRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8192)


class EmbedResponse(BaseModel):
    embedding: list[float]
    dimensions: int
    latency_ms: float
    source: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ollama": "connected" if ollama_available else "unavailable",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_api_key: str | None = Header(None)):
    """Send a prompt and receive a complete response (non-streaming)."""
    # Auth placeholder — in production, validate x_api_key here
    start = time.perf_counter()

    if ollama_available:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    f"{OLLAMA_BASE}/api/generate",
                    json={"model": req.model, "prompt": req.message, "stream": False},
                )
                r.raise_for_status()
                data = r.json()
                reply = data.get("response", "")
                source = "ollama"
        except (httpx.HTTPError, KeyError) as exc:
            raise HTTPException(502, f"Ollama error: {exc}")
    else:
        reply = f'[mock] Echo: "{req.message}"'
        source = "mock"

    elapsed = (time.perf_counter() - start) * 1000
    return ChatResponse(
        reply=reply, model=req.model, latency_ms=round(elapsed, 2), source=source
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest, x_api_key: str | None = Header(None)):
    """Generate an embedding vector for the given text."""
    start = time.perf_counter()

    if ollama_available:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{OLLAMA_BASE}/api/embed",
                    json={"model": "bge-m3:latest", "input": req.text},
                )
                r.raise_for_status()
                data = r.json()
                vec = data["embeddings"][0]
                source = "ollama"
        except (httpx.HTTPError, KeyError) as exc:
            raise HTTPException(502, f"Ollama error: {exc}")
    else:
        vec = [0.01 * i for i in range(64)]
        source = "mock"

    elapsed = (time.perf_counter() - start) * 1000
    return EmbedResponse(
        embedding=vec,
        dimensions=len(vec),
        latency_ms=round(elapsed, 2),
        source=source,
    )
