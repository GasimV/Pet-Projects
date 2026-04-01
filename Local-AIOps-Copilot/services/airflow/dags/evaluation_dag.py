"""Evaluation DAG — runs evaluation metrics on release candidates."""

from __future__ import annotations

import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "aiops-copilot",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": datetime.timedelta(minutes=5),
}


def evaluate_release(**context):
    """Trigger evaluation for a release candidate."""
    import httpx

    eval_url = "http://eval-service:50054"
    release_id = context["params"].get("release_id", "latest")
    model_name = context["params"].get("model_name", "default-model")

    try:
        resp = httpx.post(
            f"{eval_url}/api/v1/eval",
            json={
                "release_id": release_id,
                "model_name": model_name,
                "metrics_to_compute": ["latency", "quality", "consistency"],
            },
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"Evaluation complete: {result}")
        return result
    except Exception as e:
        print(f"Evaluation failed: {e}")
        raise


with DAG(
    dag_id="evaluation_pipeline",
    default_args=default_args,
    description="Evaluate release candidates against quality metrics",
    schedule_interval=None,  # Triggered manually or by upstream
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["evaluation", "mlops"],
) as dag:
    evaluate_task = PythonOperator(
        task_id="evaluate_release",
        python_callable=evaluate_release,
        params={"release_id": "latest", "model_name": "default-model"},
    )
