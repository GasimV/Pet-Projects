from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
service_path = str(ROOT / "apps" / "tool-service")
if service_path not in sys.path:
    sys.path.insert(0, service_path)

from tool_service_app.tools import (
    get_domain_mode,
    get_system_status,
    list_capabilities,
    search_manuals,
)

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - dependency may be absent before bootstrap
    FastMCP = None


def build_server():
    if FastMCP is None:
        raise RuntimeError("mcp is not installed")
    server = FastMCP("voice-platform-tools")

    @server.tool()
    def tool_get_system_status() -> dict:
        return get_system_status()

    @server.tool()
    def tool_get_domain_mode(domain: str | None = None) -> dict:
        return get_domain_mode(domain=domain)

    @server.tool()
    def tool_search_manuals(query: str, domain: str | None = None) -> dict:
        return search_manuals(query=query, domain=domain)

    @server.tool()
    def tool_list_capabilities() -> dict:
        return list_capabilities()

    return server


if __name__ == "__main__":  # pragma: no cover
    build_server().run()
