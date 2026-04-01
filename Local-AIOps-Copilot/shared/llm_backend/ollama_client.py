"""Ollama LLM client — lightweight local model backend for dev machines."""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from shared.llm_backend.base import (
    EmbeddingResponse,
    LLMClient,
    LLMMessage,
    LLMResponse,
)


class OllamaLLMClient(LLMClient):
    """Connects to a local Ollama instance for CPU-friendly inference."""

    def __init__(self, base_url: str, model: str, timeout: int = 60):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    @property
    def backend_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "stream": False,
        }
        options: dict = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        resp = await self._http.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
            },
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload: dict = {
            "model": self._model,
            "messages": self._convert_messages(messages),
            "stream": True,
        }
        options: dict = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        async with self._http.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                import json

                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token

    async def embeddings(self, texts: list[str]) -> EmbeddingResponse:
        all_embeddings = []
        for text in texts:
            resp = await self._http.post(
                "/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            all_embeddings.append(data["embedding"])
        return EmbeddingResponse(
            embeddings=all_embeddings,
            model=self._model,
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._http.aclose()
