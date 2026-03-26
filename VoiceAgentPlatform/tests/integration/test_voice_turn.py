from __future__ import annotations

import asyncio

import pytest

from session_orchestrator_app.service import LiveSession
from session_orchestrator_app.temporal_client import DurableWorkflowLauncher
from voice_platform import session_pb2


class DemoClients:
    async def transcribe(self, meta, pcm: bytes, sample_rate: int, is_final: bool):
        return ("what can you do", 0.99) if is_final else ("what", 0.5)

    async def retrieve(self, meta, query: str, top_k: int = 3):
        citation = type("Citation", (), {"source": "robotic-suit/manual.md", "excerpt": "list subsystem readiness", "score": 0.9})
        return type("RagReply", (), {"assembled_context": "list subsystem readiness", "citations": [citation]})

    async def execute_tool(self, meta, name: str, arguments_json: str):
        return {"capabilities": ["status", "manual search"]}

    async def synthesize(self, meta, text: str, voice: str):
        return b"RIFFvoice"

    async def stream_generate(self, meta, messages, system_prompt, context, enable_tools):
        if enable_tools:
            intent = type("Intent", (), {"name": "list_capabilities", "arguments_json": "{}"})
            yield type("Chunk", (), {"token": "", "is_final": False, "tool_intent": intent})
            yield type("Chunk", (), {"token": "", "is_final": True, "tool_intent": intent})
            return
        empty = type("Intent", (), {"name": "", "arguments_json": ""})
        yield type("Chunk", (), {"token": "I can report status.", "is_final": False, "tool_intent": empty})
        yield type("Chunk", (), {"token": "", "is_final": True, "tool_intent": empty})


@pytest.mark.asyncio
async def test_one_voice_turn_pipeline():
    session = LiveSession(DemoClients(), None, "robotic-suit", DurableWorkflowLauncher(None, "voice-platform"))
    message = session_pb2.SessionMessage(
        audio=session_pb2.AudioFrame(
            meta={"session_id": "s2", "turn_id": "turn-2", "request_id": "r2", "domain": "robotic-suit"},
            pcm=b"\x00\x00" * 100,
            sample_rate=16000,
            channels=1,
            end_of_turn=True,
            sequence_id=1,
        )
    )
    await session.handle_message(message)
    await asyncio.wait_for(session._active_response_task, timeout=2)  # noqa: SLF001

    seen = []
    while not session._outgoing.empty():  # noqa: SLF001
        item = await session._outgoing.get()  # noqa: SLF001
        if item is not None and item.HasField("event"):
            seen.append(item.event.event_type)

    assert seen[:2] == ["timing", "transcript.final"]
    assert "rag.context" in seen
    assert "tool.call" in seen
    assert "tool.result" in seen
    assert "tts.chunk" in seen
    assert seen[-1] == "llm.final"

