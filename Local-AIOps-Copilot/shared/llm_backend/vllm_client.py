"""vLLM client — primary GPU inference backend via OpenAI-compatible API."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from shared.llm_backend.base import (
    EmbeddingResponse,
    LLMClient,
    LLMMessage,
    LLMResponse,
)


class VLLMClient(LLMClient):
    """Connects to a vLLM server exposing an OpenAI-compatible API.

    vLLM is the primary GPU backend, running in Docker with --gpus all
    on the second machine. It exposes /v1/chat/completions and
    /v1/embeddings endpoints.
    """

    def __init__(self, base_url: str, model: str, timeout: int = 60):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    @property
    def backend_name(self) -> str:
        return "vllm"

    @property
    def model_name(self) -> str:
        return self._model

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        converted = []
        for m in messages:
            msg: dict = {"role": m.role, "content": m.content}
            if m.name:
                msg["name"] = m.name
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            converted.append(msg)
        return converted

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
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        resp = await self._http.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = message["tool_calls"]

        return LLMResponse(
            content=message.get("content", "") or "",
            model=data.get("model", self._model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=tool_calls,
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
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with self._http.stream(
            "POST", "/v1/chat/completions", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    yield token

    async def embeddings(self, texts: list[str]) -> EmbeddingResponse:
        payload = {"model": self._model, "input": texts}
        resp = await self._http.post("/v1/embeddings", json=payload)
        resp.raise_for_status()
        data = resp.json()
        vecs = [item["embedding"] for item in data["data"]]
        return EmbeddingResponse(
            embeddings=vecs,
            model=data.get("model", self._model),
            usage=data.get("usage", {}),
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._http.aclose()
