from __future__ import annotations

from prometheus_client import Counter, Histogram


REQUEST_COUNTER = Counter(
    "voice_platform_requests_total",
    "Total logical requests handled by a service",
    ["service", "route"],
)

STAGE_LATENCY = Histogram(
    "voice_platform_stage_latency_seconds",
    "Latency for pipeline stages",
    ["service", "stage"],
)

