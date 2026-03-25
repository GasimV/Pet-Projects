"""
RabbitMQ Worker — consumes process_document jobs.

Simulates document processing with a chance of failure to demonstrate
retry and dead-letter queue (DLQ) behaviour.
"""

import json
import random
import time

import pika

QUEUE = "process_document"
MAX_RETRIES = 3


def process(ch, method, properties, body):
    task = json.loads(body)
    attempt = (properties.headers or {}).get("x-retry-count", 0)
    print(
        f"[worker] Processing {task['filename']} "
        f"(job={task['job_id'][:8]}… attempt={attempt + 1})"
    )

    # Simulate work
    time.sleep(1)

    # 20% chance of failure to demonstrate retry logic
    if random.random() < 0.2 and attempt < MAX_RETRIES:
        print(f"[worker] FAILED — requeueing (retry {attempt + 1}/{MAX_RETRIES})")
        ch.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                headers={"x-retry-count": attempt + 1},
            ),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    if attempt >= MAX_RETRIES:
        print(f"[worker] Max retries reached — message goes to DLQ")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    print(f"[worker] Done: {task['filename']}")
    ch.basic_ack(delivery_tag=method.delivery_tag)


def run():
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, durable=True, arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": f"{QUEUE}.dlq",
    })
    channel.queue_declare(queue=f"{QUEUE}.dlq", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=process)
    print("[worker] Waiting for jobs… (Ctrl+C to exit)")
    channel.start_consuming()


if __name__ == "__main__":
    run()
