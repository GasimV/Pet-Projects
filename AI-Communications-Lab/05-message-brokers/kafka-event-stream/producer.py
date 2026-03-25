"""
Kafka Producer — publishes document_uploaded events.

Simulates a document ingestion system where uploads trigger multiple
independent downstream consumers (analytics, ingestion, notification).
"""

import json
import time
import uuid

from confluent_kafka import Producer

BROKER = "localhost:9092"
TOPIC = "document_events"


def delivery_report(err, msg):
    if err:
        print(f"  [FAIL] {err}")
    else:
        print(f"  [OK] partition={msg.partition()} offset={msg.offset()}")


def publish_upload(filename: str, user: str = "demo-user"):
    producer = Producer({"bootstrap.servers": BROKER})

    event = {
        "event_type": "document_uploaded",
        "document_id": str(uuid.uuid4()),
        "filename": filename,
        "user": user,
        "timestamp": time.time(),
    }

    producer.produce(
        TOPIC,
        key=event["document_id"],
        value=json.dumps(event),
        callback=delivery_report,
    )
    producer.flush()
    print(f"Published: {event['event_type']} — {filename}")
    return event


if __name__ == "__main__":
    sample_files = ["report.pdf", "meeting_notes.docx", "data.csv"]
    for f in sample_files:
        publish_upload(f)
        time.sleep(0.5)
