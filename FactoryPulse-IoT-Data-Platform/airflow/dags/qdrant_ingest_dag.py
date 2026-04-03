"""
FactoryPulse — Qdrant Vector Ingest DAG
=========================================
Daily job that triggers the FastAPI endpoint (or falls back to a direct
ClickHouse-to-Qdrant ingest) to embed incident reports and upsert them
into the Qdrant vector database for semantic search.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow import DAG
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

def _ingest_vectors(**context):
    """Call the FastAPI Qdrant ingest endpoint to embed and upsert
    incident reports into the Qdrant vector database.

    Falls back to logging a clear error if the API is unreachable so the
    operator can decide whether to run the script manually.
    """
    import requests

    api_url = "http://api:8000/api/v1/qdrant/ingest"

    logger.info("Triggering Qdrant vector ingest via %s", api_url)

    try:
        response = requests.post(api_url, timeout=300)
        response.raise_for_status()
        body = response.json()
        logger.info("Qdrant ingest response: %s", body)
    except requests.ConnectionError:
        logger.error(
            "Could not reach the FastAPI service at %s. "
            "Ensure the 'api' container is running.",
            api_url,
        )
        raise
    except requests.HTTPError as exc:
        logger.error(
            "Qdrant ingest endpoint returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise


# ------------------------------------------------------------------
#  DAG definition
# ------------------------------------------------------------------
with DAG(
    dag_id="qdrant_ingest",
    default_args=default_args,
    description="Embed and upsert incident reports into Qdrant for semantic search",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["vector-db", "semantic-search"],
) as dag:

    ingest_vectors = PythonOperator(
        task_id="ingest_vectors",
        python_callable=_ingest_vectors,
    )
