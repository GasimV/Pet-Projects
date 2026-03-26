# Hardware Profiles

The platform chooses one of three runtime profiles and writes the resolved values to `.env.generated`.

## Profiles
- `local-cpu`: no GPU path, Ollama and faster-whisper run on CPU, vLLM disabled.
- `local-hybrid`: lightweight GPU acceleration for Ollama and faster-whisper, but vLLM stays off because the GPU is too old or too small for a safe default.
- `local-nvidia-wsl2`: NVIDIA GPU is visible through WSL2/Docker and has enough headroom for the optional tiny-model vLLM path.

## Detection Rules
- Collect GPU, CPU, memory, WSL2, and Docker Desktop state from the host.
- Prefer `local-nvidia-wsl2` only when Docker Desktop runs on the WSL2 backend and the NVIDIA GPU is visible in WSL.
- Degrade to `local-hybrid` when the GPU exists but is older or memory-constrained.
- Fall back to `local-cpu` when no supported NVIDIA GPU path is found.

## Commands
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/detect_hardware.ps1`
- Linux/WSL: `bash scripts/detect_hardware.sh`
