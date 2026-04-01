"""Pydantic models for API Gateway request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    use_tools: bool = Field(True, description="Whether to enable tool calling")
    use_rag: bool = Field(True, description="Whether to enable RAG retrieval")


class ToolCallInfo(BaseModel):
    tool_name: str
    arguments: str = ""
    result: str = ""


class ChatResponse(BaseModel):
    session_id: str
    content: str
    sources: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    agent_service: bool
    environment: str
    llm_backend: str
