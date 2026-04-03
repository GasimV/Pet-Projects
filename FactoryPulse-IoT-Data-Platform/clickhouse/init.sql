-- ClickHouse initialization for FactoryPulse
-- Creates the warehouse schema used by dbt and the API.

CREATE DATABASE IF NOT EXISTS factory_pulse;

-- Raw telemetry landing table (populated by Spark batch from Iceberg or directly)
CREATE TABLE IF NOT EXISTS factory_pulse.raw_telemetry
(
    event_id       String,
    device_id      String,
    device_type    String,
    location       String,
    timestamp      DateTime64(3),
    temperature    Float64,
    vibration      Float64,
    pressure       Float64,
    humidity       Float64,
    power_usage    Float64,
    rpm            Float64,
    error_code     Nullable(String),
    ingested_at    DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (device_id, timestamp);

-- Device reference / dimension table
CREATE TABLE IF NOT EXISTS factory_pulse.raw_devices
(
    device_id       String,
    device_type     String,
    manufacturer    String,
    model           String,
    install_date    Date,
    location        String,
    zone            String,
    maintenance_interval_days  UInt16,
    last_maintenance_date      Date,
    status          String,
    updated_at      DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY device_id;

-- Alerts table
CREATE TABLE IF NOT EXISTS factory_pulse.raw_alerts
(
    alert_id        String,
    device_id       String,
    alert_type      String,
    severity        String,
    message         String,
    metric_name     String,
    metric_value    Float64,
    threshold       Float64,
    timestamp       DateTime64(3),
    resolved        UInt8 DEFAULT 0,
    ingested_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (device_id, timestamp);

-- Incidents table (for text/semantic search)
CREATE TABLE IF NOT EXISTS factory_pulse.raw_incidents
(
    incident_id     String,
    device_id       String,
    title           String,
    description     String,
    resolution      Nullable(String),
    severity        String,
    created_at      DateTime64(3),
    resolved_at     Nullable(DateTime64(3)),
    ingested_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (device_id, created_at);
