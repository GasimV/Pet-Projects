"""Smoke tests — verify services are reachable and respond.

These tests require running services (docker-compose up).
Run with: pytest tests/smoke/ -m smoke
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os

import httpx
import pytest

API_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080")
EVAL_URL = os.getenv("EVAL_SERVICE_URL", "http://localhost:50054")
RELEASE_URL = os.getenv("RELEASE_CONTROLLER_URL", "http://localhost:50055")
MCP_URL = os.getenv("MCP_TOOL_SERVER_URL", "http://localhost:50053")


@pytest.mark.smoke
def test_api_gateway_health():
    resp = httpx.get(f"{API_URL}/health", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.smoke
def test_api_gateway_backend_info():
    resp = httpx.get(f"{API_URL}/api/v1/backend/info", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "backend" in data
    assert "environment" in data


@pytest.mark.smoke
def test_chat_sync():
    resp = httpx.post(
        f"{API_URL}/api/v1/chat",
        json={"message": "hello", "use_tools": False, "use_rag": False},
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "session_id" in data


@pytest.mark.smoke
def test_chat_stream():
    with httpx.stream(
        "POST",
        f"{API_URL}/api/v1/chat/stream",
        json={"message": "hello"},
        timeout=30,
    ) as resp:
        assert resp.status_code == 200
        events = list(resp.iter_lines())
        assert len(events) > 0


@pytest.mark.smoke
def test_mcp_list_tools():
    resp = httpx.get(f"{MCP_URL}/tools", timeout=10)
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) > 0
    tool_names = [t["name"] for t in tools]
    assert "get_current_time" in tool_names


@pytest.mark.smoke
def test_mcp_call_tool():
    resp = httpx.post(
        f"{MCP_URL}/tools/call",
        json={"tool_name": "get_current_time", "arguments": {}},
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.smoke
def test_eval_service_health():
    resp = httpx.get(f"{EVAL_URL}/health", timeout=10)
    assert resp.status_code == 200


@pytest.mark.smoke
def test_release_controller_health():
    resp = httpx.get(f"{RELEASE_URL}/health", timeout=10)
    assert resp.status_code == 200
