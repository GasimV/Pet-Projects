# MLOps-LlamaIndex-Lab

A **local-first RAG (Retrieval-Augmented Generation) web application** that demonstrates modern MLOps practices: document ingestion with LlamaIndex, vector search with Qdrant, containerisation with Docker, infrastructure-as-code with Terraform, and CI/CD with GitLab.

> Built as a portfolio / interview-ready project showcasing the intersection of **ML engineering**, **DevOps**, and **software engineering**.

---

## Why This Project Is Useful

| Skill area | What you'll see |
|---|---|
| **RAG fundamentals** | Upload docs → chunk → embed → store → query with source citations |
| **LlamaIndex** | Ingestion pipeline, vector store index, pluggable LLM backend |
| **Docker** | Multi-service compose, production-ready Dockerfile |
| **Terraform** | Local Docker provider managing containers as IaC |
| **GitLab CI/CD** | Lint → test → build → terraform-validate pipeline (fully local) |
| **Clean architecture** | Modular Python, typed code, pydantic settings, FastAPI |

---

## Architecture

```
┌────────────────────────────────┐
│         Browser (UI)           │
│   HTML / CSS / vanilla JS      │
└──────────┬─────────────────────┘
           │ HTTP
┌──────────▼─────────────────────┐
│       FastAPI  (app)           │
│  /api/upload · /api/ingest     │
│  /api/query  · /api/status     │
└──────┬────────────┬────────────┘
       │            │
┌──────▼──────┐ ┌───▼───────────┐
│ LlamaIndex  │ │   Qdrant      │
│ (ingest +   │ │ (vector DB)   │
│  query)     │ │  port 6333    │
└──────┬──────┘ └───────────────┘
       │
┌──────▼──────┐
│  LLM (plug- │
│  gable)     │
│ HF / OpenAI │
│ / Ollama    │
└─────────────┘
```

**Containers overview:**

| Container | Image | Port | Purpose |
|---|---|---|---|
| `llamaindex-app` | Built from `./Dockerfile` | 8000 | FastAPI + LlamaIndex RAG app |
| `llamaindex-qdrant` | `qdrant/qdrant:v1.13.2` | 6333 | Vector database |
| `local-gitlab` | `gitlab/gitlab-ce:17.4.0-ce.0` | 8929 | Local GitLab CE (CI/CD) |
| `local-gitlab-runner` | `gitlab/gitlab-runner:v17.11.0` | — | Executes CI/CD pipeline jobs |

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **RAG framework**: LlamaIndex
- **Embeddings**: BAAI/bge-m3 (HuggingFace, runs locally on CPU)
- **Vector store**: Qdrant (Docker container only — not installed system-wide)
- **LLM**: Pluggable — HuggingFace (default), OpenAI, or Ollama
- **Frontend**: Vanilla HTML/CSS/JS served by FastAPI
- **Containerisation**: Docker, Docker Compose
- **Infrastructure-as-code**: Terraform (Docker provider)
- **CI/CD**: GitLab CE + Runner (fully local via Docker)
- **Config**: pydantic-settings + `.env`

---

## Folder Structure

```
MLOps-LlamaIndex-Lab/
├── app/
│   ├── api/routes.py          # FastAPI endpoint definitions
│   ├── core/config.py         # Pydantic settings from .env
│   ├── core/logging.py        # Structured logger
│   ├── rag/embeddings.py      # BAAI/bge-m3 embedding model
│   ├── rag/ingestion.py       # Parse → chunk → embed → store
│   ├── rag/llm_factory.py     # Pluggable LLM backend factory
│   ├── rag/query_engine.py    # LlamaIndex query engine
│   ├── rag/vector_store.py    # Qdrant client wrapper
│   ├── services/              # Business logic layer
│   ├── ui/templates/          # HTML frontend
│   ├── ui/static/             # CSS + JS
│   └── main.py                # FastAPI entry point
├── data/
│   ├── uploads/               # User-uploaded documents (gitignored)
│   ├── qdrant/                # Qdrant storage volume (gitignored)
│   └── sample_docs/           # Example .txt / .md files
├── infra/
│   ├── terraform/             # main.tf, variables.tf, outputs.tf
│   └── gitlab/                # docker-compose.gitlab.yml + runner setup
├── tests/                     # Pytest test suite
├── scripts/                   # Dev helper scripts
├── Dockerfile
├── docker-compose.yml         # App + Qdrant
├── requirements.txt
├── .env.example
├── .gitignore
├── .gitlab-ci.yml
└── README.md
```

