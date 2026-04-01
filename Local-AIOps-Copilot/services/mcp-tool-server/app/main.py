"""MCP Tool Server — exposes operational tools via Model Context Protocol."""

from __future__ import annotations

import datetime
import platform
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import httpx
import psutil
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "mcp-tool-server")
logger = get_logger(__name__)
metrics = setup_metrics("mcp-tool-server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("mcp_tool_server_started", port=settings.mcp_server_port)
    yield
    logger.info("mcp_tool_server_stopped")


app = FastAPI(title="MCP Tool Server", version="0.1.0", lifespan=lifespan)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ── Tool definitions (MCP-compatible) ──


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    tool_name: str
    result: str
    success: bool = True


TOOLS: dict[str, ToolDefinition] = {}


def register_tool(name: str, description: str, parameters: dict | None = None):
    TOOLS[name] = ToolDefinition(
        name=name, description=description, parameters=parameters or {}
    )


# ── Built-in tools ──

register_tool(
    "get_current_time",
    "Get the current date and time",
    {"type": "object", "properties": {}},
)

register_tool(
    "get_system_info",
    "Get system information (CPU, memory, disk usage)",
    {"type": "object", "properties": {}},
)

register_tool(
    "check_service_health",
    "Check health of a service by URL",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Health endpoint URL"},
        },
        "required": ["url"],
    },
)

register_tool(
    "get_prometheus_metric",
    "Query a Prometheus metric",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "PromQL query"},
        },
        "required": ["query"],
    },
)

register_tool(
    "list_docker_containers",
    "List running Docker containers",
    {"type": "object", "properties": {}},
)


# ── Tool implementations ──


async def exec_get_current_time(**kwargs) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.isoformat()


async def exec_get_system_info(**kwargs) -> str:
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/") if platform.system() != "Windows" else psutil.disk_usage("C:\\")
    return (
        f"CPU: {cpu_pct}%, "
        f"Memory: {mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB), "
        f"Disk: {disk.percent}% ({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB), "
        f"Platform: {platform.system()} {platform.release()}"
    )


async def exec_check_service_health(url: str = "", **kwargs) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            return f"Status: {resp.status_code}, Body: {resp.text[:500]}"
    except Exception as e:
        return f"Error reaching {url}: {e}"


async def exec_get_prometheus_metric(query: str = "", **kwargs) -> str:
    prom_url = f"http://localhost:{settings.prometheus_port}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{prom_url}/api/v1/query", params={"query": query})
            if resp.status_code == 200:
                data = resp.json()
                return str(data.get("data", {}).get("result", []))
            return f"Prometheus returned {resp.status_code}"
    except Exception as e:
        return f"Prometheus query failed: {e}"


async def exec_list_docker_containers(**kwargs) -> str:
    import asyncio

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode()
        return f"Docker error: {stderr.decode()}"
    except Exception as e:
        return f"Docker not available: {e}"


TOOL_EXECUTORS = {
    "get_current_time": exec_get_current_time,
    "get_system_info": exec_get_system_info,
    "check_service_health": exec_check_service_health,
    "get_prometheus_metric": exec_get_prometheus_metric,
    "list_docker_containers": exec_list_docker_containers,
}


# ── API endpoints ──


@app.get("/tools")
async def list_tools() -> list[ToolDefinition]:
    """List all available tools (MCP tool discovery)."""
    return list(TOOLS.values())


@app.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Execute a tool by name (MCP tool invocation)."""
    executor = TOOL_EXECUTORS.get(request.tool_name)
    if not executor:
        return ToolCallResponse(
            tool_name=request.tool_name,
            result=f"Unknown tool: {request.tool_name}",
            success=False,
        )
    try:
        result = await executor(**request.arguments)
        metrics.request_count.labels("POST", "/tools/call", "200").inc()
        return ToolCallResponse(tool_name=request.tool_name, result=result)
    except Exception as e:
        logger.error("tool_call_error", tool=request.tool_name, error=str(e))
        metrics.error_count.labels("tool_call").inc()
        return ToolCallResponse(
            tool_name=request.tool_name, result=f"Error: {e}", success=False
        )


@app.get("/health")
async def health():
    return {"status": "healthy", "tools_count": len(TOOLS)}
