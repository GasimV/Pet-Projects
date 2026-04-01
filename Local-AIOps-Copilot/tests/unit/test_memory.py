"""Tests for conversation memory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import importlib.util
import pytest


def _import_memory():
    spec = importlib.util.spec_from_file_location(
        "memory",
        str(Path(__file__).resolve().parents[2] / "services" / "agent-service" / "app" / "memory.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.InMemoryConversationMemory


InMemoryConversationMemory = _import_memory()


@pytest.mark.asyncio
async def test_add_and_get_messages():
    mem = InMemoryConversationMemory()
    await mem.add_message("s1", "user", "hello")
    await mem.add_message("s1", "assistant", "hi there")
    history = await mem.get_history("s1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "hi there"


@pytest.mark.asyncio
async def test_session_isolation():
    mem = InMemoryConversationMemory()
    await mem.add_message("s1", "user", "msg1")
    await mem.add_message("s2", "user", "msg2")
    assert len(await mem.get_history("s1")) == 1
    assert len(await mem.get_history("s2")) == 1


@pytest.mark.asyncio
async def test_max_history():
    mem = InMemoryConversationMemory(max_history=3)
    for i in range(5):
        await mem.add_message("s1", "user", f"msg{i}")
    history = await mem.get_history("s1")
    assert len(history) == 3
    assert history[0]["content"] == "msg2"


@pytest.mark.asyncio
async def test_clear():
    mem = InMemoryConversationMemory()
    await mem.add_message("s1", "user", "hello")
    await mem.clear("s1")
    assert len(await mem.get_history("s1")) == 0


@pytest.mark.asyncio
async def test_health_check():
    mem = InMemoryConversationMemory()
    assert await mem.health_check() is True
