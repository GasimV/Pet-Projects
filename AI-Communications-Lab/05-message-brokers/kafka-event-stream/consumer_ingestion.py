"""
Kafka Consumer — Ingestion trigger.

Listens to document_events and kicks off the RAG ingestion pipeline.
Independent consumer group from analytics.
"""

import json
import signal

from confluent_kafka import Consumer

BROKER = "localhost:9092"
TOPIC = "document_events"

running = True
signal.signal(signal.SIGINT, lambda *_: globals().update(running=False))


def run():
    consumer = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": "ingestion-group",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([TOPIC])
    print("[ingestion] Listening for events…")

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[ingestion] Error: {msg.error()}")
            continue

        event = json.loads(msg.value())
        print(
            f"[ingestion] Triggering RAG pipeline for "
            f"{event['filename']} (id={event['document_id'][:8]}…)"
        )

    consumer.close()


if __name__ == "__main__":
    run()
