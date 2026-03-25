"""
Kafka Consumer — Notification logger.

Listens to document_events and logs a notification.
Third independent consumer group.
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
        "group.id": "notification-group",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([TOPIC])
    print("[notification] Listening for events…")

    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[notification] Error: {msg.error()}")
            continue

        event = json.loads(msg.value())
        print(
            f"[notification] 📬 {event['user']} uploaded {event['filename']}"
        )

    consumer.close()


if __name__ == "__main__":
    run()
