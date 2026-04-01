"""Triton Inference Server client — alternative GPU backend for comparison.

Triton uses a different API from OpenAI-compatible servers. It exposes
HTTP and gRPC endpoints for model inference. This client normalizes
Triton's interface to match the LLMClient abstraction.

Triton model repository must be configured with an ensemble or
python_backend model that accepts chat-style inputs (prompt string)
and returns generated text.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx
import numpy as np

from shared.llm_backend.base import (
    EmbeddingResponse,
    LLMClient,
    LLMMessage,
    LLMResponse,
)


def _messages_to_prompt(messages: list[LLMMessage]) -> str:
    """Convert chat messages to a single prompt string for Triton."""
    parts = []
    for m in messages:
        if m.role == "system":
            parts.append(f"<|system|>\n{m.content}")
        elif m.role == "user":
            parts.append(f"<|user|>\n{m.content}")
        elif m.role == "assistant":
            parts.append(f"<|assistant|>\n{m.content}")
    parts.append("<|assistant|>\n")
    return "\n".join(parts)


class TritonClient(LLMClient):
    """Connects to NVIDIA Triton Inference Server for GPU inference.

    Triton exposes:
      - HTTP: http://<host>:8001/v2/models/<model>/infer
      - gRPC: <host>:8002

    This client uses the HTTP API. The model must accept:
      - input: text_input (STRING), max_tokens (INT32), temperature (FP32)
      - output: text_output (STRING)

    For a vLLM-backed Triton setup, use the vLLM Triton backend which
    exposes this interface natively.
    """

    def __init__(
        self,
        http_url: str,
        model: str,
        timeout: int = 60,
        grpc_url: str | None = None,
    ):
        self._http_url = http_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._grpc_url = grpc_url
        self._http = httpx.AsyncClient(base_url=self._http_url, timeout=timeout)

    @property
    def backend_name(self) -> str:
        return "triton"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_infer_payload(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict:
        """Build Triton KServe v2 inference request."""
        payload: dict = {
            "inputs": [
                {
                    "name": "text_input",
                    "shape": [1, 1],
                    "datatype": "BYTES",
                    "data": [prompt],
                },
                {
                    "name": "max_tokens",
                    "shape": [1, 1],
                    "datatype": "INT32",
                    "data": [max_tokens],
                },
                {
                    "name": "temperature",
                    "shape": [1, 1],
                    "datatype": "FP32",
                    "data": [temperature],
                },
            ],
            "outputs": [{"name": "text_output"}],
        }
        if stream:
            payload["inputs"].append(
                {
                    "name": "stream",
                    "shape": [1, 1],
                    "datatype": "BOOL",
                    "data": [True],
                }
            )
        return payload

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        prompt = _messages_to_prompt(messages)
        payload = self._build_infer_payload(
            prompt=prompt,
            max_tokens=max_tokens or 512,
            temperature=temperature or 0.7,
        )

        resp = await self._http.post(
            f"/v2/models/{self._model}/infer",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        output_text = ""
        for output in data.get("outputs", []):
            if output["name"] == "text_output":
                output_data = output.get("data", [])
                if output_data:
                    output_text = output_data[0]
                break

        prompt_tokens = len(prompt.split())
        completion_tokens = len(output_text.split())
        return LLMResponse(
            content=output_text,
            model=self._model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        prompt = _messages_to_prompt(messages)
        payload = self._build_infer_payload(
            prompt=prompt,
            max_tokens=max_tokens or 512,
            temperature=temperature or 0.7,
            stream=True,
        )

        async with self._http.stream(
            "POST",
            f"/v2/models/{self._model}/generate_stream",
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        token = chunk.get("text_output", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
                else:
                    try:
                        chunk = json.loads(line)
                        for output in chunk.get("outputs", []):
                            if output["name"] == "text_output":
                                for token in output.get("data", []):
                                    if token:
                                        yield token
                    except json.JSONDecodeError:
                        continue

    async def embeddings(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings using a Triton-hosted embedding model.

        Expects the model to accept text_input and return embeddings
        as a float array output named 'embedding'.
        """
        all_embeddings = []
        for text in texts:
            payload = {
                "inputs": [
                    {
                        "name": "text_input",
                        "shape": [1, 1],
                        "datatype": "BYTES",
                        "data": [text],
                    }
                ],
                "outputs": [{"name": "embedding"}],
            }
            resp = await self._http.post(
                f"/v2/models/{self._model}_embed/infer",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            for output in data.get("outputs", []):
                if output["name"] == "embedding":
                    all_embeddings.append(output["data"])
                    break

        return EmbeddingResponse(
            embeddings=all_embeddings,
            model=self._model,
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._http.get("/v2/health/ready")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._http.aclose()
