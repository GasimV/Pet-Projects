from __future__ import annotations

import asyncio
import logging
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-observability",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

from shared_config.settings import get_settings
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing
from temporal_worker_app.activities import (
    archive_session_activity,
    retry_tool_activity,
    summarize_session_activity,
)
from temporal_worker_app.workflows import (
    FailedToolRetryWorkflow,
    PostSessionSummaryWorkflow,
    SessionArchivalWorkflow,
)

from temporalio.client import Client
from temporalio.worker import Worker

logger = logging.getLogger(__name__)


async def connect_with_retry(target: str, namespace: str) -> Client:
    delay = 2
    while True:
        try:
            return await Client.connect(target, namespace=namespace)
        except Exception as exc:  # pragma: no cover - exercised in containers
            logger.warning(
                "Temporal not ready yet; retrying",
                extra={"target": target, "namespace": namespace, "error": str(exc)},
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 15)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing("temporal-worker", settings.otel_exporter_otlp_endpoint)
    client = await connect_with_retry(settings.temporal_target, settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[SessionArchivalWorkflow, PostSessionSummaryWorkflow, FailedToolRetryWorkflow],
        activities=[archive_session_activity, summarize_session_activity, retry_tool_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
