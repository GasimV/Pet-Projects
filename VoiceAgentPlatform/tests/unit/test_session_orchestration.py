from __future__ import annotations

import asyncio

import pytest

from session_orchestrator_app.service import LiveSession
from session_orchestrator_app.temporal_client import DurableWorkflowLauncher
from voice_platform import session_pb2


class FakeClients:
    async def transcribe(self, meta, pcm: bytes, sample_rate: int, is_final: bool):
        return ("hello control plane", 0.91) if is_final else ("hello", 0.5)

    async def retrieve(self, meta, query: str, top_k: int = 3):
        citation = type("Citation", (), {"source": "starship/ops", "excerpt": "bridge checklist", "score": 0.9})
        return type("RagReply", (), {"assembled_context": "bridge checklist", "citations": [citation]})

    async def execute_tool(self, meta, name: str, arguments_json: str):
        return {"status": "ok"}

    async def synthesize(self, meta, text: str, voice: str):
        return b"RIFFfake"

    async def stream_generate(self, meta, messages, system_prompt, context, enable_tools):
        yield type("Chunk", (), {"token": "Acknowledged.", "is_final": False, "tool_intent": type("Intent", (), {"name": "", "arguments_json": ""})})
        yield type("Chunk", (), {"token": "", "is_final": True, "tool_intent": type("Intent", (), {"name": "", "arguments_json": ""})})


@pytest.mark.asyncio
async def test_live_session_emits_final_transcript_and_response():
    session = LiveSession(FakeClients(), None, "starship", DurableWorkflowLauncher(None, "voice-platform"))
    message = session_pb2.SessionMessage(
        audio=session_pb2.AudioFrame(
            meta={"session_id": "s1", "turn_id": "turn-1", "request_id": "r1", "domain": "starship"},
            pcm=b"\x00\x00" * 100,
            sample_rate=16000,
            channels=1,
            end_of_turn=True,
            sequence_id=1,
        )
    )
    await session.handle_message(message)
    await asyncio.wait_for(session._active_response_task, timeout=2)  # noqa: SLF001

    events = []
    while not session._outgoing.empty():  # noqa: SLF001
        item = await session._outgoing.get()  # noqa: SLF001
        if item is not None and item.HasField("event"):
            events.append(item.event.event_type)

    assert "transcript.final" in events
    assert "llm.final" in events
    assert "tts.chunk" in events
