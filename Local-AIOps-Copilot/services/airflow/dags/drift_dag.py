"""Drift Detection DAG — monitors for data and model drift."""

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


def detect_drift(**context):
    """Run drift detection for the active release."""
    import httpx

    eval_url = "http://eval-service:50054"
    release_id = context["params"].get("release_id", "active")

    try:
        resp = httpx.post(
            f"{eval_url}/api/v1/drift",
            json={
                "release_id": release_id,
                "window_hours": 24,
            },
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"Drift detection result: {result}")

        if result.get("drift_detected"):
            print("DRIFT DETECTED — triggering review")
            # Could trigger an alert or downstream DAG here

        context["ti"].xcom_push(key="drift_result", value=result)
        return result
    except Exception as e:
        print(f"Drift detection failed: {e}")
        raise


with DAG(
    dag_id="drift_detection_pipeline",
    default_args=default_args,
    description="Monitor for data and model drift on active releases",
    schedule_interval="@hourly",
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["drift", "monitoring", "mlops"],
) as dag:
    drift_task = PythonOperator(
        task_id="detect_drift",
        python_callable=detect_drift,
        params={"release_id": "active"},
    )
