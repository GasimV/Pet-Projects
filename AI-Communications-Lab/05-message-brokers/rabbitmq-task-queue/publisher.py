"""
RabbitMQ Publisher — enqueues process_document jobs.

Each message represents a document processing task. Messages are
persistent and require explicit acknowledgement (at-least-once delivery).
"""

import json
import uuid

import pika

QUEUE = "process_document"


def publish(filename: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()

    # Durable queue survives broker restarts
    channel.queue_declare(queue=QUEUE, durable=True, arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": f"{QUEUE}.dlq",
    })

    # Dead-letter queue for failed messages
    channel.queue_declare(queue=f"{QUEUE}.dlq", durable=True)

    task = {
        "job_id": str(uuid.uuid4()),
        "filename": filename,
        "action": "process_document",
    }

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE,
        body=json.dumps(task),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )
    print(f"[publisher] Enqueued: {filename} (job={task['job_id'][:8]}…)")
    connection.close()


if __name__ == "__main__":
    for f in ["contract.pdf", "invoice.pdf", "memo.docx"]:
        publish(f)
