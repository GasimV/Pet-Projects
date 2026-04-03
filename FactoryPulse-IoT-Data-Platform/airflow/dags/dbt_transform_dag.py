"""
FactoryPulse — dbt Transform DAG
==================================
Runs dbt models and tests against the ClickHouse warehouse every 3 hours
to maintain the curated / mart layers.
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
    dag_id="dbt_transform",
    default_args=default_args,
    description="Run dbt models and tests on ClickHouse warehouse",
    schedule_interval="0 */3 * * *",  # every 3 hours
    start_date=days_ago(1),
    catchup=False,
    tags=["elt", "warehouse", "dbt"],
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/dbt && dbt run --profiles-dir .",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/dbt && dbt test --profiles-dir .",
    )

    dbt_run >> dbt_test
