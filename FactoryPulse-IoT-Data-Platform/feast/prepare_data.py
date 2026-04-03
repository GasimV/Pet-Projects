"""
Prepare offline Parquet files for Feast from the ClickHouse warehouse.

This script queries ClickHouse for:
  1. Hourly aggregated sensor stats per device  -> device_hourly_stats.parquet
  2. Device health / maintenance indicators     -> device_health.parquet

Run inside the feast container (or anywhere with network access to ClickHouse):
    python prepare_data.py
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import clickhouse_connect
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration (read from env, with sensible defaults matching docker-compose)
# ---------------------------------------------------------------------------
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "factory_pulse")

DATA_DIR = Path("/app/feast/data")


def get_client() -> clickhouse_connect.driver.Client:
    """Return a ClickHouse HTTP client."""
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB,
    )


# ---------------------------------------------------------------------------
# Query 1: device_hourly_stats
# ---------------------------------------------------------------------------
HOURLY_STATS_SQL = """
SELECT
    device_id,
    toStartOfHour(timestamp)                        AS event_timestamp,
    avg(temperature)                                 AS avg_temperature,
    max(temperature)                                 AS max_temperature,
    avg(vibration)                                   AS avg_vibration,
    max(vibration)                                   AS max_vibration,
    avg(pressure)                                    AS avg_pressure,
    avg(power_usage)                                 AS avg_power_usage,
    count()                                          AS reading_count
FROM raw_telemetry
WHERE timestamp >= now() - INTERVAL 7 DAY
GROUP BY device_id, toStartOfHour(timestamp)
ORDER BY device_id, event_timestamp
"""


def fetch_hourly_stats(client: clickhouse_connect.driver.Client) -> pd.DataFrame:
    """Fetch hourly aggregated telemetry stats from ClickHouse."""
    result = client.query(HOURLY_STATS_SQL)
    df = pd.DataFrame(result.result_rows, columns=result.column_names)

    if df.empty:
        # Return an empty frame with the correct schema so Feast can still
        # register the source even when ClickHouse has no data yet.
        df = pd.DataFrame(
            columns=[
                "device_id",
                "event_timestamp",
                "avg_temperature",
                "max_temperature",
                "avg_vibration",
                "max_vibration",
                "avg_pressure",
                "avg_power_usage",
                "reading_count",
            ]
        )
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
        df["reading_count"] = df["reading_count"].astype("int64")
        for col in [
            "avg_temperature",
            "max_temperature",
            "avg_vibration",
            "max_vibration",
            "avg_pressure",
            "avg_power_usage",
        ]:
            df[col] = df[col].astype("float32")
    else:
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True)
        df["reading_count"] = df["reading_count"].astype("int64")
        for col in [
            "avg_temperature",
            "max_temperature",
            "avg_vibration",
            "max_vibration",
            "avg_pressure",
            "avg_power_usage",
        ]:
            df[col] = df[col].astype("float32")

    return df


# ---------------------------------------------------------------------------
# Query 2: device_health
# ---------------------------------------------------------------------------
DEVICE_HEALTH_SQL = """
SELECT
    d.device_id                                                     AS device_id,
    now()                                                           AS event_timestamp,
    -- Synthetic health_score: 100 minus penalties for age, alerts & vibration
    greatest(
        0,
        100
        - 2 * dateDiff('day', d.last_maintenance_date, today())
        - 10 * ifNull(a.alert_count_24h, 0)
    )                                                               AS health_score,
    dateDiff('day', d.last_maintenance_date, today())               AS days_since_maintenance,
    ifNull(a.alert_count_24h, 0)                                    AS alert_count_24h,
    -- Anomaly score: ratio of recent alerts to expected maintenance interval
    ifNull(a.alert_count_24h, 0) / d.maintenance_interval_days     AS anomaly_score
FROM raw_devices AS d
LEFT JOIN (
    SELECT
        device_id,
        countIf(timestamp >= now() - INTERVAL 1 DAY) AS alert_count_24h
    FROM raw_alerts
    GROUP BY device_id
) AS a ON d.device_id = a.device_id
ORDER BY d.device_id
"""


def fetch_device_health(client: clickhouse_connect.driver.Client) -> pd.DataFrame:
    """Fetch device health features from ClickHouse."""
    result = client.query(DEVICE_HEALTH_SQL)
    df = pd.DataFrame(result.result_rows, columns=result.column_names)

    if df.empty:
        df = pd.DataFrame(
            columns=[
                "device_id",
                "event_timestamp",
                "health_score",
                "days_since_maintenance",
                "alert_count_24h",
                "anomaly_score",
            ]
        )
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
        df["days_since_maintenance"] = df["days_since_maintenance"].astype("int64")
        df["alert_count_24h"] = df["alert_count_24h"].astype("int64")
        for col in ["health_score", "anomaly_score"]:
            df[col] = df[col].astype("float32")
    else:
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], utc=True)
        df["days_since_maintenance"] = df["days_since_maintenance"].astype("int64")
        df["alert_count_24h"] = df["alert_count_24h"].astype("int64")
        for col in ["health_score", "anomaly_score"]:
            df[col] = df[col].astype("float32")

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT} ...")
    client = get_client()

    # -- Hourly stats --
    print("Fetching device hourly stats ...")
    hourly_df = fetch_hourly_stats(client)
    hourly_path = DATA_DIR / "device_hourly_stats.parquet"
    hourly_df.to_parquet(hourly_path, index=False)
    print(f"  Wrote {len(hourly_df)} rows to {hourly_path}")

    # -- Device health --
    print("Fetching device health features ...")
    health_df = fetch_device_health(client)
    health_path = DATA_DIR / "device_health.parquet"
    health_df.to_parquet(health_path, index=False)
    print(f"  Wrote {len(health_df)} rows to {health_path}")

    print("Done. Parquet files are ready for Feast.")


if __name__ == "__main__":
    main()
