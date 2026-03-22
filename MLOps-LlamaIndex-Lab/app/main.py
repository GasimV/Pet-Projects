"""
MLOps-LlamaIndex-Lab — FastAPI Application Entry Point.

Starts the server, mounts static files, and wires up the API routes
plus a simple HTML frontend.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown logic."""
    logger.info(
        "Starting MLOps-LlamaIndex-Lab  provider=%s  model=%s  qdrant=%s:%s",
        settings.llm_provider,
        settings.llm_model,
        settings.qdrant_host,
        settings.qdrant_port,
    )
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    yield

# ── Application factory ─────────────────────────────────────────────────────

app = FastAPI(
    title="MLOps LlamaIndex Lab",
    description="Local RAG web app powered by LlamaIndex, FastAPI, and Qdrant.",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static assets (CSS / JS)
UI_DIR = Path(__file__).parent / "ui"
app.mount("/static", StaticFiles(directory=UI_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(UI_DIR / "templates"))

# Include API routes
app.include_router(router)


# ── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page frontend."""
    return templates.TemplateResponse(request, "index.html")


# ── Run with: python -m app.main ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level,
    )
