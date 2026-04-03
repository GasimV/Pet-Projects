"""
FactoryPulse — Anomaly Scoring DAG
====================================
Runs the Spark batch anomaly-scoring model every 2 hours, then queries
ClickHouse for any new CRITICAL alerts and logs them so downstream
alerting integrations (PagerDuty, Slack, etc.) can pick them up.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  Default arguments
# ------------------------------------------------------------------
default_args = {
    "owner": "factorpulse",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ------------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------------

def _notify_critical_alerts(**context):
    """Query ClickHouse for CRITICAL alerts created in the last 2 hours
    and log each one.  In a production setting this would call a webhook
    (Slack, PagerDuty, etc.).
    """
    import clickhouse_connect

    client = clickhouse_connect.get_client(
        host="clickhouse",
        port=8123,
        username="default",
        password="clickhouse",
        database="factory_pulse",
    )

    query = """
        SELECT alert_id, device_id, alert_type, severity, message,
               metric_name, metric_value, threshold, timestamp
        FROM factory_pulse.raw_alerts
        WHERE severity = 'CRITICAL'
          AND timestamp >= now() - INTERVAL 2 HOUR
        ORDER BY timestamp DESC
        LIMIT 100
    """

    result = client.query(query)
    rows = result.result_rows

    if not rows:
        logger.info("No new CRITICAL alerts in the last 2 hours.")
        return

    logger.warning(
        "Found %d CRITICAL alert(s) in the last 2 hours:", len(rows)
    )
    for row in rows:
        (
            alert_id, device_id, alert_type, severity, message,
            metric_name, metric_value, threshold, timestamp,
        ) = row
        logger.warning(
            "  ALERT %s | device=%s | type=%s | %s=%.2f (threshold=%.2f) | %s | %s",
            alert_id,
            device_id,
            alert_type,
            metric_name,
            metric_value,
            threshold,
            message,
            timestamp,
        )


# ------------------------------------------------------------------
#  DAG definition
# ------------------------------------------------------------------
with DAG(
    dag_id="anomaly_scoring",
    default_args=default_args,
    description="Run Spark anomaly scoring model and notify on CRITICAL alerts",
    schedule_interval="0 */2 * * *",  # every 2 hours
    start_date=days_ago(1),
    catchup=False,
    tags=["batch", "ml", "lambda"],
) as dag:

    run_anomaly_scoring = BashOperator(
        task_id="run_anomaly_scoring",
        bash_command=(
            "docker exec factorpulse-spark-master-1 "
            "/opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--deploy-mode client "
            "/opt/spark-apps/batch/anomaly_scoring.py"
        ),
    )

    notify_alerts = PythonOperator(
        task_id="notify_alerts",
        python_callable=_notify_critical_alerts,
    )

    run_anomaly_scoring >> notify_alerts
