"""Blue-Green release decision engine."""

from __future__ import annotations

from dataclasses import dataclass

from shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionCriteria:
    """Thresholds for automatic release decisions."""

    max_error_rate: float = 0.05
    min_quality_score: float = 0.70
    max_latency_p99_ms: float = 1000.0
    max_drift_score: float = 0.25
    min_quality_improvement: float = 0.02  # green must be at least this much better


def make_decision(
    blue_metrics: dict[str, float],
    green_metrics: dict[str, float],
    drift_score: float = 0.0,
    criteria: DecisionCriteria | None = None,
) -> tuple[str, str]:
    """Evaluate blue vs green metrics and return (decision, rationale).

    Returns one of:
        - stay_on_blue
        - switch_to_green
        - rollback_to_blue
        - hold_for_review
    """
    criteria = criteria or DecisionCriteria()
    reasons = []

    green_error = green_metrics.get("error_rate", 0)
    green_quality = green_metrics.get("quality_score", 0)
    green_latency = green_metrics.get("latency_p99_ms", 0)
    blue_error = blue_metrics.get("error_rate", 0)
    blue_quality = blue_metrics.get("quality_score", 0)
    blue_latency = blue_metrics.get("latency_p99_ms", 0)

    # Gate 1: Green must meet minimum thresholds
    if green_error > criteria.max_error_rate:
        reasons.append(f"Green error rate {green_error:.3f} exceeds max {criteria.max_error_rate}")
        return "rollback_to_blue", "; ".join(reasons)

    if green_quality < criteria.min_quality_score:
        reasons.append(f"Green quality {green_quality:.3f} below min {criteria.min_quality_score}")
        return "rollback_to_blue", "; ".join(reasons)

    if green_latency > criteria.max_latency_p99_ms:
        reasons.append(f"Green p99 latency {green_latency:.1f}ms exceeds max {criteria.max_latency_p99_ms}ms")
        return "hold_for_review", "; ".join(reasons)

    # Gate 2: Check for drift
    if drift_score > criteria.max_drift_score:
        reasons.append(f"Drift score {drift_score:.3f} exceeds threshold {criteria.max_drift_score}")
        return "hold_for_review", "; ".join(reasons)

    # Gate 3: Compare green vs blue
    quality_improvement = green_quality - blue_quality
    if quality_improvement < criteria.min_quality_improvement:
        reasons.append(
            f"Green quality improvement {quality_improvement:.3f} below min "
            f"{criteria.min_quality_improvement} (blue={blue_quality:.3f}, green={green_quality:.3f})"
        )
        if green_error <= blue_error and green_latency <= blue_latency:
            reasons.append("Green is not worse on error/latency, but quality gain is marginal")
            return "stay_on_blue", "; ".join(reasons)
        return "stay_on_blue", "; ".join(reasons)

    # Gate 4: Green must not regress on other metrics
    if green_error > blue_error * 1.5:
        reasons.append(f"Green error rate {green_error:.3f} is >1.5x blue ({blue_error:.3f})")
        return "hold_for_review", "; ".join(reasons)

    if green_latency > blue_latency * 1.3:
        reasons.append(f"Green latency {green_latency:.1f}ms is >1.3x blue ({blue_latency:.1f}ms)")
        return "hold_for_review", "; ".join(reasons)

    # All gates passed
    reasons.append(
        f"Green passes all gates: quality={green_quality:.3f} (+{quality_improvement:.3f}), "
        f"error_rate={green_error:.3f}, p99={green_latency:.1f}ms, drift={drift_score:.3f}"
    )
    return "switch_to_green", "; ".join(reasons)
