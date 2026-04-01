"""Tests for the blue-green release decision engine."""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _import_decision():
    mod_path = str(
        Path(__file__).resolve().parents[2]
        / "services" / "release-controller" / "app" / "decision_engine.py"
    )
    spec = importlib.util.spec_from_file_location("decision_engine", mod_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decision_engine"] = mod
    spec.loader.exec_module(mod)
    return mod.make_decision, mod.DecisionCriteria


make_decision, DecisionCriteria = _import_decision()


def test_switch_to_green_when_better():
    blue = {"error_rate": 0.03, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.01, "quality_score": 0.85, "latency_p99_ms": 350.0}
    decision, rationale = make_decision(blue, green)
    assert decision == "switch_to_green"
    assert "passes all gates" in rationale


def test_stay_on_blue_marginal_improvement():
    blue = {"error_rate": 0.03, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.03, "quality_score": 0.81, "latency_p99_ms": 400.0}
    decision, _ = make_decision(blue, green)
    assert decision == "stay_on_blue"


def test_rollback_high_error_rate():
    blue = {"error_rate": 0.02, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.10, "quality_score": 0.90, "latency_p99_ms": 300.0}
    decision, rationale = make_decision(blue, green)
    assert decision == "rollback_to_blue"
    assert "error rate" in rationale.lower()


def test_rollback_low_quality():
    blue = {"error_rate": 0.02, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.01, "quality_score": 0.50, "latency_p99_ms": 300.0}
    decision, _ = make_decision(blue, green)
    assert decision == "rollback_to_blue"


def test_hold_for_review_high_latency():
    blue = {"error_rate": 0.02, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.01, "quality_score": 0.90, "latency_p99_ms": 1500.0}
    decision, _ = make_decision(blue, green)
    assert decision == "hold_for_review"


def test_hold_for_review_drift():
    blue = {"error_rate": 0.02, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.01, "quality_score": 0.85, "latency_p99_ms": 350.0}
    decision, _ = make_decision(blue, green, drift_score=0.30)
    assert decision == "hold_for_review"


def test_hold_when_error_regresses():
    blue = {"error_rate": 0.01, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.02, "quality_score": 0.90, "latency_p99_ms": 350.0}
    decision, _ = make_decision(blue, green)
    assert decision in ("switch_to_green", "hold_for_review")


def test_custom_criteria():
    blue = {"error_rate": 0.03, "quality_score": 0.80, "latency_p99_ms": 400.0}
    green = {"error_rate": 0.01, "quality_score": 0.81, "latency_p99_ms": 350.0}
    criteria = DecisionCriteria(min_quality_improvement=0.005)
    decision, _ = make_decision(blue, green, criteria=criteria)
    assert decision == "switch_to_green"
