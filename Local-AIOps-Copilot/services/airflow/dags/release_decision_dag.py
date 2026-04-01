"""Release Decision DAG — orchestrates the full blue-green release pipeline.

Pipeline: evaluate → replay → drift → decide
"""

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


def evaluate_candidates(**context):
    """Evaluate both blue and green candidates."""
    import httpx

    eval_url = "http://eval-service:50054"
    for slot in ["blue", "green"]:
        release_id = context["params"].get(f"{slot}_release_id", f"{slot}-latest")
        try:
            resp = httpx.post(
                f"{eval_url}/api/v1/eval",
                json={"release_id": release_id, "model_name": "default"},
                timeout=120,
            )
            resp.raise_for_status()
            context["ti"].xcom_push(key=f"{slot}_eval", value=resp.json())
        except Exception as e:
            print(f"Evaluation failed for {slot}: {e}")
            raise


def run_replay(**context):
    """Replay comparison."""
    import httpx

    eval_url = "http://eval-service:50054"
    blue_id = context["params"].get("blue_release_id", "blue-latest")
    green_id = context["params"].get("green_release_id", "green-latest")

    resp = httpx.post(
        f"{eval_url}/api/v1/replay",
        json={"release_id_blue": blue_id, "release_id_green": green_id},
        timeout=300,
    )
    resp.raise_for_status()
    context["ti"].xcom_push(key="replay_result", value=resp.json())


def check_drift(**context):
    """Check drift on active release."""
    import httpx

    eval_url = "http://eval-service:50054"
    release_id = context["params"].get("blue_release_id", "blue-latest")

    resp = httpx.post(
        f"{eval_url}/api/v1/drift",
        json={"release_id": release_id, "window_hours": 24},
        timeout=120,
    )
    resp.raise_for_status()
    context["ti"].xcom_push(key="drift_result", value=resp.json())


def make_release_decision(**context):
    """Call the release controller to make a decision."""
    import httpx

    controller_url = "http://release-controller:50055"
    blue_id = context["params"].get("blue_release_id", "blue-latest")
    green_id = context["params"].get("green_release_id", "green-latest")

    resp = httpx.post(
        f"{controller_url}/api/v1/releases/decide",
        json={
            "blue_release_id": blue_id,
            "green_release_id": green_id,
            "auto_apply": False,  # recommendation only by default
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"Release decision: {result['decision']}")
    print(f"Rationale: {result['rationale']}")
    return result


with DAG(
    dag_id="release_decision_pipeline",
    default_args=default_args,
    description="Full blue-green release decision pipeline: eval → replay → drift → decide",
    schedule_interval=None,
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["release", "blue-green", "mlops", "decision"],
) as dag:
    evaluate = PythonOperator(
        task_id="evaluate_candidates",
        python_callable=evaluate_candidates,
        params={"blue_release_id": "blue-latest", "green_release_id": "green-latest"},
    )

    replay = PythonOperator(
        task_id="run_replay",
        python_callable=run_replay,
        params={"blue_release_id": "blue-latest", "green_release_id": "green-latest"},
    )

    drift = PythonOperator(
        task_id="check_drift",
        python_callable=check_drift,
        params={"blue_release_id": "blue-latest"},
    )

    decide = PythonOperator(
        task_id="make_release_decision",
        python_callable=make_release_decision,
        params={"blue_release_id": "blue-latest", "green_release_id": "green-latest"},
    )

    evaluate >> [replay, drift] >> decide
