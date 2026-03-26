# Architecture

## Design Rules
- Realtime orchestration is separate from durable orchestration.
- Model serving is treated as data plane; the session orchestrator is the control plane.
- The pipeline is concurrent and cancellation-aware rather than a single blocking chain.
- Domain packs live in `knowledge/` and are swappable without platform rewrites.

## Realtime Path
1. The browser captures English audio and sends PCM chunks to the gateway over WebSocket.
2. The gateway opens a bidirectional gRPC session stream to the orchestrator.
3. The orchestrator buffers audio per turn and launches non-blocking partial STT snapshots.
4. On finalized turn audio, the orchestrator runs final STT, then RAG.
5. The LLM service streams tokens.
6. The orchestrator emits tokens to the UI immediately and feeds sentence chunks to a concurrent TTS worker.
7. TTS audio chunks stream back to the UI while token generation continues.
8. On interruption, the orchestrator cancels obsolete work and emits a stop event.

## Durable Path
- `session-archival` writes a session artifact after an assistant turn completes.
- `post-session-summary` generates a concise mission-log style summary.
- `failed-tool-retry` is started when a tool execution fails in the realtime path.

## Service Boundaries
- `apps/gateway`: HTTP, WebSocket, SSE, static UI hosting, LiveKit token issuance
- `apps/session-orchestrator`: session lifecycle, turn routing, cancellation, event fanout, Temporal handoff
- `apps/stt-service`: faster-whisper transcription
- `apps/rag-service`: domain ingestion and retrieval with LlamaIndex/Qdrant
- `apps/llm-service`: Ollama-first provider abstraction with optional vLLM mode
- `apps/tts-service`: `espeak-ng` fallback TTS with Ollama TTS probe logic
- `apps/tool-service`: LangChain/MCP-compatible tool surface
- `apps/temporal-worker`: durable workflows and activities
- `apps/livekit-agent`: production insertion point for full LiveKit participant bridging

## Event Model
- Shared UI/debug events are defined in `libs/shared-events/shared_events/events.py`
- Internal RPC contracts are defined in `libs/proto/voice_platform/*.proto`
- Redis pub/sub is used for transient session event fanout
- gRPC is used for internal service-to-service calls

## Runtime Profiles
- `local-cpu`: CPU only
- `local-hybrid`: GPU-assisted tiny-model local stack, vLLM disabled
- `local-nvidia-wsl2`: NVIDIA GPU visible in WSL2/Docker and strong enough for optional tiny-model vLLM

## Theme Packs
- `knowledge/starship`
- `knowledge/robotic-suit`
- `knowledge/robotic-home`
- `knowledge/ugv`

Each domain pack feeds retrieval context and informs the system prompt chosen by the orchestrator.
