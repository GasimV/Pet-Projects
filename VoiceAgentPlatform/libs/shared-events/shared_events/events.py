from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    SESSION_STATUS = "session.status"
    TRANSCRIPT_PARTIAL = "transcript.partial"
    TRANSCRIPT_FINAL = "transcript.final"
    RAG_CONTEXT = "rag.context"
    LLM_TOKEN = "llm.token"
    LLM_FINAL = "llm.final"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    TTS_CHUNK = "tts.chunk"
    TTS_STOPPED = "tts.stopped"
    TIMING = "timing"
    ERROR = "error"


class EventEnvelope(BaseModel):
    event_type: EventType
    session_id: str
    turn_id: str
    sequence_id: int = 0
    request_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TimingBreakdown(BaseModel):
    stage: str
    started_at_ms: int
    completed_at_ms: int
    duration_ms: int

