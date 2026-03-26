from __future__ import annotations

import logging

import orjson

from shared_events.events import EventEnvelope

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, redis_client, channel: str) -> None:
        self._redis = redis_client
        self._channel = channel

    async def publish(self, event: EventEnvelope) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.publish(self._channel, event.model_dump_json())
        except Exception:
            logger.exception("Failed to publish session event")


class EventSubscriber:
    def __init__(self, redis_client, channel: str) -> None:
        self._redis = redis_client
        self._channel = channel

    async def iter_events(self):
        if self._redis is None:
            return
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield EventEnvelope.model_validate(orjson.loads(message["data"]))
