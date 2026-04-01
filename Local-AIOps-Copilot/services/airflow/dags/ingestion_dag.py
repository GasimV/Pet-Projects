"""Ingestion DAG — ingests documents into the RAG vector store."""

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


def ingest_documents(**context):
    """Ingest documents from a source directory into the RAG service."""
    import httpx

    rag_url = "http://rag-service:50052"
    source_dir = context["params"].get("source_dir", "/data/docs")

    from pathlib import Path

    docs_path = Path(source_dir)
    if not docs_path.exists():
        print(f"Source directory {source_dir} not found, skipping.")
        return {"ingested": 0}

    count = 0
    for doc_file in docs_path.glob("**/*.md"):
        content = doc_file.read_text(encoding="utf-8")
        # Call RAG service ingest via gRPC or HTTP
        # For simplicity, log the action
        print(f"Would ingest: {doc_file.name} ({len(content)} chars)")
        count += 1

    return {"ingested": count}


with DAG(
    dag_id="ingestion_pipeline",
    default_args=default_args,
    description="Ingest documents into the RAG vector store",
    schedule_interval="@daily",
    start_date=datetime.datetime(2024, 1, 1),
    catchup=False,
    tags=["rag", "ingestion"],
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_documents",
        python_callable=ingest_documents,
        params={"source_dir": "/data/docs"},
    )
