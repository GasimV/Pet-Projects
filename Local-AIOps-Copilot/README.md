# Local-AIOps-Copilot

A local-first AIOps assistant, MLOps experimentation platform, and Blue-Green release decision system.

## What It Does

- **Chat with LLM** — conversational AI assistant for infrastructure operations
- **RAG over local docs** — semantic retrieval from your documentation
- **Tool calling (MCP)** — execute operational tools (system info, Prometheus queries, Docker status)
- **Blue-Green release decisions** — automated evaluation, replay testing, drift detection, and release recommendations
- **MLOps pipelines** — Airflow DAGs for ingestion, evaluation, replay, drift, and release decisioning
- **Full observability** — Prometheus metrics, Grafana dashboards, Alertmanager, structured logging

## Architecture

```
Frontend (Streamlit) → API Gateway (FastAPI) → Agent Service (LangGraph)
                                                    ├── RAG Service (Qdrant)
                                                    ├── MCP Tool Server
                                                    └── LLM Backend (pluggable)
                                                         ├── Mock (dev)
                                                         ├── Ollama (dev)
                                                         ├── vLLM (GPU, primary)
                                                         └── Triton (GPU, alternative)
```

See [Architecture/](Architecture/) for full C4 model PlantUML diagrams.

## Two-Machine Setup

| | Dev Machine | GPU Machine |
|---|---|---|
| **OS** | Windows 10 | Windows 11 Pro |
| **CPU** | i7-7700HQ | Intel Core Ultra 9 275HX |
| **GPU** | Quadro M1200 (unused) | RTX 5080 16GB |
| **Compose** | `docker-compose.dev.yml` | `docker-compose.gpu.yml` |
| **LLM Backend** | mock / ollama | vLLM / Triton |
| **Purpose** | Development, debugging | Validation, GPU inference |

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+ (for local testing)
- Git

### Dev Machine (CPU Mode)

```bash
# Clone the repo
git clone <repo-url>
cd Local-AIOps-Copilot

# Create .env from example
cp .env.example .env

# Start all services
docker compose -f docker-compose.dev.yml up --build

# Or use the script:
# bash infra/scripts/dev-up.sh
# PowerShell: .\infra\scripts\dev-up.ps1 -Build
```

Open:
- **Chat UI**: http://localhost:8501
- **API Gateway**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MLflow**: http://localhost:5000
- **Airflow**: http://localhost:8082 (admin/admin)

### GPU Machine (vLLM)

```bash
git clone <repo-url>
cd Local-AIOps-Copilot

cp .env.example .env
# Edit .env: set LLM_BACKEND=vllm, ENVIRONMENT=gpu

# Start with vLLM profile
docker compose -f docker-compose.gpu.yml --profile vllm up --build

# Or use the script:
# bash infra/scripts/gpu-up.sh vllm
# PowerShell: .\infra\scripts\gpu-up.ps1 -Profile vllm -Build
```

### GPU Machine (Triton)

```bash
# Start with Triton profile
docker compose -f docker-compose.gpu.yml --profile triton up --build

# PowerShell: .\infra\scripts\gpu-up.ps1 -Profile triton -Build
```

### Side-by-Side (vLLM + Triton)

```bash
# Run both inference backends simultaneously
docker compose -f docker-compose.gpu.yml --profile gpu-all up --build
```

## Switching Inference Backend

The LLM backend is selected via the `LLM_BACKEND` environment variable:

| Value | Description | Machine |
|-------|-------------|---------|
| `mock` | Deterministic responses, no inference | Dev (default) |
| `ollama` | Local CPU model via Ollama | Dev |
| `vllm` | GPU inference via vLLM (OpenAI-compatible) | GPU (default) |
| `triton` | GPU inference via Triton Inference Server | GPU |

Change at runtime:
```bash
# In .env
LLM_BACKEND=vllm

# Or via environment variable
LLM_BACKEND=triton docker compose -f docker-compose.gpu.yml up
```

All backends expose the same interface (`LLMClient.chat()`, `.stream()`, `.embeddings()`), so the application code never changes.

## Project Structure

