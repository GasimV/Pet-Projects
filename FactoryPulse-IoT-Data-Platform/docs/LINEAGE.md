# FactoryPulse — Data Lineage

## Overview

Data lineage is tracked via **Marquez** (OpenLineage backend). Airflow emits OpenLineage events automatically through the `openlineage-airflow` package.

View lineage: http://localhost:3001

## Lineage Graph

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│ Kafka:           │     │ MinIO:              │     │ MinIO:            │
│ factory.telemetry│     │ factory-raw/        │     │ factory-raw/      │
│ .raw             │     │ reference/devices.csv│    │ historical/*.parq │
└────────┬────────┘     └─────────┬──────────┘     └────────┬─────────┘
         │                        │                          │
         ▼                        └──────────┬───────────────┘
   Spark Streaming                           ▼
   (telemetry_stream)              Spark Batch Ingest
         │                       (ingest_reference)
         ▼                              │
   Iceberg:                             ▼
   factory_db.                   Iceberg:                    ClickHouse:
   raw_telemetry  ──────────▶   factory_db.raw_telemetry ──▶ raw_telemetry
                                factory_db.dim_devices   ──▶ raw_devices
                                        │
                                        ▼
                              Spark Anomaly Scoring
                             (anomaly_scoring)
                                        │
                                        ▼
                              Iceberg: anomaly_scores
                              ClickHouse: raw_alerts
                                        │
                                        ▼
                                  dbt Transform
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              stg_telemetry      stg_devices          stg_alerts
                    │                   │                   │
                    ▼                   ▼                   ▼
           int_device_hourly    int_device_daily    int_alert_summary
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              dim_devices      fct_device_health    fct_alerts
                                        │
                                        ▼
                              fct_maintenance_recommendations
```

## Tracked Jobs

| DAG | Input Datasets | Output Datasets |
|-----|---------------|-----------------|
| `batch_ingest` | MinIO: devices.csv, historical/*.parquet | Iceberg: raw_telemetry, dim_devices → ClickHouse: raw_telemetry, raw_devices |
| `anomaly_scoring` | Iceberg: raw_telemetry | Iceberg: anomaly_scores → ClickHouse: raw_alerts |
| `dbt_transform` | ClickHouse: raw_* tables | ClickHouse: stg_*, int_*, dim_*, fct_* |
| `feast_materialize` | ClickHouse: fct_* tables | Redis: online features |
| `qdrant_ingest` | MinIO: incident_manuals.json, ClickHouse: raw_incidents | Qdrant: incidents collection |

## OpenLineage Integration

Airflow automatically emits lineage events via the `AIRFLOW__OPENLINEAGE__TRANSPORT` environment variable configured in `docker-compose.yml`:

```json
{"type": "http", "url": "http://marquez-api:5000", "endpoint": "api/v1/lineage"}
```

Spark jobs can also emit OpenLineage events by adding the OpenLineage Spark integration JAR (not configured by default to keep the setup simple).
