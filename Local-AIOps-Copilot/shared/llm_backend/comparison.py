"""Side-by-side backend comparison for evaluating vLLM vs Triton."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from shared.llm_backend.base import LLMClient, LLMMessage, LLMResponse
from shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing two backends on the same request."""

    prompt: str
    backend_a_name: str
    backend_b_name: str
    response_a: LLMResponse | None = None
    response_b: LLMResponse | None = None
    latency_a_ms: float = 0.0
    latency_b_ms: float = 0.0
    error_a: str | None = None
    error_b: str | None = None

    @property
    def both_succeeded(self) -> bool:
        return self.response_a is not None and self.response_b is not None

    @property
    def latency_diff_ms(self) -> float:
        return self.latency_a_ms - self.latency_b_ms

    @property
    def faster_backend(self) -> str:
        if self.latency_a_ms < self.latency_b_ms:
            return self.backend_a_name
        return self.backend_b_name

    def to_dict(self) -> dict:
        result = {
            "prompt": self.prompt[:100],
            "backend_a": self.backend_a_name,
            "backend_b": self.backend_b_name,
            "latency_a_ms": round(self.latency_a_ms, 2),
            "latency_b_ms": round(self.latency_b_ms, 2),
            "faster": self.faster_backend,
            "latency_diff_ms": round(abs(self.latency_diff_ms), 2),
        }
        if self.response_a:
            result["tokens_a"] = self.response_a.total_tokens
            result["content_a_preview"] = self.response_a.content[:200]
        if self.response_b:
            result["tokens_b"] = self.response_b.total_tokens
            result["content_b_preview"] = self.response_b.content[:200]
        if self.error_a:
            result["error_a"] = self.error_a
        if self.error_b:
            result["error_b"] = self.error_b
        return result


@dataclass
class ComparisonReport:
    """Aggregate report across multiple comparison requests."""

    results: list[ComparisonResult] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return len(self.results)

    @property
    def both_succeeded_count(self) -> int:
        return sum(1 for r in self.results if r.both_succeeded)

    @property
    def avg_latency_a_ms(self) -> float:
        succeeded = [r for r in self.results if r.response_a is not None]
        if not succeeded:
            return 0.0
        return sum(r.latency_a_ms for r in succeeded) / len(succeeded)

    @property
    def avg_latency_b_ms(self) -> float:
        succeeded = [r for r in self.results if r.response_b is not None]
        if not succeeded:
            return 0.0
        return sum(r.latency_b_ms for r in succeeded) / len(succeeded)

    def summary(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "both_succeeded": self.both_succeeded_count,
            "avg_latency_a_ms": round(self.avg_latency_a_ms, 2),
            "avg_latency_b_ms": round(self.avg_latency_b_ms, 2),
            "results": [r.to_dict() for r in self.results],
        }


async def _timed_chat(
    client: LLMClient, messages: list[LLMMessage], **kwargs
) -> tuple[LLMResponse | None, float, str | None]:
    """Execute a chat request and measure latency."""
    start = time.perf_counter()
    try:
        response = await client.chat(messages, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        return response, elapsed, None
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return None, elapsed, str(exc)


async def compare_backends(
    client_a: LLMClient,
    client_b: LLMClient,
    prompts: list[str],
    *,
    temperature: float = 0.7,
    max_tokens: int = 256,
    parallel: bool = True,
) -> ComparisonReport:
    """Run the same prompts through two backends and compare results.

    Args:
        client_a: First backend (e.g., vLLM).
        client_b: Second backend (e.g., Triton).
        prompts: List of user prompts to test.
        temperature: Sampling temperature.
        max_tokens: Max tokens per response.
        parallel: If True, run both backends concurrently per prompt.

    Returns:
        ComparisonReport with per-prompt and aggregate results.
    """
    report = ComparisonReport()

    for prompt in prompts:
        messages = [LLMMessage(role="user", content=prompt)]
        kwargs = {"temperature": temperature, "max_tokens": max_tokens}

        if parallel:
            (resp_a, lat_a, err_a), (resp_b, lat_b, err_b) = await asyncio.gather(
                _timed_chat(client_a, messages, **kwargs),
                _timed_chat(client_b, messages, **kwargs),
            )
        else:
            resp_a, lat_a, err_a = await _timed_chat(client_a, messages, **kwargs)
            resp_b, lat_b, err_b = await _timed_chat(client_b, messages, **kwargs)

        result = ComparisonResult(
            prompt=prompt,
            backend_a_name=client_a.backend_name,
            backend_b_name=client_b.backend_name,
            response_a=resp_a,
            response_b=resp_b,
            latency_a_ms=lat_a,
            latency_b_ms=lat_b,
            error_a=err_a,
            error_b=err_b,
        )
        report.results.append(result)
        logger.info(
            "comparison_result",
            prompt=prompt[:50],
            faster=result.faster_backend,
            diff_ms=round(abs(result.latency_diff_ms), 2),
        )

    return report
