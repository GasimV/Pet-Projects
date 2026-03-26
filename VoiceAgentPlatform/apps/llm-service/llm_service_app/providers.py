from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncIterator

import httpx


@dataclass(slots=True)
class GenerationPiece:
    token: str
    is_final: bool = False


class BaseProvider:
    async def stream(
        self, messages: list[dict[str, str]], system_prompt: str, context: str
    ) -> AsyncIterator[GenerationPiece]:
        raise NotImplementedError


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def stream(
        self, messages: list[dict[str, str]], system_prompt: str, context: str
    ) -> AsyncIterator[GenerationPiece]:
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [
                {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context}".strip()},
                *messages,
            ],
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield GenerationPiece(token=chunk)
                    if data.get("done"):
                        yield GenerationPiece(token="", is_final=True)
                        break


class VllmProvider(BaseProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def stream(
        self, messages: list[dict[str, str]], system_prompt: str, context: str
    ) -> AsyncIterator[GenerationPiece]:
        payload = {
            "model": self._model,
            "stream": True,
            "messages": [
                {"role": "system", "content": f"{system_prompt}\n\nContext:\n{context}".strip()},
                *messages,
            ],
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self._base_url}/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        yield GenerationPiece(token="", is_final=True)
                        break
                    delta = json.loads(raw)["choices"][0]["delta"]
                    content = delta.get("content", "")
                    if content:
                        yield GenerationPiece(token=content)

