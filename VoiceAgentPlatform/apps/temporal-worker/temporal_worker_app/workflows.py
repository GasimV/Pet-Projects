from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal_worker_app.activities import (
        archive_session_activity,
        retry_tool_activity,
        summarize_session_activity,
    )


@workflow.defn(name="session-archival")
class SessionArchivalWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> str:
        return await workflow.execute_activity(
            archive_session_activity,
            payload,
            start_to_close_timeout=timedelta(minutes=1),
        )


@workflow.defn(name="post-session-summary")
class PostSessionSummaryWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> dict:
        return await workflow.execute_activity(
            summarize_session_activity,
            payload,
            start_to_close_timeout=timedelta(minutes=1),
        )


@workflow.defn(name="failed-tool-retry")
class FailedToolRetryWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> dict:
        return await workflow.execute_activity(
            retry_tool_activity,
            payload,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
