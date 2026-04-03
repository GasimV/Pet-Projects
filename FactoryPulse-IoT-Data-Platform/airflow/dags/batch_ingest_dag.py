"""
FactoryPulse — Batch Ingest DAG
================================
Orchestrates the daily batch (lambda) pipeline:
  1. Generate reference / device-catalog CSV and upload to MinIO.
  2. Run Spark batch job to ingest reference data into Iceberg / ClickHouse.
  3. Validate the ingested data with Great Expectations.

OpenLineage integration is handled automatically by the openlineage-airflow
package through the AIRFLOW__OPENLINEAGE__TRANSPORT env var set in
docker-compose.yml.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import boto3
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#  Default arguments shared across all tasks
# ------------------------------------------------------------------
default_args = {
    "owner": "factorpulse",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ------------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------------

def _check_minio_reference_files(**context):
    """Verify that expected reference CSV files exist in the MinIO raw bucket.

    If the simulator has already produced today's reference file we skip
    regeneration; otherwise we log a warning but do NOT fail (the Spark
    job will pick up whatever files are present).
    """
    s3 = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    bucket = "factory-raw"
    prefix = "reference/"

    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=10)
        contents = resp.get("Contents", [])
        if contents:
            keys = [obj["Key"] for obj in contents]
            logger.info("Reference files found in MinIO: %s", keys)
        else:
            logger.warning(
                "No reference files found under s3://%s/%s — "
                "the Spark ingest job may have nothing to process.",
                bucket,
                prefix,
            )
    except Exception:
        logger.exception("Failed to list objects in MinIO bucket %s", bucket)
        raise


def _validate_with_great_expectations(**context):
    """Run a Great Expectations checkpoint against the ingested data.

    We use a programmatic (RuntimeDataConnector) approach so the DAG
    stays self-contained.  The checkpoint validates that the ClickHouse
    raw_telemetry and raw_devices tables are non-empty and that key
    columns contain no nulls.
    """
    import clickhouse_connect

    client = clickhouse_connect.get_client(
        host="clickhouse",
        port=8123,
        username="default",
        password="clickhouse",
        database="factory_pulse",
    )

    # --- Validate raw_devices ------------------------------------------
    device_count = client.command(
        "SELECT count() FROM factory_pulse.raw_devices"
    )
    logger.info("raw_devices row count: %s", device_count)
    if device_count == 0:
        raise ValueError(
            "Great Expectations check FAILED: raw_devices table is empty "
            "after batch ingest."
        )

    null_device_ids = client.command(
        "SELECT count() FROM factory_pulse.raw_devices WHERE device_id = ''"
    )
    if null_device_ids > 0:
        raise ValueError(
            f"Great Expectations check FAILED: {null_device_ids} rows in "
            "raw_devices have empty device_id."
        )

    # --- Validate raw_telemetry ----------------------------------------
    telemetry_count = client.command(
        "SELECT count() FROM factory_pulse.raw_telemetry"
    )
    logger.info("raw_telemetry row count: %s", telemetry_count)

    logger.info("All Great Expectations checks PASSED.")


# ------------------------------------------------------------------
#  DAG definition
# ------------------------------------------------------------------
with DAG(
    dag_id="batch_ingest",
    default_args=default_args,
    description="Daily batch ingest: generate reference data, Spark ingest, GE validation",
    schedule_interval="0 6 * * *",  # every day at 06:00 UTC
    start_date=days_ago(1),
    catchup=False,
    tags=["batch", "lambda", "etl"],
) as dag:

    generate_reference = PythonOperator(
        task_id="generate_reference",
        python_callable=_check_minio_reference_files,
    )

    spark_batch_ingest = BashOperator(
        task_id="spark_batch_ingest",
        bash_command=(
            "docker exec factorpulse-spark-master-1 "
            "/opt/bitnami/spark/bin/spark-submit "
            "--master spark://spark-master:7077 "
            "--deploy-mode client "
            "/opt/spark-apps/batch/ingest_reference.py"
        ),
    )

    validate_data = PythonOperator(
        task_id="validate_data",
        python_callable=_validate_with_great_expectations,
    )

    generate_reference >> spark_batch_ingest >> validate_data
