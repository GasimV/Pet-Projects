"""FactoryPulse API — Unified serving layer for IoT data platform."""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from routers import alerts, devices, features, search, telemetry

app = FastAPI(
    title="FactoryPulse API",
    description=(
        "Unified serving layer exposing data from ClickHouse (warehouse), "
        "Redis/Feast (features), Qdrant (vectors), and MLflow."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(telemetry.router)
app.include_router(alerts.router)
app.include_router(devices.router)
app.include_router(search.router)
app.include_router(features.router)

# ---------------------------------------------------------------------------
# Prometheus instrumentation
# ---------------------------------------------------------------------------
Instrumentator().instrument(app).expose(app)


# ---------------------------------------------------------------------------
# Root & health
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint returning service metadata."""
    return {"service": "FactoryPulse API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
