# Voice Agent Platform

Local-first monorepo for an English-only realtime AI voice assistant that can be themed as:
- starship onboard assistant
- Iron-Man-style robotic suit assistant
- robotic home-on-wheels assistant
- UGV / robotic vehicle assistant

## What Is Implemented
- Event-driven realtime control plane in `apps/session-orchestrator`
- Separate STT, RAG, LLM, TTS, tool, gateway, livekit-agent, and Temporal worker services
- gRPC contracts in `libs/proto/voice_platform`
- Redis hot-state/event fanout, PostgreSQL metadata store, Qdrant retrieval store
- Ollama-default LLM provider abstraction with optional vLLM path
- faster-whisper STT service with CPU/GPU profile selection
- LlamaIndex + Qdrant RAG service over local `knowledge/` domain packs
- Tool calling surface through gRPC plus an MCP server entrypoint
- Docker Compose local stack, Kubernetes manifests, and a Helm chart skeleton
- Browser UI with mic capture, transcripts, assistant stream, and stage timings
- Temporal workflows for archival, post-session summary, and failed tool retry

## Honest Deviations
- The verified local MVP audio loop uses browser mic capture to raw PCM over WebSocket into the gateway, then gRPC into the orchestrator. LiveKit server/token plumbing and a `livekit-agent` service are included, but the full browser-to-LiveKit-to-agent audio bridge is left as the production insertion point.
- Ollama is the default LLM/embedding runtime, but not the TTS runtime. Community Ollama-hosted TTS models exist, yet the standard Ollama API surface does not provide a clean audio-output contract for this stack, so the project falls back to `espeak-ng` for local TTS.

## Repo Layout
```text
apps/
  gateway/
  livekit-agent/
  session-orchestrator/
  stt-service/
  rag-service/
  llm-service/
  tts-service/
  tool-service/
  web-ui/
  temporal-worker/
libs/
  proto/
  shared-config/
  shared-events/
  shared-observability/
deploy/
  docker/
  k8s/
  helm/
docs/
knowledge/
scripts/
tests/
```

## Local Hardware Outcome
Run the detection script first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/detect_hardware.ps1
```

On the inspected host in this workspace, the generated profile is `local-hybrid`:
- NVIDIA Quadro M1200, 4 GiB VRAM, compute capability 5.0
- Docker Desktop uses WSL2
- GPU is visible in WSL2/Docker
- vLLM disabled by default because the GPU is too constrained for a safe default path

See `docs/hardware-report.md` and `.env.generated`.

## Quick Start
1. Create the Python environment and install dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python scripts\generate_protos.py
```

2. Bootstrap Ollama models:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_models.ps1
```

3. Start the stack:
```powershell
docker compose up --build
```

4. Open:
- UI: `http://localhost:8080`
- Gateway health: `http://localhost:8080/health/ready`
- Orchestrator health: `http://localhost:8081/health/ready`

## Service Ports
- gateway: `8080`
- livekit-agent: `8091`
- stt-service: `8092` and gRPC `50052`
- llm-service: `8093` and gRPC `50053`
- tts-service: `8094` and gRPC `50054`
- tool-service: `8095` and gRPC `50055`
- rag-service: `8096` and gRPC `50056`
- session-orchestrator: `8081` and gRPC `50051`
- LiveKit: `7880`
- Redis: `6379`
- PostgreSQL: `5432`
- Qdrant: `6333`
- Temporal: `7233`
- Ollama: `11434`

## Tests
```powershell
.\.venv\Scripts\python -m pytest
```

## Tooling
- `scripts/detect_hardware.ps1` and `scripts/detect_hardware.sh`
- `scripts/bootstrap_models.ps1` and `scripts/bootstrap_models.sh`
- `scripts/generate_protos.py`
- `Makefile` for a simple task runner surface

## Next Work
- Replace the WebSocket PCM bridge with a full LiveKit participant bridge in `apps/livekit-agent`
- Add persistent session metadata writes to PostgreSQL
- Add a richer tool planner once the local Ollama model is upgraded beyond the smallest footprint
