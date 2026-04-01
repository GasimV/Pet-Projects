# Architecture Diagrams

All diagrams use [PlantUML](https://plantuml.com/). `C1`-`C5` use the [C4 Model](https://c4model.com/) extension, while `C6` uses native PlantUML deployment notation so it can show node, pod, container, networking, and storage details.

## Diagrams

### C1 — System Context (`C1_SystemContext.puml`)
Shows the Local-AIOps-Copilot system from the outside: the platform engineer user, the copilot system boundary, and external dependencies (LLM backends, Docker, infrastructure metrics). This is the highest-level view of what the system does and who interacts with it.

### C2 — Container Diagram (`C2_Container.puml`)
Zooms into the system boundary to show all containers (services and data stores):
- **Application services**: Frontend, API Gateway, Agent Service, RAG Service, MCP Tool Server, Eval Service, Release Controller, Airflow
- **Data stores**: Redis, PostgreSQL, Qdrant, MLflow
- **Observability**: Prometheus, Grafana, Alertmanager, Logstash
- **External**: LLM Backend (pluggable: Mock / Ollama / vLLM / Triton)

Shows communication protocols (gRPC, HTTP, SSE, WebSocket) between all containers.

### C3 — Deployment Diagram (`C3_Deployment.puml`)
Shows the two-machine deployment topology:
- **Dev Machine** (Windows 10, CPU-only): runs `docker-compose.dev.yml` with mock or Ollama LLM backend, no GPU dependency
- **GPU Machine** (Windows 11, RTX 5080): runs `docker-compose.gpu.yml` with vLLM and/or Triton GPU-accelerated inference

Both machines run identical application services — only the inference backend differs.

### C4 — Chat Request Flow (`C4_ChatFlow.puml`)
Sequence diagram showing the end-to-end chat request lifecycle:
1. User types a message in the Streamlit frontend
2. Frontend sends SSE streaming request to API Gateway
3. API Gateway calls Agent Service via gRPC
4. Agent Service retrieves conversation history from Redis
5. Agent routes to RAG (context retrieval) and/or MCP (tool calling)
6. Agent streams LLM tokens back through the chain
7. Also shows the WebSocket bidirectional flow for live events

### C5 — MLOps Pipeline (`C5_MLOpsPipeline.puml`)
Shows the complete blue-green release decision pipeline:
1. **Registration**: Platform engineer registers a green candidate via Release Controller
2. **Evaluation**: Airflow triggers eval-service to compute quality, latency, consistency metrics
3. **Replay**: Side-by-side replay of traffic through blue and green
4. **Drift Detection**: Checks for data/model drift against baseline
5. **Decision**: Release Controller's decision engine evaluates gates and outputs one of: `stay_on_blue`, `switch_to_green`, `rollback_to_blue`, `hold_for_review`
6. **Apply**: Default is recommendation-only (manual approval); can be auto-applied

Shows where metrics, artifacts, and decisions are stored (PostgreSQL, MLflow, Prometheus).

### C6 — Kubernetes Deployment (`C6_KubernetesDeployment.puml`)
Adds a design-level Kubernetes cluster topology for the platform:
- **Cluster control plane**: Kubernetes API server, scheduler, controller manager, etcd
- **Worker nodes**: CPU node pool for application and stateful workloads, optional GPU node pool for `vLLM` and `Triton`
- **Pods and containers**: replica layout for frontend, API Gateway, Agent Service, RAG, MCP, Eval, Release Controller, Airflow, observability, and stateful services
- **Networking**: external load balancer, ingress-nginx, ClusterIP services, kube-proxy, CoreDNS, Pod-to-Pod traffic
- **CNI and policy**: Calico shown as the reference CNI for overlay networking and `NetworkPolicy`
- **Storage**: PVC-backed stateful workloads via CSI and StorageClass

This diagram is intentionally a **reference target deployment** based on the current Helm values and Terraform scaffolding, not a claim that every Kubernetes manifest already exists in the repository.

## Rendering

To render these diagrams:
- **VS Code**: Install the PlantUML extension
- **CLI**: `java -jar plantuml.jar Architecture/*.puml`
- **Online**: Paste contents at [plantuml.com](https://www.plantuml.com/plantuml/uml/)

## Relationship to Implementation

Each diagram directly maps to the codebase:
| Diagram | Implementation |
|---------|---------------|
| C1 System Context | `.env.example`, `shared/config/settings.py` |
| C2 Containers | `services/*/`, `docker-compose.*.yml` |
| C3 Deployment | `docker-compose.dev.yml`, `docker-compose.gpu.yml` |
| C4 Chat Flow | `services/api-gateway/`, `services/agent-service/`, `services/rag-service/` |
| C5 MLOps Pipeline | `services/eval-service/`, `services/release-controller/`, `services/airflow/dags/` |
| C6 Kubernetes Deployment | `infra/helm/values.yaml`, `infra/terraform/main.tf` |
