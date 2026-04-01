"""Eval Service — evaluation, replay testing, and drift detection with MLflow."""

from __future__ import annotations

import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from shared.config import get_settings
from shared.logging import setup_logging, get_logger
from shared.metrics import setup_metrics

settings = get_settings()
setup_logging(settings.log_level, settings.log_format, "eval-service")
logger = get_logger(__name__)
metrics = setup_metrics("eval-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("eval_service_started", mlflow_uri=settings.mlflow_tracking_uri)
    yield
    logger.info("eval_service_stopped")


app = FastAPI(title="Eval Service", version="0.1.0", lifespan=lifespan)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ── Models ──


class EvalRequest(BaseModel):
    release_id: str
    model_name: str
    dataset_name: str = "default"
    metrics_to_compute: list[str] = Field(default_factory=lambda: ["latency", "quality", "consistency"])


class EvalResult(BaseModel):
    eval_id: str
    release_id: str
    model_name: str
    metrics: dict[str, float]
    mlflow_run_id: str | None = None
    status: str = "completed"


class ReplayRequest(BaseModel):
    release_id_blue: str
    release_id_green: str
    replay_dataset: str = "default"
    sample_size: int = 50


class ReplayResult(BaseModel):
    comparison_id: str
    blue_metrics: dict[str, float]
    green_metrics: dict[str, float]
    recommendation: str
    mlflow_run_id: str | None = None


class DriftRequest(BaseModel):
    release_id: str
    window_hours: int = 24
    reference_dataset: str = "baseline"


class DriftResult(BaseModel):
    drift_id: str
    release_id: str
    drift_detected: bool
    drift_score: float
    drift_details: dict[str, float] = Field(default_factory=dict)
    mlflow_run_id: str | None = None


# ── MLflow integration ──


def _log_to_mlflow(experiment_name: str, run_name: str, params: dict, metrics: dict) -> str | None:
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)
            return run.info.run_id
    except Exception as e:
        logger.warning("mlflow_log_failed", error=str(e))
        return None


# ── Endpoints ──


@app.post("/api/v1/eval", response_model=EvalResult)
async def run_evaluation(request: EvalRequest):
    """Run evaluation metrics on a release candidate."""
    eval_id = str(uuid.uuid4())[:8]
    start = time.time()

    # Simulated evaluation metrics (replace with real evaluation logic)
    eval_metrics = {
        "latency_p50_ms": 120.5,
        "latency_p99_ms": 450.2,
        "quality_score": 0.82,
        "consistency_score": 0.91,
        "error_rate": 0.02,
    }
    eval_metrics["eval_duration_s"] = round(time.time() - start, 3)

    mlflow_run_id = _log_to_mlflow(
        experiment_name="evaluations",
        run_name=f"eval-{request.release_id}-{eval_id}",
        params={"release_id": request.release_id, "model_name": request.model_name, "dataset": request.dataset_name},
        metrics=eval_metrics,
    )

    metrics.request_count.labels("POST", "/api/v1/eval", "200").inc()
    return EvalResult(
        eval_id=eval_id,
        release_id=request.release_id,
        model_name=request.model_name,
        metrics=eval_metrics,
        mlflow_run_id=mlflow_run_id,
    )


@app.post("/api/v1/replay", response_model=ReplayResult)
async def run_replay(request: ReplayRequest):
    """Run replay comparison between blue and green releases."""
    comparison_id = str(uuid.uuid4())[:8]

    # Simulated replay metrics
    blue_metrics = {"latency_p50_ms": 130.0, "quality_score": 0.80, "error_rate": 0.03}
    green_metrics = {"latency_p50_ms": 115.0, "quality_score": 0.85, "error_rate": 0.01}

    # Simple decision logic
    green_better = (
        green_metrics["quality_score"] > blue_metrics["quality_score"]
        and green_metrics["error_rate"] <= blue_metrics["error_rate"]
    )
    recommendation = "switch_to_green" if green_better else "stay_on_blue"

    mlflow_run_id = _log_to_mlflow(
        experiment_name="replay_comparisons",
        run_name=f"replay-{comparison_id}",
        params={
            "blue_release": request.release_id_blue,
            "green_release": request.release_id_green,
            "sample_size": str(request.sample_size),
        },
        metrics={**{f"blue_{k}": v for k, v in blue_metrics.items()}, **{f"green_{k}": v for k, v in green_metrics.items()}},
    )

    return ReplayResult(
        comparison_id=comparison_id,
        blue_metrics=blue_metrics,
        green_metrics=green_metrics,
        recommendation=recommendation,
        mlflow_run_id=mlflow_run_id,
    )


@app.post("/api/v1/drift", response_model=DriftResult)
async def detect_drift(request: DriftRequest):
    """Detect data or model drift for a release."""
    drift_id = str(uuid.uuid4())[:8]

    # Simulated drift detection
    drift_details = {
        "input_distribution_shift": 0.15,
        "output_distribution_shift": 0.08,
        "feature_drift_pct": 0.12,
    }
    drift_score = max(drift_details.values())
    drift_detected = drift_score > 0.20

    mlflow_run_id = _log_to_mlflow(
        experiment_name="drift_detection",
        run_name=f"drift-{request.release_id}-{drift_id}",
        params={"release_id": request.release_id, "window_hours": str(request.window_hours)},
        metrics={"drift_score": drift_score, **drift_details},
    )

    return DriftResult(
        drift_id=drift_id,
        release_id=request.release_id,
        drift_detected=drift_detected,
        drift_score=drift_score,
        drift_details=drift_details,
        mlflow_run_id=mlflow_run_id,
    )


@app.get("/health")
async def health():
    mlflow_ok = False
    try:
        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.search_experiments(max_results=1)
        mlflow_ok = True
    except Exception:
        pass
    return {"status": "healthy", "mlflow_connected": mlflow_ok}
