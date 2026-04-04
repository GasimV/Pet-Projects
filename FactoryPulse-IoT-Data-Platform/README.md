# FactoryPulse — IoT Data Engineering Platform

A fully local, open-source, Dockerised IoT data engineering platform that demonstrates modern data architecture patterns: **batch + streaming**, **ETL + ELT**, **Data Lake + Lakehouse + Warehouse**, **Lambda + Kappa**, feature stores, vector search, data quality, lineage tracking, and ML experiment management.

## Architecture Overview

```
┌──────────────┐
│ IoT Simulator │──→ Kafka ──→ Spark Structured Streaming ──→ Iceberg/MinIO  (Speed Layer)
│  (10 devices) │                   or Flink (Kappa)
└──────┬───────┘
       │
       └──→ MinIO (CSV/Parquet) ──→ Spark Batch ──→ Iceberg ──→ ClickHouse  (Batch Layer)
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
| **Lambda Architecture** | Batch layer (Spark Batch → Iceberg → ClickHouse) + Speed layer (Spark Structured Streaming → Iceberg) merge at the serving layer (FastAPI) |
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

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- 16 GB RAM recommended (8 GB minimum)
- ~15 GB disk space

### 1. Start the Platform

```bash
# Clone and enter the repo
cd FactoryPulse-IoT-Data-Platform

# Copy env file and start all services
make up
```

This starts ~20 containers: Kafka, MinIO, Iceberg, Spark, ClickHouse, Redis, Qdrant, Airflow, FastAPI, Marquez, MLflow, Prometheus, Grafana, and the IoT simulator.

### 2. Run the Full Demo

```bash
make demo
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
| Spark UI | http://localhost:8080 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| MLflow | http://localhost:5050 | — |
| Marquez (Lineage) | http://localhost:3001 | — |
| ClickHouse HTTP | http://localhost:8123 | — |
| Qdrant Dashboard | http://localhost:6333/dashboard | — |
| Prometheus | http://localhost:9090 | — |
| Iceberg REST | http://localhost:8181 | — |

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

- **Streaming telemetry** → Kafka → Spark/Flink → Iceberg (every 2 seconds)
- **Batch reference files** → MinIO (devices.csv, historical Parquet, incident_manuals.json)
- **Alerts** → ClickHouse (anomaly scoring produces CRITICAL/WARNING/NORMAL)
- **Incidents** → Kafka + ClickHouse → Qdrant (for semantic search)

### Anomaly Scoring (Rule-Based)

| Condition | Score |
|-----------|-------|
| temperature > 95°C | +30 |
| vibration > 3.0 mm/s | +25 |
| pressure > 250 or < 50 bar | +20 |
| power_usage > 90 kW | +15 |
| error_code present | +10 |

Classification: **CRITICAL** (≥50), **WARNING** (≥30), **NORMAL** (<30)

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

#### Marts (dbt tables — MergeTree)
- `dim_devices` — device dimension with `maintenance_due` flag
- `fct_device_health` — health scores per device (0–100 scale)
- `fct_alerts` — alerts enriched with device info
- `fct_maintenance_recommendations` — devices needing maintenance with priority/action

## Flink Alternative (Kappa Architecture)

To use Flink instead of Spark for streaming:

```bash
# Start with Flink overlay
make up-flink

# Submit the Flink streaming job
make flink-streaming
```

The Flink job reads from the same Kafka topic and writes to MinIO, demonstrating the Kappa approach where **all processing goes through the stream** — no separate batch layer.

## Project Structure

```
FactoryPulse-IoT-Data-Platform/
├── docker-compose.yml           # Core stack (Kafka + Spark streaming)
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
│   │   └── telemetry_stream.py  # Structured Streaming (speed layer)
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
│   └── models/marts/            # Materialized tables
│
├── feast/                       # Feature store
│   ├── features.py              # Feature definitions
│   └── prepare_data.py          # ClickHouse → Parquet bridge
│
├── api/                         # FastAPI serving layer
│   ├── routers/                 # Endpoint modules
│   ├── qdrant_ingest.py         # Vector ingestion script
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

## Lineage Tracking

Pipeline lineage is tracked via **Marquez** (OpenLineage backend). Airflow DAGs automatically emit OpenLineage events to Marquez, creating a visual lineage graph of:

- Data sources (Kafka topics, MinIO buckets)
- Processing jobs (Spark batch, Spark streaming, dbt models)
- Output datasets (Iceberg tables, ClickHouse tables, Qdrant collections)

View lineage at http://localhost:3001.

## Monitoring

Two pre-configured Grafana dashboards:

1. **FactoryPulse Overview** — Active devices, telemetry rate, temperatures, alerts, API latency
2. **Pipeline Health** — Data freshness, throughput, error rates, quality score, table sizes

Prometheus scrapes metrics from: FastAPI, Kafka (JMX), Spark, ClickHouse, Flink, Airflow, MLflow.

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
| No telemetry data | `make logs SVC=simulator` | Restart simulator |
| Spark job fails | `make logs SVC=spark-master` | Check Iceberg REST, MinIO |
| dbt fails | Check ClickHouse raw tables | Run `make spark-batch` first |
| Empty Qdrant | Run `make qdrant-ingest` | Check MinIO for manuals file |
| Grafana no data | Check ClickHouse connection | Verify datasource config |

### Resource Requirements

The full stack uses ~12 GB RAM. To reduce footprint:
- Stop Flink overlay if not needed (`make down-flink`)
- Use `profiles` to skip optional services (dbt, feast run on-demand)
- Reduce `SIMULATOR_DEVICE_COUNT` in `.env`

## License

Open source — all components use permissive or open-source licenses.
