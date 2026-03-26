from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator

import grpc

from session_orchestrator_app.clients import ServiceClients
from session_orchestrator_app.temporal_client import DurableWorkflowLauncher
from shared_events.bus import EventPublisher
from shared_events.events import EventEnvelope, EventType
from voice_platform import common_pb2, llm_pb2, session_pb2, session_pb2_grpc


class LiveSession:
    def __init__(
        self,
        clients: ServiceClients,
        publisher: EventPublisher | None,
        default_domain: str,
        workflow_launcher: DurableWorkflowLauncher,
    ) -> None:
        self._clients = clients
        self._publisher = publisher
        self._default_domain = default_domain
        self._workflow_launcher = workflow_launcher
        self._outgoing: asyncio.Queue[session_pb2.SessionMessage | None] = asyncio.Queue()
        self._audio_buffer = bytearray()
        self._sample_rate = 16000
        self._sequence = 0
        self._domain = default_domain
        self._session_id = str(uuid.uuid4())
        self._turn_id = "turn-0"
        self._active_response_task: asyncio.Task | None = None
        self._partial_task: asyncio.Task | None = None

    async def close(self) -> None:
        for task in (self._partial_task, self._active_response_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _emit(self, event_type: str, text: str = "", *, audio: bytes = b"", is_final: bool = False, payload: dict | None = None) -> None:
        self._sequence += 1
        meta = common_pb2.RequestMeta(
            session_id=self._session_id,
            turn_id=self._turn_id,
            request_id=f"{self._session_id}:{self._sequence}",
            domain=self._domain,
        )
        message = session_pb2.SessionMessage(
            event=session_pb2.UiEvent(
                meta=meta,
                event_type=event_type,
                text=text,
                audio=audio,
                is_final=is_final,
                sequence_id=self._sequence,
                mime_type="audio/wav" if audio else "",
                json_payload=json.dumps(payload or {}),
            )
        )
        await self._outgoing.put(message)
        if self._publisher is not None:
            await self._publisher.publish(
                EventEnvelope(
                    event_type=EventType(event_type),
                    session_id=self._session_id,
                    turn_id=self._turn_id,
                    sequence_id=self._sequence,
                    request_id=meta.request_id,
                    payload=payload or {"text": text},
                )
            )

    async def _emit_timing(self, stage: str, started: float) -> None:
        now = time.time()
        await self._emit(
            EventType.TIMING.value,
            payload={
                "stage": stage,
                "started_at_ms": int(started * 1000),
                "completed_at_ms": int(now * 1000),
                "duration_ms": int((now - started) * 1000),
            },
        )

    async def _run_partial_stt(self) -> None:
        if not self._audio_buffer:
            return
        meta = common_pb2.RequestMeta(
            session_id=self._session_id,
            turn_id=self._turn_id,
            request_id=str(uuid.uuid4()),
            domain=self._domain,
        )
        try:
            text, _ = await self._clients.transcribe(
                meta, bytes(self._audio_buffer), self._sample_rate, False
            )
        except Exception:
            return
        if text:
            await self._emit(EventType.TRANSCRIPT_PARTIAL.value, text=text, payload={"confidence": 0.5})

    async def _tts_worker(self, meta, queue: asyncio.Queue[str | None]) -> None:
        while True:
            chunk = await queue.get()
            if chunk is None:
                return
            audio = await self._clients.synthesize(meta, chunk, "en-us")
            if audio:
                await self._emit(EventType.TTS_CHUNK.value, text=chunk, audio=audio, payload={"text": chunk})

    async def _run_turn(self, transcript: str) -> None:
        try:
            meta = common_pb2.RequestMeta(
                session_id=self._session_id,
                turn_id=self._turn_id,
                request_id=str(uuid.uuid4()),
                domain=self._domain,
            )
            rag_started = time.time()
            rag_reply = await self._clients.retrieve(meta, transcript, top_k=3)
            await self._emit_timing("rag", rag_started)
            await self._emit(
                EventType.RAG_CONTEXT.value,
                payload={
                    "context": rag_reply.assembled_context,
                    "citations": [
                        {"source": item.source, "excerpt": item.excerpt, "score": item.score}
                        for item in rag_reply.citations
                    ],
                },
            )

            messages = [{"role": "user", "content": transcript}]
            system_prompt = (
                f"You are an English-only assistant themed for the '{self._domain}' domain. "
                "Be concise, grounded, and operationally clear."
            )

            llm_started = time.time()
            first_pass = [
                chunk
                async for chunk in self._clients.stream_generate(
                    meta, messages, system_prompt, rag_reply.assembled_context, True
                )
            ]
            if first_pass and first_pass[0].tool_intent.name:
                intent = first_pass[0].tool_intent
                await self._emit(
                    EventType.TOOL_CALL.value,
                    payload={"name": intent.name, "arguments_json": intent.arguments_json},
                )
                try:
                    tool_result = await self._clients.execute_tool(meta, intent.name, intent.arguments_json)
                except Exception:
                    await self._workflow_launcher.start_tool_retry(
                        {
                            "session_id": self._session_id,
                            "turn_id": self._turn_id,
                            "tool_name": intent.name,
                            "arguments_json": intent.arguments_json,
                        }
                    )
                    raise
                await self._emit(EventType.TOOL_RESULT.value, payload=tool_result)
                messages.append({"role": "tool", "content": json.dumps(tool_result)})
                stream = self._clients.stream_generate(
                    meta, messages, system_prompt, rag_reply.assembled_context, False
                )
            else:

                async def replay():
                    for chunk in first_pass:
                        yield chunk

                stream = replay()

            tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
            tts_task = asyncio.create_task(self._tts_worker(meta, tts_queue))
            accumulated = ""
            sentence_buffer = ""
            async for chunk in stream:
                if chunk.is_final:
                    break
                accumulated += chunk.token
                sentence_buffer += chunk.token
                await self._emit(EventType.LLM_TOKEN.value, text=chunk.token)
                if any(sentence_buffer.rstrip().endswith(marker) for marker in (".", "!", "?")):
                    await tts_queue.put(sentence_buffer.strip())
                    sentence_buffer = ""

            if sentence_buffer.strip():
                await tts_queue.put(sentence_buffer.strip())
            await tts_queue.put(None)
            await tts_task
            await self._emit_timing("llm_total", llm_started)
            await self._emit(EventType.LLM_FINAL.value, text=accumulated, is_final=True)
            await self._workflow_launcher.start_post_session(
                {
                    "session_id": self._session_id,
                    "turn_id": self._turn_id,
                    "transcript": transcript,
                    "assistant_response": accumulated,
                    "domain": self._domain,
                }
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._emit(
                EventType.ERROR.value,
                payload={"stage": "turn", "error": str(exc)},
            )

    async def handle_message(self, message: session_pb2.SessionMessage) -> None:
        if message.HasField("control"):
            control = message.control
            if control.command == "set_domain":
                self._domain = control.value or self._default_domain
            if control.command == "interrupt":
                if self._active_response_task is not None:
                    self._active_response_task.cancel()
                    self._active_response_task = None
                await self._emit(EventType.TTS_STOPPED.value, payload={"reason": "barge-in"})
            return

        if not message.HasField("audio"):
            return

        audio = message.audio
        self._session_id = audio.meta.session_id or self._session_id
        self._sample_rate = audio.sample_rate or self._sample_rate
        self._audio_buffer.extend(audio.pcm)

        if self._partial_task is not None and not self._partial_task.done():
            self._partial_task.cancel()
        self._partial_task = asyncio.create_task(self._run_partial_stt())

        if audio.end_of_turn:
            self._turn_id = audio.meta.turn_id or f"turn-{uuid.uuid4().hex[:8]}"
            stt_started = time.time()
            meta = common_pb2.RequestMeta(
                session_id=self._session_id,
                turn_id=self._turn_id,
                request_id=str(uuid.uuid4()),
                domain=self._domain,
            )
            try:
                transcript, confidence = await self._clients.transcribe(
                    meta, bytes(self._audio_buffer), self._sample_rate, True
                )
            except Exception as exc:
                self._audio_buffer.clear()
                await self._emit(
                    EventType.ERROR.value,
                    payload={"stage": "stt", "error": str(exc)},
                )
                return
            self._audio_buffer.clear()
            await self._emit_timing("stt_final", stt_started)
            await self._emit(
                EventType.TRANSCRIPT_FINAL.value,
                text=transcript,
                is_final=True,
                payload={"confidence": confidence},
            )
            if self._active_response_task is not None:
                self._active_response_task.cancel()
            self._active_response_task = asyncio.create_task(self._run_turn(transcript))

    async def consume(self, request_iterator) -> None:
        try:
            async for message in request_iterator:
                await self.handle_message(message)
        finally:
            await self._outgoing.put(None)

    async def events(self) -> AsyncIterator[session_pb2.SessionMessage]:
        while True:
            item = await self._outgoing.get()
            if item is None:
                return
            yield item


class RealtimeSessionService(session_pb2_grpc.RealtimeSessionOrchestratorServicer):
    def __init__(
        self,
        clients: ServiceClients,
        publisher: EventPublisher | None,
        default_domain: str,
        workflow_launcher: DurableWorkflowLauncher,
    ) -> None:
        self._clients = clients
        self._publisher = publisher
        self._default_domain = default_domain
        self._workflow_launcher = workflow_launcher

    async def Connect(self, request_iterator, context: grpc.aio.ServicerContext):
        session = LiveSession(
            self._clients,
            self._publisher,
            self._default_domain,
            self._workflow_launcher,
        )
        consumer = asyncio.create_task(session.consume(request_iterator))
        try:
            async for event in session.events():
                yield event
        finally:
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass
            await session.close()

    async def Health(self, request: common_pb2.Empty, context: grpc.aio.ServicerContext):
        return common_pb2.HealthReply(status="ok")
