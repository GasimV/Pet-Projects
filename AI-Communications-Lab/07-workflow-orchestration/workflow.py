"""
Temporal Workflow — Document Processing Pipeline

Orchestrates the full document ingestion flow:
  upload → parse → chunk → embed → store → notify

Temporal provides:
- Automatic retries with configurable policies
- Step-level visibility and status tracking
- Durable execution (survives worker/server restarts)
- Timeout handling at workflow and activity level
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        DocumentInfo,
        chunk_document,
        embed_chunks,
        notify_completion,
        parse_document,
        store_embeddings,
    )


@workflow.defn
class DocumentPipeline:
    @workflow.run
    async def run(self, doc: DocumentInfo) -> str:
        workflow.logger.info(f"Starting pipeline for {doc.filename}")

        # Step 1: Parse
        doc = await workflow.execute_activity(
            parse_document,
            doc,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
            ),
        )

        # Step 2: Chunk
        doc = await workflow.execute_activity(
            chunk_document,
            doc,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 3: Embed
        doc = await workflow.execute_activity(
            embed_chunks,
            doc,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        # Step 4: Store
        store_id = await workflow.execute_activity(
            store_embeddings,
            doc,
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 5: Notify
        result = await workflow.execute_activity(
            notify_completion,
            doc,
            start_to_close_timeout=timedelta(seconds=10),
        )

        workflow.logger.info(f"Pipeline finished: {result}")
        return result
