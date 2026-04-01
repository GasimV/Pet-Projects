"""Mock LLM client for development and testing — deterministic responses."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from shared.llm_backend.base import (
    EmbeddingResponse,
    LLMClient,
    LLMMessage,
    LLMResponse,
)

_MOCK_RESPONSES: dict[str, str] = {
    "ping": "pong",
    "hello": "Hello! I'm the Local-AIOps-Copilot mock assistant. How can I help you?",
    "default": (
        "I'm running in mock mode. This is a deterministic response for development "
        "and testing. To use a real LLM backend, set LLM_BACKEND to 'ollama', 'vllm', "
        "or 'triton' in your .env file."
    ),
}


class MockLLMClient(LLMClient):
    """Deterministic mock backend for CPU-only development."""

    def __init__(self, model: str = "mock-model", latency: float = 0.1):
        self._model = model
        self._latency = latency

    @property
    def backend_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        await asyncio.sleep(self._latency)
        last_content = messages[-1].content.strip().lower() if messages else ""
        response_text = _MOCK_RESPONSES.get(last_content, _MOCK_RESPONSES["default"])

        # Simulate tool calling if tools are provided
        tool_calls = None
        if tools and "what time" in last_content:
            tool_calls = [
                {
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "arguments": "{}",
                    },
                }
            ]
            response_text = ""

        prompt_tokens = sum(len(m.content.split()) for m in messages)
        completion_tokens = len(response_text.split())
        return LLMResponse(
            content=response_text,
            model=self._model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        last_content = messages[-1].content.strip().lower() if messages else ""
        response_text = _MOCK_RESPONSES.get(last_content, _MOCK_RESPONSES["default"])
        words = response_text.split()
        for word in words:
            await asyncio.sleep(self._latency / len(words))
            yield word + " "

    async def embeddings(self, texts: list[str]) -> EmbeddingResponse:
        await asyncio.sleep(self._latency)
        dim = 384
        fake_embeddings = []
        for text in texts:
            vec = [(hash(text + str(i)) % 1000) / 1000.0 for i in range(dim)]
            norm = sum(v * v for v in vec) ** 0.5
            fake_embeddings.append([v / norm for v in vec])
        return EmbeddingResponse(
            embeddings=fake_embeddings,
            model=self._model,
            usage={"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": 0},
        )

    async def health_check(self) -> bool:
        return True
