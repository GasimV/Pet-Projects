# AI Communications Lab

A production-minded monorepo of small pet projects demonstrating the core
**communication and orchestration patterns** used in modern AI systems.

Built for learning, reuse, and future recall — each project is runnable
independently with clear architecture notes, AI-specific use cases, and
production considerations.

---

## What's Inside

| #  | Folder                        | Technology          | Pattern                                | AI Use Case                                  |
|----|-------------------------------|---------------------|----------------------------------------|----------------------------------------------|
| 01 | `01-http-https/`             | HTTP/HTTPS (REST)   | Request / Response                     | AI inference APIs (chat, embeddings)          |
| 02 | `02-websockets/`             | WebSockets          | Bidirectional real-time                | Agent status UIs, live collaboration          |
| 03 | `03-sse/`                    | Server-Sent Events  | Server → Client streaming              | LLM token streaming                          |
| 04 | `04-grpc/`                   | gRPC + Protobuf     | Internal typed RPC                     | Microservice calls (embed → retrieve)         |
| 05 | `05-message-brokers/`        | Kafka + RabbitMQ    | Event distribution + Job queuing       | RAG ingestion triggers, document processing   |
| 06 | `06-webrtc-voice-ai/`        | WebRTC              | Low-latency peer-to-peer media         | Real-time voice AI assistants                 |
| 07 | `07-workflow-orchestration/`  | Temporal            | Stateful multi-step workflow control   | Document pipelines (parse→chunk→embed→store)  |
| 08 | `08-graphql/`                | GraphQL + Strawberry| Typed query/mutation/sub w/ nesting    | AI conversation + RAG knowledge graph         |

---

## Pattern Comparison

### Core Differences

| Technology   | Direction             | Connection     | Data Format      | Latency     |
|--------------|-----------------------|----------------|------------------|-------------|
| HTTP/REST    | Client ↔ Server       | Stateless      | JSON             | Medium      |
| WebSocket    | Bidirectional         | Persistent     | JSON / Binary    | Low         |
| SSE          | Server → Client       | Persistent     | Text events      | Low         |
| gRPC         | Client ↔ Server       | Persistent (H2)| Protobuf (binary)| Very low    |
| Kafka        | Producer → Consumers  | Decoupled      | Bytes / Avro     | Low-Medium  |
| RabbitMQ     | Publisher → Worker    | Decoupled      | Bytes / JSON     | Low-Medium  |
| WebRTC       | Peer ↔ Peer           | Persistent     | RTP (audio/video)| Ultra-low   |
| Temporal     | Orchestrator → Workers| Durable        | Protobuf         | Variable    |
| GraphQL      | Client ↔ Server (+Sub)| Stateless / WS | JSON over typed schema | Medium |

### When to Use What

```
Need request/response for AI inference?    → HTTP/REST  (01)
Need real-time bidirectional agent UI?     → WebSocket  (02)
Need server-to-client token streaming?     → SSE        (03)
Need fast internal service-to-service?     → gRPC       (04)
Need event fan-out to multiple consumers?  → Kafka      (05)
Need reliable async job processing?        → RabbitMQ   (05)
Need ultra-low latency voice/video AI?     → WebRTC     (06)
Need multi-step pipeline orchestration?    → Temporal   (07)
Need flexible client-shaped queries?       → GraphQL    (08)
```

### AI-Specific Decision Matrix

| Scenario                                | Best Pattern       | Why                                           |
|-----------------------------------------|--------------------|-----------------------------------------------|
| Serve embeddings / completions API      | HTTP/REST          | Stateless, cacheable, universal client support |
| Show agent tool calls live              | WebSocket          | Bidirectional: user can cancel, agent pushes   |
| Stream LLM tokens to browser           | SSE                | Simple, auto-reconnect, HTTP-compatible        |
| Embed → retrieve between microservices | gRPC               | Typed contracts, HTTP/2 multiplexing, fast     |
| Trigger RAG on document upload          | Kafka              | Fan-out, replay, independent consumer groups   |
| Queue PDF parsing for batch processing  | RabbitMQ           | Reliable ack, retries, dead-letter handling    |
| Real-time voice assistant               | WebRTC             | Sub-200ms audio, built-in echo cancellation    |
| Multi-step ingestion pipeline           | Temporal           | Durable execution, step retries, visibility    |
| Expose model catalog + chat + history one endpoint | GraphQL | One typed schema, client picks fields, subs for streams |

---

## Quick Start

```bash
# Clone and set up
git clone https://github.com/GasimV/Pet-Projects/
cd AI-Communications-Lab

# Create virtual environment (Windows)
python -m venv venv
source venv/Scripts/activate

# Run any subproject — each has its own requirements.txt
pip install -r 01-http-https/requirements.txt
uvicorn 01-http-https.server:app --reload --port 8001
```

Each subfolder README has full run instructions.

### Prerequisites

- **Python 3.12+** (for the venv)
- **Ollama** (optional — demos fall back to mock mode)
  - Models: `gemma3:1b`, `bge-m3:latest`
- **Docker Desktop** (for Kafka, RabbitMQ, Qdrant, Temporal)

---

## Repo Structure

```
AI-Communications-Lab/
├── README.md                          ← You are here
├── .gitignore
├── venv/                              ← Python virtual environment
│
├── 01-http-https/                     ← REST API inference gateway
│   ├── server.py
│   ├── requirements.txt
│   └── README.md
│
├── 02-websockets/                     ← Real-time agent chat
│   ├── server.py
│   ├── requirements.txt
│   └── README.md
│
├── 03-sse/                            ← Token streaming
│   ├── server.py
│   ├── requirements.txt
│   └── README.md
│
├── 04-grpc/                           ← AI microservices (embed + retrieve)
│   ├── protos/ai_services.proto
│   ├── generate_proto.py
│   ├── embedding_server.py
│   ├── retrieval_server.py
│   ├── client.py
│   ├── docker-compose.yml             ← Qdrant
│   ├── requirements.txt
│   └── README.md
│
├── 05-message-brokers/
│   ├── kafka-event-stream/            ← Pub/sub event fan-out
│   │   ├── producer.py
│   │   ├── consumer_analytics.py
│   │   ├── consumer_ingestion.py
│   │   ├── consumer_notification.py
│   │   ├── docker-compose.yml
│   │   └── requirements.txt
│   ├── rabbitmq-task-queue/           ← Reliable job processing
│   │   ├── publisher.py
│   │   ├── worker.py
│   │   ├── docker-compose.yml
│   │   └── requirements.txt
│   └── README.md
│
├── 06-webrtc-voice-ai/                ← Voice AI signaling skeleton
│   ├── server.py
│   ├── requirements.txt
│   └── README.md
│
├── 07-workflow-orchestration/         ← Temporal document pipeline
│   ├── activities.py
│   ├── workflow.py
│   ├── worker.py
│   ├── starter.py
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── README.md
│
└── 08-graphql/                        ← GraphQL AI inference + knowledge graph
    ├── server.py                       (FastAPI + Strawberry router + HTML client)
    ├── schema.py                       (types, interface, unions, enums, inputs)
    ├── resolvers.py                    (Query/Mutation/Subscription + DataLoaders)
    ├── data.py                         (in-memory seed data)
    ├── ollama.py                       (gemma4:e2b proxy + mock fallback)
    ├── sample_queries.graphql
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    └── README.md
```

---

## Design Principles

- **Simple over clever** — each demo is minimal and educational
- **Runnable independently** — no cross-project dependencies
- **Mock-first** — demos work without external services (Ollama, Docker)
- **Production-aware** — each README includes production notes
- **Consistent structure** — every folder has the same layout
