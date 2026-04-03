"""
FactoryPulse — Feast Materialize DAG
======================================
Runs an incremental Feast materialization every hour so that the online
feature store (Redis) stays fresh for real-time serving via the FastAPI
layer.
"""

from __future__ import annotations

from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# ------------------------------------------------------------------
#  Default arguments
# ------------------------------------------------------------------
default_args = {
    "owner": "factorpulse",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ------------------------------------------------------------------
#  DAG definition
# ------------------------------------------------------------------
with DAG(
    dag_id="feast_materialize",
    default_args=default_args,
    description="Incremental Feast materialization to Redis online store",
    schedule_interval="@hourly",
    start_date=days_ago(1),
    catchup=False,
    tags=["feature-store"],
) as dag:

    materialize = BashOperator(
        task_id="materialize",
        bash_command=(
            'cd /opt/feast && feast materialize-incremental '
            '"$(date -u +\\"%Y-%m-%dT%H:%M:%S\\")"'
        ),
    )
