"""
Kafka Consumer — Analytics logger.

Listens to document_events and logs analytics data.
Runs in its own consumer group so it processes independently
from other consumers.
"""

import json
import signal
import sys

from confluent_kafka import Consumer

BROKER = "localhost:9092"
TOPIC = "document_events"

running = True


def shutdown(sig, frame):
    global running
    running = False


signal.signal(signal.SIGINT, shutdown)


def run():
    consumer = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": "analytics-group",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([TOPIC])
    print("[analytics] Listening for events…")

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[analytics] Error: {msg.error()}")
            continue

        event = json.loads(msg.value())
        print(
            f"[analytics] {event['event_type']} | "
            f"file={event['filename']} user={event['user']}"
        )

    consumer.close()


if __name__ == "__main__":
    run()
