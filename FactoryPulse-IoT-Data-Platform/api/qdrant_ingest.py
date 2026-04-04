"""
Qdrant Vector Ingestion Script
===============================
Embeds incident reports and maintenance manual entries using
sentence-transformers/all-MiniLM-L6-v2, then upserts them into Qdrant.

Run:  python qdrant_ingest.py
"""

import json
import os
import uuid

import boto3
import clickhouse_connect
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
COLLECTION = os.environ.get("QDRANT_COLLECTION", "incidents")
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET_RAW", "factory-raw")


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        region_name="us-east-1",
    )


def get_ch_client():
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=os.environ.get("CLICKHOUSE_DB", "factory_pulse"),
    )


def load_manuals_from_minio() -> list[dict]:
    """Load incident_manuals.json from MinIO."""
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=MINIO_BUCKET, Key="reference/incident_manuals.json")
        data = json.loads(obj["Body"].read())
        print(f"  Loaded {len(data)} manual entries from MinIO")
        return data
    except Exception as exc:
        print(f"  Warning: Could not load manuals from MinIO: {exc}")
        return []


def load_incidents_from_clickhouse() -> list[dict]:
    """Load incident reports from ClickHouse."""
    try:
        client = get_ch_client()
        result = client.query(
            "SELECT incident_id, device_id, title, description, resolution, severity "
            "FROM raw_incidents ORDER BY created_at DESC LIMIT 1000"
        )
        incidents = []
        for row in result.result_rows:
            text = f"{row[2]}. {row[3]}"
            if row[4]:
                text += f" Resolution: {row[4]}"
            incidents.append(
                {
                    "id": row[0],
                    "device_id": row[1],
                    "title": row[2],
                    "text": text,
                    "severity": row[5],
                    "source": "incident",
                }
            )
        print(f"  Loaded {len(incidents)} incidents from ClickHouse")
        return incidents
    except Exception as exc:
        print(f"  Warning: Could not load incidents from ClickHouse: {exc}")
        return []


def main():
    print("=== Qdrant Vector Ingestion ===")

    # Load data
    manuals = load_manuals_from_minio()
    incidents = load_incidents_from_clickhouse()

    # Prepare documents
    documents = []
    for m in manuals:
        documents.append(
            {
                "id": m.get("id", str(uuid.uuid4())),
                "title": m.get("title", ""),
                "text": m.get("content", m.get("text", "")),
                "device_id": m.get("device_id"),
                "severity": m.get("severity"),
                "source": "manual",
            }
        )
    documents.extend(incidents)

    if not documents:
        print("No documents to ingest. Exiting.")
        return

    # Load embedding model
    model_name = os.environ.get(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    print(f"  Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    # Embed all texts
    texts = [d["text"] for d in documents]
    print(f"  Embedding {len(texts)} documents...")
    embeddings = model.encode(texts, show_progress_bar=True)

    # Connect to Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Create collection if it doesn't exist
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"  Created Qdrant collection: {COLLECTION}")

    # Upsert points
    points = []
    for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
        points.append(
            PointStruct(
                id=i,
                vector=embedding.tolist(),
                payload={
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "text": doc["text"][:1000],  # Truncate long texts in payload
                    "device_id": doc.get("device_id"),
                    "severity": doc.get("severity"),
                    "source": doc["source"],
                },
            )
        )

    # Batch upsert
    BATCH_SIZE = 100
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch)
        print(f"  Upserted batch {i // BATCH_SIZE + 1} ({len(batch)} points)")

    print(f"\nDone. {len(points)} vectors ingested into Qdrant collection '{COLLECTION}'.")


if __name__ == "__main__":
    main()