```
├── shared/                     # Shared libraries
│   ├── config/                 # Centralized Pydantic settings
│   ├── llm_backend/            # Pluggable LLM abstraction
│   │   ├── base.py             # Abstract LLMClient interface
│   │   ├── mock_client.py      # Deterministic mock backend
│   │   ├── ollama_client.py    # Ollama backend
│   │   ├── vllm_client.py      # vLLM backend (OpenAI API)
│   │   ├── triton_client.py    # Triton Inference Server backend
│   │   ├── comparison.py       # Side-by-side backend comparison
│   │   └── factory.py          # Backend factory
│   ├── grpc_common/protos/     # gRPC proto definitions
│   ├── logging/                # Structured JSON logging
│   └── metrics/                # Prometheus metrics
├── services/
│   ├── api-gateway/            # FastAPI — REST, SSE, WebSocket
│   ├── frontend/               # Streamlit chat UI
│   ├── agent-service/          # LangGraph agent + gRPC server
│   ├── rag-service/            # Qdrant vector store + gRPC
│   ├── mcp-tool-server/        # MCP-compatible operational tools
│   ├── eval-service/           # MLflow evaluation + drift detection
│   ├── release-controller/     # Blue-Green release decision engine
│   └── airflow/dags/           # MLOps pipeline DAGs
├── Architecture/               # PlantUML C4 diagrams
├── infra/
│   ├── docker/                 # Prometheus, Grafana, Logstash configs
│   ├── helm/                   # Kubernetes Helm chart
│   ├── terraform/              # Terraform deployment config
│   ├── triton/                 # Triton model repository
│   └── scripts/                # Startup scripts (.sh + .ps1)
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── smoke/                  # End-to-end smoke tests
├── docker-compose.dev.yml      # CPU-only mode
├── docker-compose.gpu.yml      # GPU mode (vLLM + Triton)
└── .env.example                # Environment configuration template
```

## LLM Backend Comparison Mode

On the GPU machine, you can compare vLLM and Triton side-by-side:

```python
from shared.llm_backend.factory import create_llm_client
from shared.llm_backend.comparison import compare_backends
from shared.config.settings import Settings

vllm_client = create_llm_client(backend="vllm")
triton_client = create_llm_client(backend="triton")

report = await compare_backends(
    client_a=vllm_client,
    client_b=triton_client,
    prompts=["Explain Kubernetes pods", "What is blue-green deployment?"],
)

print(report.summary())
```

## Blue-Green Release Flow

1. **Register** a green candidate: `POST /api/v1/releases`
2. **Evaluate** both candidates via Airflow or API
3. **Replay** traffic comparison: `POST /api/v1/replay`
4. **Detect drift**: `POST /api/v1/drift`
5. **Decide**: `POST /api/v1/releases/decide`

Decision outcomes:
- `stay_on_blue` — green doesn't improve enough
- `switch_to_green` — green passes all quality gates
- `rollback_to_blue` — green fails critical thresholds
- `hold_for_review` — ambiguous results, human review needed

Default mode is **recommendation only** (manual approval required).

## Running Tests

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Unit tests (no services needed)
python -m pytest tests/unit/ -v

# Smoke tests (requires running services)
docker compose -f docker-compose.dev.yml up -d
python -m pytest tests/smoke/ -v -m smoke
```

## GPU Setup (Docker + WSL2)

On the second machine (Windows 11 + RTX 5080):

1. Install Docker Desktop with WSL2 backend
2. Install NVIDIA drivers (latest Game Ready or Studio)
3. Install NVIDIA Container Toolkit in WSL2:
   ```bash
   # Inside WSL2
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   ```
4. Restart Docker Desktop
5. Verify: `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`
6. Start GPU services: `docker compose -f docker-compose.gpu.yml --profile vllm up --build`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Services can't connect | Check Docker network: `docker network ls` |
| Mock backend returns same response | Expected — mock is deterministic by design |
| vLLM OOM | Reduce `--gpu-memory-utilization` in docker-compose.gpu.yml |
| Triton model not loading | Check `infra/triton/model_repository/` config |
| gRPC stubs missing | Run proto compilation (see below) |
| Airflow DAGs not visible | Check volume mount: `./services/airflow/dags` |
| Redis connection error | Service falls back to in-memory store automatically |

### Compiling gRPC Protos

```bash
python -m grpc_tools.protoc \
  -I shared/grpc_common/protos \
  --python_out=shared/grpc_common \
  --grpc_python_out=shared/grpc_common \
  --pyi_out=shared/grpc_common \
  shared/grpc_common/protos/*.proto
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| API Gateway | FastAPI, SSE, WebSocket |
| Agent | LangGraph, gRPC |
| RAG | Qdrant, text-splitters |
| Tools | MCP protocol, FastAPI |
| LLM Inference | Mock, Ollama, vLLM, Triton |
| Memory | Redis |
| Eval/MLOps | MLflow, scikit-learn |
| Release | PostgreSQL, SQLAlchemy |
| Pipelines | Apache Airflow |
| Monitoring | Prometheus, Grafana, Alertmanager |
| Logging | Logstash, structlog |
| Orchestration | Docker Compose |
| IaC | Helm, Terraform (design-level) |
