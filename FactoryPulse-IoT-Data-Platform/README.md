# FactoryPulse — IoT Data Engineering Platform

A fully local, open-source, Dockerised IoT data engineering platform that demonstrates modern data architecture patterns: **batch + streaming**, **ETL + ELT**, **Data Lake + Lakehouse + Warehouse**, **Lambda + Kappa**, feature stores, vector search, data quality, lineage tracking, and ML experiment management.

<a id="contents"></a>
## Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [IoT Domain](#iot-domain)
- [Data Model](#data-model)
- [Flink Alternative](#flink-alternative-kappa-architecture)
- [Project Structure](#project-structure)
- [Makefile Commands](#makefile-commands)
- [Lineage Tracking](#lineage-tracking)
- [Monitoring](#monitoring)
- [Runbook](#runbook)
- [License](#license)

<a id="architecture-overview"></a>
## Architecture Overview

```
┌───────────────┐
│ IoT Simulator │──→ Kafka ──→ Spark Structured Streaming ──→ Iceberg/MinIO
│  (10 devices) │                                 │
└──────┬────────┘                                 └──────────────→ ClickHouse
       │                                                        (Speed Layer)
       │
       └──→ MinIO (CSV/Parquet) ──→ Spark Batch ──→ Iceberg ──→ ClickHouse
                                                                       │
                                           dbt-core (ELT) ◄───────────┘
                                               │
                       ┌───────────────────────┼───────────────────┐
                       ▼                       ▼                   ▼
                Feast + Redis          ClickHouse Marts      Qdrant (Vectors)
               (Feature Store)         (Analytics)         (Semantic Search)
                       │                       │                   │
                       └───────────────────────┼───────────────────┘
                                               ▼
                                          FastAPI  ◄── Prometheus ──→ Grafana
                                         (Serving)
```

### Architecture Patterns Demonstrated

| Pattern | Implementation |
|---------|---------------|
| **Lambda Architecture** | Batch layer (Spark Batch → Iceberg → ClickHouse) + Speed layer (Spark Structured Streaming → Iceberg + ClickHouse) merge at the serving layer (FastAPI) |
| **Kappa Architecture** | Flink alternative — all processing through a single stream pipeline (use `make up-flink`) |
| **ETL** | Spark reads raw data, transforms, loads into Iceberg (extract-transform-load) |
| **ELT** | dbt-core transforms data already loaded in ClickHouse (extract-load-transform) |
| **Data Lake** | MinIO stores raw CSV, Parquet, and JSON files |
| **Lakehouse** | Apache Iceberg on MinIO provides ACID transactions, schema evolution, time travel |
| **Data Warehouse** | ClickHouse OLAP engine with dimensional models (star schema via dbt) |
| **Feature Store** | Feast with ClickHouse offline store → Redis online store |
| **Vector DB** | Qdrant stores sentence-transformer embeddings for semantic search |
| **Data Quality** | Great Expectations validates telemetry against defined expectations |
| **Data Lineage** | Marquez/OpenLineage tracks pipeline lineage via Airflow integration |
| **Distributed Processing** | Spark (batch + streaming) and Flink (streaming) |

[Back to Contents](#contents)

<a id="tech-stack"></a>
## Tech Stack

| Layer | Technology |
|-------|-----------|
| Message Broker | Apache Kafka (Confluent) + Zookeeper |
| Object Storage | MinIO (S3-compatible) |
| Table Format | Apache Iceberg |
| Batch Processing | Apache Spark 3.5 |
| Stream Processing | Spark Structured Streaming / Apache Flink 1.18 |
| Data Warehouse | ClickHouse |
| Transformations | dbt-core + dbt-clickhouse |
| Feature Store | Feast + Redis |
| Vector Database | Qdrant |
| API | FastAPI |
| Orchestration | Apache Airflow |
| Data Quality | Great Expectations |
| Data Lineage | Marquez (OpenLineage) |
| ML Tracking | MLflow |
| Monitoring | Prometheus + Grafana |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (CPU) |

[Back to Contents](#contents)

<a id="quick-start"></a>
## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- GNU Make (`make`) — or `mingw32-make` on Windows (ships with MSYS2/MinGW)
- 16 GB RAM recommended (8 GB minimum)
- ~15 GB disk space

### 1. Start the Platform

```bash
# Clone and enter the repo
cd FactoryPulse-IoT-Data-Platform

# Copy env file and start all services
make up                  # Linux / macOS / Git Bash
mingw32-make up          # Windows (cmd/PowerShell with MinGW)
```

This starts the infrastructure and simulator stack: Kafka, MinIO, Iceberg, Spark, ClickHouse, Redis, Qdrant, Airflow, FastAPI, Marquez, MLflow, Prometheus, Grafana, and the IoT simulator.

`make up` does not fully execute the processing pipeline by itself. To populate the warehouse, alerts, vectors, and dbt models end-to-end, run `make demo` or the individual Spark/dbt commands below.

### 2. Run the Full Demo

```bash
make demo                # Linux / macOS / Git Bash
mingw32-make demo        # Windows with MinGW
```

This runs the entire pipeline end-to-end:
1. Starts all services
2. Generates batch reference data (devices, historical telemetry, manuals)
3. Runs Spark batch ingest (batch layer)
4. Starts Spark Structured Streaming (speed layer)
5. Runs anomaly scoring
6. Runs dbt transformations
7. Ingests vectors into Qdrant
8. Validates data quality
9. Queries the API

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| FastAPI Docs | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / admin |
| Airflow | http://localhost:8082 | admin / admin |
| Spark Master UI | http://localhost:8080 | — |
| Spark Job UI | http://localhost:4040 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| MLflow | http://localhost:5050 | — |
| Marquez (Lineage) | http://localhost:3001 | — |
| ClickHouse HTTP | http://localhost:8123 | — |
| Qdrant Dashboard | http://localhost:6333/dashboard | — |
| Prometheus | http://localhost:9090 | — |
| Iceberg REST | http://localhost:8181 | — |

### 4. What To Expect In These Services

This project is primarily an architecture demo stack, not a polished UI-heavy app. Several of these services are infrastructure or control-plane tools, so "mostly empty" is expected unless you specifically drive data or workflows through them.

What should usually have visible content:

- **FastAPI Docs** — should show working endpoints.
- **Grafana** — should show metrics and dashboards after the pipeline has been running for a bit; refresh if needed.
- **Spark Job UI** — only looks interesting while jobs are actively running; this is the main place to watch streaming activity.
- **MLflow** — should show anomaly-scoring runs if `make spark-anomaly` has been run.
- **Qdrant Dashboard** — should at least show the `incidents` collection.
- **Prometheus** — should show targets and metrics, but it is still a technical UI rather than a business dashboard.

What is often sparse by design:

- **Airflow** — usually looks empty unless you trigger DAGs inside Airflow itself. This repo does not depend on Airflow runs for the main demo flow.
- **Marquez** — may stay mostly empty unless lineage events are emitted through Airflow or DAG execution.
- **ClickHouse HTTP** — this is an HTTP interface, not a dashboard.
- **Iceberg REST** — this is an API endpoint, not a browser UI.

If you want to see more happen in the stack:

```bash
mingw32-make spark-anomaly
mingw32-make dbt-run
mingw32-make qdrant-ingest
mingw32-make ge-validate
```

If you want the full end-to-end demo again:

```bash
mingw32-make demo
```

If your goal is interactive exploration, the most useful browser entry points are:

- FastAPI Docs for API behavior
- Grafana for metrics and dashboards
- Spark UI while streaming is running
- MLflow for anomaly-scoring runs
- Qdrant Dashboard for vectors and collections

[Back to Contents](#contents)

<a id="iot-domain"></a>
## IoT Domain

### Simulated Factory Sensors

The simulator generates telemetry from 10 factory devices across 5 types:

| Device Type | Metrics | Anomaly Signals |
|-------------|---------|-----------------|
| CNC_Mill | temperature, vibration, rpm | Overheating, excessive vibration |
| Hydraulic_Press | pressure, temperature, power | Over-pressure, high temp |
| Conveyor | vibration, rpm, power_usage | Belt vibration, motor strain |
| Compressor | pressure, temperature, humidity | Pressure drop, overheating |
| Welding_Robot | temperature, power, vibration | Electrode wear, power spikes |

### Data Produced

- **Streaming telemetry** → Kafka → Spark/Flink → Iceberg + ClickHouse (every 2 seconds)
- **Batch reference files** → MinIO (devices.csv, historical Parquet, incident_manuals.json)
- **Alerts** → ClickHouse (anomaly scoring produces CRITICAL/WARNING/NORMAL)
- **Semantic search documents** → Qdrant (maintenance manuals by default, incident text when available)

### Anomaly Scoring (Rule-Based)

| Condition | Score |
|-----------|-------|
| temperature > 95°C | +30 |
| vibration > 3.0 mm/s | +25 |
| pressure > 250 or < 50 bar | +20 |
| power_usage > 90 kW | +15 |
| error_code present | +10 |

Classification: **CRITICAL** (≥50), **WARNING** (≥30), **NORMAL** (<30)

[Back to Contents](#contents)

<a id="data-model"></a>
## Data Model

### ClickHouse Schema (factory_pulse database)

#### Raw Layer (landing)
- `raw_telemetry` — sensor readings (partitioned by day, ordered by device_id + timestamp)
- `raw_devices` — device reference/dimension (ReplacingMergeTree)
- `raw_alerts` — anomaly alerts (partitioned by day)
- `raw_incidents` — incident reports with free-text descriptions

#### Staging (dbt views)
- `stg_telemetry` — typed telemetry with `reading_hour`
- `stg_devices` — devices with computed `days_since_maintenance`
- `stg_alerts` — cleaned alerts

#### Intermediate (dbt views)
- `int_device_hourly_stats` — hourly aggregates per device
- `int_device_daily_stats` — daily aggregates per device
- `int_alert_summary` — daily alert counts by device/type/severity

#### Marts (dbt tables/views)
- `dim_devices` — device dimension with `maintenance_due` flag
- `fct_device_health` — device health scores per day (currently materialized as a view)
- `fct_alerts` — alerts enriched with device info
- `fct_maintenance_recommendations` — maintenance-oriented recommendation view for overdue devices

[Back to Contents](#contents)

<a id="flink-alternative-kappa-architecture"></a>
## Flink Alternative (Kappa Architecture)

To use Flink instead of Spark for streaming:

```bash
# Start with Flink overlay
make up-flink

# Submit the Flink streaming job
make flink-streaming
```

The Flink job reads from the same Kafka topic and writes to MinIO, demonstrating the Kappa approach where **all processing goes through the stream** — no separate batch layer.

[Back to Contents](#contents)

<a id="project-structure"></a>
## Project Structure

```
FactoryPulse-IoT-Data-Platform/
├── docker-compose.yml           # Core stack (infra + simulator; processing jobs run via commands/demo)
├── docker-compose.flink.yml     # Flink overlay (Kappa architecture)
├── .env.example                 # Environment configuration
├── Makefile                     # All commands
│
├── simulators/                  # IoT data generators
│   ├── sensor_stream.py         # Streaming telemetry → Kafka
│   └── batch_reference_gen.py   # Reference data → MinIO
│
├── spark/                       # Spark processing
│   ├── streaming/
│   │   └── telemetry_stream.py  # Structured Streaming (speed layer → Iceberg + ClickHouse)
│   └── batch/
│       ├── ingest_reference.py  # Batch ingest (batch layer)
│       └── anomaly_scoring.py   # Rule-based anomaly detection + MLflow
│
├── flink/                       # Flink processing (Kappa alternative)
│   └── telemetry_stream.py      # PyFlink streaming job
│
├── airflow/dags/                # Pipeline orchestration
│   ├── batch_ingest_dag.py
│   ├── anomaly_scoring_dag.py
│   ├── dbt_transform_dag.py
│   ├── feast_materialize_dag.py
│   └── qdrant_ingest_dag.py
│
├── dbt/                         # ClickHouse transformations (ELT)
│   ├── models/staging/          # Staging views
│   ├── models/intermediate/     # Intermediate views
│   └── models/marts/            # dbt marts (tables + views)
│
├── feast/                       # Feature store
│   ├── features.py              # Feature definitions
│   └── prepare_data.py          # ClickHouse → Parquet bridge
│
├── api/                         # FastAPI serving layer
│   ├── routers/                 # Endpoint modules
│   ├── qdrant_ingest.py         # Vector ingestion script (manuals + incidents when present)
│   └── ge_validate.py           # Data quality validation
│
├── clickhouse/init.sql          # Warehouse schema
│
├── monitoring/                  # Observability
│   ├── prometheus/              # Scrape configs
│   └── grafana/provisioning/    # Datasources + dashboards
│
├── great_expectations/          # Data quality expectations
├── mlflow/                      # ML experiment tracking
├── architecture/                # PlantUML C4 diagrams
├── scripts/                     # Demo and utility scripts
└── docs/                        # Additional documentation
```

[Back to Contents](#contents)

<a id="makefile-commands"></a>
## Makefile Commands

```bash
make help                # Show all commands
make up                  # Start core stack
make down                # Stop everything
make up-flink            # Start with Flink overlay
make demo                # Run full end-to-end demo
make spark-streaming     # Launch Spark Structured Streaming
make spark-batch         # Run Spark batch ingest
make spark-anomaly       # Run anomaly scoring
make flink-streaming     # Submit Flink streaming job
make dbt-run             # Run dbt models
make dbt-test            # Run dbt tests
make feast-apply         # Apply Feast feature definitions
make feast-materialize   # Materialize features to Redis
make qdrant-ingest       # Ingest vectors into Qdrant
make ge-validate         # Run data quality validation
make api-test            # Run API tests
make logs SVC=<name>     # Tail service logs
make clean               # Stop and remove volumes
```

### Stopping vs Cleaning Up

`make down` only stops and removes the Compose containers and network. It does not remove volumes or persisted data.

The destructive targets are:

- `make clean` — runs `docker compose down -v` and removes volumes/data
- `make prune` — removes volumes/data and also prunes images

In practice:

- `make down` — safe stop; data should remain
- `make clean` — removes volumes/data
- `make prune` — removes volumes/data and prunes images

[Back to Contents](#contents)

<a id="lineage-tracking"></a>
## Lineage Tracking

Pipeline lineage is tracked via **Marquez** (OpenLineage backend). Airflow DAGs automatically emit OpenLineage events to Marquez, creating a visual lineage graph of:

- Data sources (Kafka topics, MinIO buckets)
- Processing jobs (Spark batch, Spark streaming, dbt models)
- Output datasets (Iceberg tables, ClickHouse tables, Qdrant collections)

View lineage at http://localhost:3001.

[Back to Contents](#contents)

<a id="monitoring"></a>
## Monitoring

Two pre-configured Grafana dashboards:

1. **FactoryPulse Overview** — Active devices, telemetry rate, temperatures, alerts, API latency
2. **Pipeline Health** — Data freshness, throughput, error rates, quality score, table sizes

Prometheus scrapes metrics from: FastAPI, Kafka (JMX), Spark, ClickHouse, Flink, Airflow, MLflow.

[Back to Contents](#contents)

<a id="runbook"></a>
## Runbook

### Common Operations

```bash
# Check service health
make ps
bash scripts/wait_for_services.sh

# View logs for a specific service
make logs SVC=simulator
make logs SVC=spark-master

# Restart a single service
docker compose restart api

# Run batch ingest manually
make spark-batch

# Check ClickHouse data
docker compose exec clickhouse clickhouse-client --password clickhouse \
  -q "SELECT count() FROM factory_pulse.raw_telemetry"
```

### Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Kafka not ready | `make logs SVC=kafka` | Wait 30s, check Zookeeper |
| No telemetry data | `make logs SVC=simulator` and `make logs SVC=spark-master` | Ensure simulator is producing and rerun `make spark-streaming` |
| Spark job fails | `make logs SVC=spark-master` | Check Iceberg REST, MinIO, and Kafka connectivity |
| dbt fails | Check ClickHouse raw tables | Run `make spark-batch` and `make spark-anomaly` first |
| Empty Qdrant | Run `make qdrant-ingest` | Check MinIO for `incident_manuals.json` and API logs |
| Grafana no data | Check ClickHouse connection | Verify datasource config |

### Resource Requirements

The full stack uses ~12 GB RAM. To reduce footprint:
- Stop Flink overlay if not needed (`make down-flink`)
- Use `profiles` to skip optional services (dbt, feast run on-demand)
- Reduce `SIMULATOR_DEVICE_COUNT` in `.env`

[Back to Contents](#contents)

<a id="license"></a>
## License

Open source — all components use permissive or open-source licenses.

[Back to Contents](#contents)
