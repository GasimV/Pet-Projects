"""Prometheus metrics shared across services."""

from __future__ import annotations

from dataclasses import dataclass, field

from prometheus_client import Counter, Histogram, Info


@dataclass
class ServiceMetrics:
    service_name: str
    info: Info = field(init=False)
    request_count: Counter = field(init=False)
    request_latency: Histogram = field(init=False)
    error_count: Counter = field(init=False)
    llm_request_count: Counter = field(init=False)
    llm_request_latency: Histogram = field(init=False)
    llm_token_count: Counter = field(init=False)

    def __post_init__(self):
        prefix = self.service_name.replace("-", "_")
        self.info = Info(f"{prefix}_info", f"Info about {self.service_name}")
        self.request_count = Counter(
            f"{prefix}_requests_total",
            "Total requests",
            ["method", "endpoint", "status"],
        )
        self.request_latency = Histogram(
            f"{prefix}_request_duration_seconds",
            "Request latency in seconds",
            ["method", "endpoint"],
        )
        self.error_count = Counter(
            f"{prefix}_errors_total",
            "Total errors",
            ["error_type"],
        )
        self.llm_request_count = Counter(
            f"{prefix}_llm_requests_total",
            "Total LLM requests",
            ["backend", "model"],
        )
        self.llm_request_latency = Histogram(
            f"{prefix}_llm_request_duration_seconds",
            "LLM request latency",
            ["backend", "model"],
        )
        self.llm_token_count = Counter(
            f"{prefix}_llm_tokens_total",
            "Total LLM tokens",
            ["backend", "model", "direction"],
        )


_metrics: dict[str, ServiceMetrics] = {}


def setup_metrics(service_name: str) -> ServiceMetrics:
    if service_name not in _metrics:
        _metrics[service_name] = ServiceMetrics(service_name=service_name)
    return _metrics[service_name]


def get_metrics(service_name: str) -> ServiceMetrics:
    if service_name not in _metrics:
        return setup_metrics(service_name)
    return _metrics[service_name]