---

## Option A — Run with Python venv (Windows)

This mode runs the Python app directly on your machine, with only Qdrant in Docker.
The app talks to Ollama on the host via `localhost`.

### Prerequisites

- Python 3.10+ installed and on PATH
- Docker Desktop installed and **running**
- Ollama installed on the host with a model pulled (`ollama pull gemma3:1b`)

### Step-by-step

```powershell
# 1. Clone and enter the repo
git clone https://github.com/<your-username>/MLOps-LlamaIndex-Lab.git
cd MLOps-LlamaIndex-Lab

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create your .env from the template
copy .env.example .env
```

Your `.env` should contain (the defaults in `.env.example` already work for venv mode):
```
LLM_PROVIDER=ollama
LLM_MODEL=gemma3:1b
LLM_API_BASE=http://localhost:11434
```

```powershell
# 5. Start Qdrant as a Docker container
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:v1.13.2

# 6. Start the app
python -m app.main

# 7. Open in browser
start http://localhost:8000
```

To stop:
```powershell
# Stop the app: Ctrl+C in the terminal
# Stop Qdrant:
docker stop qdrant && docker rm qdrant
```

### (Optional) Ingest sample documents

```powershell
python scripts/ingest_sample_docs.py
```

---

## Option B — Run with Docker Compose

This mode runs **both** the app and Qdrant in Docker containers. No venv needed.
Ollama still runs on your host — the container reaches it via `host.docker.internal`.

### `LLM_API_BASE` — venv vs Docker

| Mode | `LLM_API_BASE` value | Why |
|---|---|---|
| Python venv (Option A) | `http://localhost:11434` | App runs on the host, same as Ollama |
| Docker Compose (Option B) | `http://host.docker.internal:11434` | App runs in a container; `host.docker.internal` resolves to the host |

The `docker-compose.yml` defaults to `http://host.docker.internal:11434` automatically, so you don't need to change your `.env` — the compose environment variable overrides it.

### Step-by-step

```powershell
# Start everything (builds the app image on first run)
docker compose up --build

# Open in browser
start http://localhost:8000

# Stop everything
docker compose down
```

Uploaded files persist in `data/uploads/` (mounted volume).

---

## Option C — Run with Terraform

