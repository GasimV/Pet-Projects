"""Redis-backed conversation memory for the agent service."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from shared.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Stores conversation history per session in Redis."""

    def __init__(self, redis_url: str, max_history: int = 50, ttl_seconds: int = 3600):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._max_history = max_history
        self._ttl = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"copilot:chat:{session_id}"

    async def add_message(self, session_id: str, role: str, content: str):
        key = self._key(session_id)
        msg = json.dumps({"role": role, "content": content})
        await self._redis.rpush(key, msg)
        await self._redis.ltrim(key, -self._max_history, -1)
        await self._redis.expire(key, self._ttl)

    async def get_history(self, session_id: str) -> list[dict]:
        key = self._key(session_id)
        raw = await self._redis.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]

    async def clear(self, session_id: str):
        await self._redis.delete(self._key(session_id))

    async def health_check(self) -> bool:
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def close(self):
        await self._redis.aclose()


class InMemoryConversationMemory:
    """Fallback in-memory store when Redis is unavailable."""

    def __init__(self, max_history: int = 50):
        self._store: dict[str, list[dict]] = {}
        self._max_history = max_history

    async def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append({"role": role, "content": content})
        self._store[session_id] = self._store[session_id][-self._max_history:]

    async def get_history(self, session_id: str) -> list[dict]:
        return list(self._store.get(session_id, []))

    async def clear(self, session_id: str):
        self._store.pop(session_id, None)

    async def health_check(self) -> bool:
        return True

    async def close(self):
        self._store.clear()
