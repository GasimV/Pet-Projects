from __future__ import annotations

import logging

from temporalio.client import Client

logger = logging.getLogger(__name__)


class DurableWorkflowLauncher:
    def __init__(self, client: Client | None, task_queue: str) -> None:
        self._client = client
        self._task_queue = task_queue

    async def start_post_session(self, payload: dict) -> None:
        if self._client is None:
            return
        try:
            await self._client.start_workflow(
                "session-archival",
                payload,
                id=f"archive-{payload['session_id']}-{payload['turn_id']}",
                task_queue=self._task_queue,
            )
            await self._client.start_workflow(
                "post-session-summary",
                payload,
                id=f"summary-{payload['session_id']}-{payload['turn_id']}",
                task_queue=self._task_queue,
            )
        except Exception:
            logger.exception("Failed to start post-session workflows")

    async def start_tool_retry(self, payload: dict) -> None:
        if self._client is None:
            return
        try:
            await self._client.start_workflow(
                "failed-tool-retry",
                payload,
                id=f"tool-retry-{payload['session_id']}-{payload['turn_id']}",
                task_queue=self._task_queue,
            )
        except Exception:
            logger.exception("Failed to start tool retry workflow")