Terraform manages the same Docker containers declaratively using the
[kreuzwerker/docker](https://registry.terraform.io/providers/kreuzwerker/docker/latest)
provider. It creates the same resources as Docker Compose — an app container, a Qdrant
container, and a bridge network — but through infrastructure-as-code.

### How Terraform differs from Docker Compose here

| Aspect | Docker Compose | Terraform |
|---|---|---|
| Defined in | `docker-compose.yml` | `infra/terraform/*.tf` |
| State tracking | Docker engine only | `terraform.tfstate` file |
| Config override | `.env` file | `-var` flags or `terraform.tfvars` |
| Image build | Built-in (`build:`) | Via `docker_image` resource `build` block |
| DNS between containers | Service name (`qdrant`) | Container name (`llamaindex-qdrant-tf`) |
| Intended use | Day-to-day local dev | IaC demonstration for portfolio |

### Prerequisites

- Docker Desktop **running**
- Terraform >= 1.0 installed and on PATH
- Ollama running on the host with `gemma3:1b` and `bge-m3` models

### Step-by-step

```powershell
cd infra\terraform

# Initialise the Docker provider (downloads the plugin on first run)
terraform init

# Preview what will be created
terraform plan

# Create the network, pull/build images, and start containers
terraform apply

# Open in browser
start http://localhost:8000
```

After `apply` completes, Terraform prints the app URL, Qdrant URL, and container names.

To tear down:
```powershell
terraform destroy

# Return to project root
cd ..\..
```

### What to expect on first run

1. `terraform init` downloads the `kreuzwerker/docker` provider plugin (~30 MB).
2. `terraform apply` pulls the Qdrant image, builds the app image from the Dockerfile, creates a bridge network, and starts both containers. The first image build takes a few minutes (same as `docker compose up --build`).
3. Subsequent `apply` runs are fast — Terraform detects nothing changed and skips.

### Known limitations vs Compose

- Terraform's Docker provider does not support `depends_on` health checks, so the app container may start before Qdrant is fully ready. The app retries on first connection, so this is rarely an issue.
- The `docker_image` `build` block does not support all Dockerfile build options (e.g., build args, multi-stage target selection). For this project's simple Dockerfile it works fine.
- Container names differ (`-tf` suffix) to avoid collisions if Compose containers still exist.

> **Important**: Use either Docker Compose (Option B) **or** Terraform (Option C) — not both at the same time, since they manage overlapping ports.

---

## Local GitLab CI/CD Setup

This project includes a fully local GitLab CE + Runner setup so you can run real CI/CD pipelines entirely on your machine using Docker Desktop.

### Prerequisites

- Docker Desktop **running**
- At least **6 GB RAM** allocated to Docker Desktop (Settings → Resources → Memory)

### 1. Start GitLab and Runner

```powershell
docker compose -f infra/gitlab/docker-compose.gitlab.yml up -d
```

### 2. Wait for GitLab to boot

First boot takes **3–5 minutes** (sometimes longer). Check readiness:

```powershell
docker logs -f local-gitlab
```

GitLab is ready when you see lines like:
```
==> /var/log/gitlab/puma/puma_stdout.log <==
* Listening on http://0.0.0.0:8080
```

Or simply keep refreshing `http://localhost:8929` until the login page appears.

### 3. Log in

| Field | Value |
|---|---|
| URL | `http://localhost:8929` |
| Username | `root` |
| Password | `P@ssw0rd1234!` |

### 4. Create a project in GitLab

1. Click **"New project"** → **"Create blank project"**.
2. Name it `MLOps-LlamaIndex-Lab`. Set visibility to **Private** or **Public**.
3. Uncheck "Initialize repository with a README" (you already have one).
4. Click **Create project**.

### 5. Configure the project for CI/CD

This project lives inside a parent Git repository, so two settings must be adjusted after creating the project:

1. **Disable Auto DevOps** — Go to **Admin Area** → **Settings** → **CI/CD** → **Auto DevOps** → uncheck **"Default to Auto DevOps pipeline"** → **Save changes**.
2. **Set CI config path** — Go to the project → **Settings** → **CI/CD** → **General pipelines** → set **CI/CD configuration file** to `MLOps-LlamaIndex-Lab/.gitlab-ci.yml` → **Save changes**.

> Without these settings, pipelines will fail with "Pipeline cannot be run. Review the workflow:rules configuration."

### 6. Push this repo to local GitLab

```powershell
# Add the local GitLab remote
git remote add gitlab http://localhost:8929/root/mlops-llamaindex-lab.git

# Push (enter root / P@ssw0rd1234! when prompted)
git push gitlab master
```

### 7. Create a runner token

1. In GitLab, go to **Admin Area** (wrench icon in the top bar) → **CI/CD** → **Runners**.
2. Click **"New instance runner"**.
3. Select **Linux** as the platform, add any tags you like (or leave empty), check **"Run untagged jobs"**.
4. Click **"Create runner"**.
5. Copy the displayed **runner authentication token** (starts with `glrt-`).

### 8. Register the runner

In **Git Bash**, **WSL**, or any bash-compatible shell on Windows:

```bash
bash infra/gitlab/register-runner.sh <YOUR_RUNNER_TOKEN>
```

For example:
```bash
bash infra/gitlab/register-runner.sh glrt-xxxxxxxxxxxxxxxxxxxx
```

The registration script configures the runner with:
- **Docker executor** using `python:3.11-slim` as the default image
- **`--clone-url http://local-gitlab`** so CI job containers clone via Docker network (not `localhost`)
- **`--docker-network-mode gitlab-network`** so job containers can reach GitLab

### 9. Trigger the first pipeline

Push a commit (or go to the project → **Build** → **Pipelines** → **Run pipeline**).

The pipeline runs four stages defined in `.gitlab-ci.yml`:

| Stage | Job | What it does |
|---|---|---|
| `lint` | `lint` | Runs `ruff check` on `app/` and `tests/` |
| `test` | `test` | Installs lightweight deps (`requirements-docker.txt` + pytest) and runs `pytest` |
| `build` | `build` | Builds the Docker image via Docker socket binding (master/main only) |
| `infra` | `terraform-validate` | Validates Terraform config formatting |

> **CI vs local runtime:** The pipeline validates code quality, runs unit tests, and builds the Docker image — it does **not** run the full RAG pipeline. There is no Ollama, no Qdrant, and no LLM inference in CI. The test stage uses the lightweight `requirements-docker.txt` (no torch / HuggingFace), so tests complete in seconds rather than minutes.

### 10. Stop GitLab when done

```powershell
docker compose -f infra/gitlab/docker-compose.gitlab.yml down
```

To also remove GitLab data (full reset):
```powershell
docker compose -f infra/gitlab/docker-compose.gitlab.yml down -v
```

> **Note:** After a full reset (`-v`), you must repeat steps 4–8 (create project, configure settings, push, register runner).

### Troubleshooting — Local GitLab

| Issue | Fix |
|---|---|
| GitLab login page doesn't appear | Wait 3–5 min on first boot. Run `docker logs -f local-gitlab` to watch progress. |
| "Pipeline cannot be run" | Disable Auto DevOps (Admin → Settings → CI/CD) and set the CI config path to `MLOps-LlamaIndex-Lab/.gitlab-ci.yml` (project → Settings → CI/CD → General pipelines). |
| Port 8929 already in use | Change the port in `infra/gitlab/docker-compose.gitlab.yml` (e.g., `"8930:80"`). |
| Runner can't reach GitLab | Both containers must be on `gitlab-network`. The runner connects via `http://local-gitlab` (Docker internal DNS). |
| CI jobs fail to clone repo | Ensure the runner was registered with `--clone-url http://local-gitlab`. Check `infra/gitlab/runner/config.toml` for `clone_url = "http://local-gitlab"`. |
| Build stage fails (`docker` command errors) | The build uses Docker socket binding (not DinD). Verify `infra/gitlab/runner/config.toml` includes `"/var/run/docker.sock:/var/run/docker.sock"` in the `volumes` array. |
| Out of memory / slow | GitLab CE is resource-heavy. Allocate at least **6 GB RAM** to Docker Desktop (Settings → Resources). |
| `docker exec` errors on Windows CMD | Use **Git Bash** or **PowerShell** for the runner registration script. |

---

## Running Tests

```powershell
python -m pytest tests/ -v
```

Expected output:
```
tests/test_config.py::test_default_settings PASSED
tests/test_config.py::test_upload_path_is_absolute PASSED
tests/test_config.py::test_project_root_exists PASSED
tests/test_document_service.py::test_supported_extensions_include_common_types PASSED
tests/test_health.py::test_health_returns_ok PASSED
tests/test_health.py::test_index_page_loads PASSED

6 passed
```

---

## How the RAG Pipeline Works

1. **Upload** — User sends files via the web UI or `POST /api/upload`.
2. **Ingest** — `POST /api/ingest` triggers:
   - Parsing (.txt, .md, .pdf, .docx)
   - Chunking via `SentenceSplitter` (configurable size/overlap)
   - Embedding with `BAAI/bge-m3`
   - Storage in Qdrant
3. **Query** — `POST /api/query` triggers:
   - Query embedding
   - Top-k similarity search in Qdrant
   - LLM generates an answer grounded in retrieved chunks
4. **Response** — Answer + source chunks with filenames and relevance scores.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/status` | Index stats, provider info |
| `POST` | `/api/upload` | Upload documents (multipart) |
| `GET` | `/api/documents` | List uploaded files |
| `POST` | `/api/ingest` | Run ingestion pipeline |
| `POST` | `/api/query` | Ask a question (`{"question": "..."}`) |

Interactive API docs (Swagger): **http://localhost:8000/docs**

---

## Configuration

All settings are controlled via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `huggingface`, `openai`, or `ollama` |
| `LLM_MODEL` | `gemma3:1b` | Model identifier |
| `LLM_API_KEY` | _(empty)_ | API key for cloud providers |
| `LLM_API_BASE` | `http://localhost:11434` | Ollama endpoint (use `http://host.docker.internal:11434` in Docker) |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace embedding model |
| `QDRANT_HOST` | `localhost` | Qdrant hostname (`qdrant` inside Docker) |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `CHUNK_SIZE` | `512` | Chunk size in tokens |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |

---

## Switching LLM Providers

### Ollama (recommended for local use)

1. Install [Ollama](https://ollama.com/) and pull a model:
   ```powershell
   ollama pull gemma3:1b
   ```
2. Set in `.env`:
   ```
   LLM_PROVIDER=ollama
   LLM_MODEL=gemma3:1b
   LLM_API_BASE=http://localhost:11434
   ```

### OpenAI

Set in `.env`:
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
```

---

## Future Improvements

- [ ] Streaming responses via WebSocket / SSE
- [ ] User authentication
- [ ] Multi-collection support
- [ ] Conversation memory / chat history
- [ ] GPU-accelerated embedding on Windows
- [ ] Kubernetes deployment manifests
- [ ] Model evaluation metrics (RAGAS, etc.)
- [ ] Upload progress bar with async workers

---

## License

This project is intended for educational and portfolio use. Feel free to fork and adapt.
