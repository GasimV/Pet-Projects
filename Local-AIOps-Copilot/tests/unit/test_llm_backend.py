"""Tests for the LLM abstraction layer and backends."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from shared.llm_backend.base import LLMMessage, LLMResponse, EmbeddingResponse
from shared.llm_backend.mock_client import MockLLMClient
from shared.llm_backend.factory import create_llm_client
from shared.config.settings import Settings, LLMBackendType


@pytest.mark.asyncio
async def test_mock_client_chat():
    client = MockLLMClient()
    messages = [LLMMessage(role="user", content="hello")]
    response = await client.chat(messages)
    assert isinstance(response, LLMResponse)
    assert "mock" in response.content.lower() or "hello" in response.content.lower()
    assert response.model == "mock-model"


@pytest.mark.asyncio
async def test_mock_client_stream():
    client = MockLLMClient()
    messages = [LLMMessage(role="user", content="hello")]
    tokens = []
    async for token in client.stream(messages):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens).strip()
    assert len(full) > 0


@pytest.mark.asyncio
async def test_mock_client_embeddings():
    client = MockLLMClient()
    response = await client.embeddings(["test text"])
    assert isinstance(response, EmbeddingResponse)
    assert len(response.embeddings) == 1
    assert len(response.embeddings[0]) == 384  # default dim


@pytest.mark.asyncio
async def test_mock_client_health_check():
    client = MockLLMClient()
    assert await client.health_check() is True


@pytest.mark.asyncio
async def test_mock_client_tool_calling():
    client = MockLLMClient()
    messages = [LLMMessage(role="user", content="what time is it")]
    tools = [{"type": "function", "function": {"name": "get_current_time"}}]
    response = await client.chat(messages, tools=tools)
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["function"]["name"] == "get_current_time"


def test_factory_creates_mock():
    s = Settings(llm_backend="mock", _env_file=None)
    client = create_llm_client(settings=s)
    assert client.backend_name == "mock"


def test_factory_creates_ollama():
    s = Settings(llm_backend="ollama", _env_file=None)
    client = create_llm_client(settings=s)
    assert client.backend_name == "ollama"


def test_factory_creates_vllm():
    s = Settings(llm_backend="vllm", _env_file=None)
    client = create_llm_client(settings=s)
    assert client.backend_name == "vllm"


def test_factory_creates_triton():
    s = Settings(llm_backend="triton", _env_file=None)
    client = create_llm_client(settings=s)
    assert client.backend_name == "triton"


def test_factory_backend_override():
    s = Settings(llm_backend="mock", _env_file=None)
    client = create_llm_client(backend="vllm", settings=s)
    assert client.backend_name == "vllm"


@pytest.mark.asyncio
async def test_mock_deterministic():
    """Mock client should return deterministic responses."""
    client = MockLLMClient()
    msg = [LLMMessage(role="user", content="ping")]
    r1 = await client.chat(msg)
    r2 = await client.chat(msg)
    assert r1.content == r2.content == "pong"
