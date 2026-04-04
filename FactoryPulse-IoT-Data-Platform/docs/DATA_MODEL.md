# FactoryPulse — Data Model

## Entity Relationship

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   Devices    │1────*│    Telemetry     │       │   Incidents  │
│──────────────│       │──────────────────│       │──────────────│
│ device_id PK │       │ event_id PK      │       │ incident_id  │
│ device_type  │       │ device_id FK     │       │ device_id FK │
│ manufacturer │       │ timestamp        │       │ title        │
│ model        │       │ temperature      │       │ description  │
│ install_date │       │ vibration        │       │ resolution   │
│ location     │       │ pressure         │       │ severity     │
│ zone         │       │ humidity         │       │ created_at   │
│ maint_intrvl │       │ power_usage      │       │ resolved_at  │
│ last_maint   │       │ rpm              │       └──────────────┘
│ status       │       │ error_code       │
└──────┬───────┘       └──────────────────┘
       │1
       │
       │*
┌──────────────┐
│    Alerts    │
│──────────────│
│ alert_id PK  │
│ device_id FK │
│ alert_type   │
│ severity     │
│ message      │
│ metric_name  │
│ metric_value │
│ threshold    │
│ timestamp    │
│ resolved     │
└──────────────┘
```

## Layer Progression

### Raw Layer (MinIO / Iceberg)
- Unprocessed sensor readings and files as landed
- Stored as Parquet in Iceberg tables on MinIO
- Schema: same as source with `ingested_at` timestamp added

### Landing Layer (ClickHouse raw_* tables)
- Mirror of Iceberg raw data in ClickHouse for query performance
- MergeTree engine with partition by day, ordered by (device_id, timestamp)
- Populated by Spark batch/streaming jobs

### Staging Layer (dbt views: stg_*)
- Type casts, renames, computed columns
- `stg_telemetry`: adds `reading_hour` (toStartOfHour)
- `stg_devices`: adds `days_since_maintenance` (dateDiff)
- `stg_alerts`: pass-through with cleaning

### Intermediate Layer (dbt views: int_*)
- Aggregations and joins
- `int_device_hourly_stats`: avg/max/min metrics per device per hour
- `int_device_daily_stats`: daily rollup
- `int_alert_summary`: alert counts by device/type/severity per day

### Marts Layer (dbt tables: dim_* / fct_*)
- Business-ready dimensional model (star schema)
- `dim_devices`: device dimension with `maintenance_due` flag
- `fct_device_health`: health scores (0-100) per device
- `fct_alerts`: enriched alerts with device info
- `fct_maintenance_recommendations`: actionable maintenance priorities

### Feature Store (Feast → Redis)
- `device_hourly_stats`: latest hourly aggregates per device
- `device_health_features`: health score, days since maintenance, alert count
- `device_risk_level`: on-demand computed risk classification

### Vector Store (Qdrant)
- Collection: `incidents` (384-dim vectors, cosine similarity)
- Sources: incident reports + maintenance manuals
- Payload: title, text, device_id, severity, source

## Data Flow Summary

```
Sensors → Kafka → Spark Streaming → Iceberg (MinIO)  ← SPEED LAYER
Sensors → MinIO → Spark Batch → Iceberg → ClickHouse  ← BATCH LAYER
ClickHouse → dbt (staging → intermediate → marts)     ← ELT TRANSFORMS
ClickHouse → Feast → Redis                            ← FEATURE SERVING
Incidents → sentence-transformers → Qdrant             ← VECTOR SEARCH
All above → FastAPI                                    ← UNIFIED SERVING
```
