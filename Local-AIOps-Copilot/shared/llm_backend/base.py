"""Abstract base classes for the pluggable LLM backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    tool_calls: list[dict] | None = None

    @property
    def prompt_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", 0)


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class LLMClient(ABC):
    """Abstract LLM client — all backends implement this interface."""

    @property
    @abstractmethod
    def backend_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request and return the full response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens as an async iterator."""
        ...

    @abstractmethod
    async def embeddings(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for a list of texts."""
        ...

    async def health_check(self) -> bool:
        """Check if the backend is available."""
        try:
            resp = await self.chat(
                [LLMMessage(role="user", content="ping")], max_tokens=5
            )
            return bool(resp.content)
        except Exception:
            return False

    async def close(self):
        """Clean up resources."""
        pass
