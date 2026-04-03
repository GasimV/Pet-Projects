"""
Feast feature definitions for the FactoryPulse IoT platform.

Feature views:
  - device_hourly_stats:   rolling 1-hour aggregated sensor metrics per device.
  - device_health_features: health / maintenance indicators per device.
  - device_risk_level:      on-demand risk classification derived from health score.
"""

from datetime import timedelta

import pandas as pd
from feast import Entity, FeatureView, Field, FileSource, on_demand_feature_view
from feast.types import Float32, Int64, String

# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------
device = Entity(
    name="device",
    join_keys=["device_id"],
    value_type=String,
    description="A physical IoT device on the factory floor.",
)

# ---------------------------------------------------------------------------
# Sources (Parquet files prepared by prepare_data.py)
# ---------------------------------------------------------------------------
device_hourly_stats_source = FileSource(
    path="/app/feast/data/device_hourly_stats.parquet",
    timestamp_field="event_timestamp",
)

device_health_source = FileSource(
    path="/app/feast/data/device_health.parquet",
    timestamp_field="event_timestamp",
)

# ---------------------------------------------------------------------------
# Feature View: device_hourly_stats
# ---------------------------------------------------------------------------
device_hourly_stats = FeatureView(
    name="device_hourly_stats",
    entities=[device],
    ttl=timedelta(hours=1),
    schema=[
        Field(name="avg_temperature", dtype=Float32),
        Field(name="max_temperature", dtype=Float32),
        Field(name="avg_vibration", dtype=Float32),
        Field(name="max_vibration", dtype=Float32),
        Field(name="avg_pressure", dtype=Float32),
        Field(name="avg_power_usage", dtype=Float32),
        Field(name="reading_count", dtype=Int64),
    ],
    source=device_hourly_stats_source,
    online=True,
)

# ---------------------------------------------------------------------------
# Feature View: device_health_features
# ---------------------------------------------------------------------------
device_health_features = FeatureView(
    name="device_health_features",
    entities=[device],
    ttl=timedelta(hours=24),
    schema=[
        Field(name="health_score", dtype=Float32),
        Field(name="days_since_maintenance", dtype=Int64),
        Field(name="alert_count_24h", dtype=Int64),
        Field(name="anomaly_score", dtype=Float32),
    ],
    source=device_health_source,
    online=True,
)

# ---------------------------------------------------------------------------
# On-demand Feature View: device_risk_level
# ---------------------------------------------------------------------------
@on_demand_feature_view(
    sources=[device_health_features],
    schema=[
        Field(name="risk_level", dtype=String),
    ],
)
def device_risk_level(inputs: pd.DataFrame) -> pd.DataFrame:
    """Classify device risk based on health_score thresholds."""
    df = pd.DataFrame()
    health = inputs["health_score"]

    df["risk_level"] = health.apply(
        lambda score: (
            "CRITICAL" if score < 30
            else "HIGH" if score < 50
            else "MEDIUM" if score < 70
            else "LOW"
        )
    )
    return df
