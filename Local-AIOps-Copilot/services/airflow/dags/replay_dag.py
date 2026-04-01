"""Replay DAG — runs replay comparison between blue and green releases."""

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


def replay_comparison(**context):
    """Run replay traffic through both blue and green releases."""
    import httpx

    eval_url = "http://eval-service:50054"
    blue_id = context["params"].get("blue_release_id", "blue-latest")
    green_id = context["params"].get("green_release_id", "green-latest")

    try:
        resp = httpx.post(
            f"{eval_url}/api/v1/replay",
            json={
                "release_id_blue": blue_id,
                "release_id_green": green_id,
                "sample_size": 50,
            },
            timeout=300,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"Replay result: {result}")
        context["ti"].xcom_push(key="replay_result", value=result)
        return result
    except Exception as e:
        print(f"Replay failed: {e}")
        raise


with DAG(
    dag_id="replay_pipeline",
    default_args=default_args,
    description="Replay comparison between blue and green releases",
    schedule_interval=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["replay", "mlops", "blue-green"],
) as dag:
    replay_task = PythonOperator(
        task_id="replay_comparison",
        python_callable=replay_comparison,
        params={"blue_release_id": "blue-latest", "green_release_id": "green-latest"},
    )
