# FactoryPulse — Architecture Guide

## Lambda Architecture

The platform implements the **Lambda Architecture** with three layers:

### Batch Layer
- **Technology**: Spark Batch → Iceberg → ClickHouse
- **Purpose**: Processes complete datasets for accuracy
- **Jobs**: `ingest_reference.py` (reference data), `anomaly_scoring.py` (batch ML)
- **Latency**: Minutes to hours (scheduled via Airflow)
- **Data path**: MinIO (CSV/Parquet) → Spark → Iceberg tables → ClickHouse

### Speed Layer
- **Technology**: Spark Structured Streaming (or Flink)
- **Purpose**: Low-latency processing of real-time telemetry
- **Jobs**: `telemetry_stream.py` (continuous)
- **Latency**: Seconds (micro-batch every 10s)
- **Data path**: Kafka → Spark Streaming → Iceberg tables

### Serving Layer
- **Technology**: FastAPI + ClickHouse + Redis + Qdrant
- **Purpose**: Unified query interface merging batch and speed results
- **Endpoints**: telemetry, alerts, devices, health, search, features
- **Data path**: ClickHouse (batch results) + Iceberg (streaming results) → API

## Kappa Architecture (Flink Alternative)

When using the Flink overlay (`docker-compose.flink.yml`), the platform operates in **Kappa mode**:

- **Single pipeline**: All data flows through Flink streaming
- **No separate batch layer**: Historical reprocessing done by replaying Kafka
- **Simpler architecture**: One code path for both real-time and historical
- **Trade-off**: Less optimised for complex batch analytics

### Switching Between Lambda and Kappa

```bash
# Lambda (default): Spark batch + Spark streaming
make up

# Kappa: Flink streaming only
make up-flink
make flink-streaming
```

## Storage Tiers

```
┌─────────────────────────────────────────────┐
│           MinIO (Object Storage)            │  ← Data Lake
│  Raw files: CSV, Parquet, JSON              │
├─────────────────────────────────────────────┤
│        Iceberg (Table Format)               │  ← Lakehouse
│  ACID transactions, schema evolution,       │
│  time travel on top of MinIO                │
├─────────────────────────────────────────────┤
│         ClickHouse (OLAP Engine)            │  ← Data Warehouse
│  Columnar storage, fast aggregations,       │
│  dimensional models via dbt                 │
├─────────────────────────────────────────────┤
│   Redis (Online Features) │ Qdrant (Vectors)│  ← Serving Stores
│   Low-latency lookups     │ Semantic search  │
└─────────────────────────────────────────────┘
```

## ETL vs ELT

| Pattern | Where | Implementation |
|---------|-------|---------------|
| **ETL** | Spark jobs | Extract from Kafka/MinIO → Transform (parse, clean, score) → Load to Iceberg/ClickHouse |
| **ELT** | dbt-core | Extract & Load (Spark loads raw data to ClickHouse) → Transform (dbt runs SQL models in ClickHouse) |

Both patterns coexist: ETL handles the heavy lifting (parsing streams, computing anomalies), while ELT handles analytical transformations (aggregations, joins, dimensional modelling).

## Service Communication

```
                    ┌──── gRPC/HTTP ────┐
                    │                    │
Simulator ─Kafka──▶ Spark/Flink ─S3A──▶ MinIO/Iceberg
                    │                    │
                    └─HTTP──▶ ClickHouse ◄── dbt (HTTP)
                                │
                    Feast ──────┘──▶ Redis
                                │
                    API ◄───────┘──▶ Qdrant
                     │
               Prometheus ◄── scrape ── all services
                     │
                  Grafana
```

## C4 Diagrams

See `architecture/*.puml` for:
- **C1**: System Context — actors and external systems
- **C2**: Container — all services and data flows
- **C3**: Component — detailed data flow showing Lambda vs Kappa
- **C4**: Deployment — Docker Compose deployment view
