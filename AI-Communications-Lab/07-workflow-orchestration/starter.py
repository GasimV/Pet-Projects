"""
Temporal Workflow Starter — kicks off a document processing pipeline.

Run this after the worker is running to start a workflow execution.
"""

import asyncio
import uuid

from temporalio.client import Client

from activities import DocumentInfo
from workflow import DocumentPipeline

TASK_QUEUE = "document-pipeline"


async def main():
    client = await Client.connect("localhost:7233")

    doc = DocumentInfo(
        document_id=str(uuid.uuid4()),
        filename="quarterly_report.pdf",
    )

    print(f"Starting pipeline for {doc.filename} (id={doc.document_id[:8]}...)")

    result = await client.execute_workflow(
        DocumentPipeline.run,
        doc,
        id=f"doc-pipeline-{doc.document_id[:8]}",
        task_queue=TASK_QUEUE,
    )

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
