"""
Temporal Worker — hosts workflow and activity implementations.

The worker polls the Temporal server for tasks and executes them.
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import (
    chunk_document,
    embed_chunks,
    notify_completion,
    parse_document,
    store_embeddings,
)
from workflow import DocumentPipeline

TASK_QUEUE = "document-pipeline"


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[DocumentPipeline],
        activities=[
            parse_document,
            chunk_document,
            embed_chunks,
            store_embeddings,
            notify_completion,
        ],
    )

    print(f"[worker] Listening on task queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
