"""Telemetry router — query raw telemetry readings from ClickHouse."""

import os
from typing import Optional

import clickhouse_connect
from fastapi import APIRouter, HTTPException, Query

from models import TelemetryReading

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


def _get_ch_client():
    """Create a ClickHouse client from environment variables."""
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=os.environ.get("CLICKHOUSE_DB", "factory_pulse"),
    )


@router.get("/", response_model=list[TelemetryReading])
async def get_telemetry(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    limit: int = Query(100, ge=1, le=10000, description="Max rows returned"),
    hours_back: int = Query(24, ge=1, le=720, description="Look-back window in hours"),
):
    """Query recent telemetry readings from ClickHouse."""
    try:
        client = _get_ch_client()

        query = """
            SELECT
                event_id, device_id, device_type, location,
                timestamp, temperature, vibration, pressure,
                humidity, power_usage, rpm, error_code
            FROM raw_telemetry
            WHERE timestamp >= now() - INTERVAL {hours_back:UInt32} HOUR
        """
        params: dict = {"hours_back": hours_back, "limit": limit}

        if device_id:
            query += " AND device_id = {device_id:String}"
            params["device_id"] = device_id

        query += " ORDER BY timestamp DESC LIMIT {limit:UInt32}"

        result = client.query(query, parameters=params)

        readings = []
        for row in result.result_rows:
            readings.append(
                TelemetryReading(
                    event_id=row[0],
                    device_id=row[1],
                    device_type=row[2],
                    location=row[3],
                    timestamp=row[4],
                    temperature=row[5],
                    vibration=row[6],
                    pressure=row[7],
                    humidity=row[8],
                    power_usage=row[9],
                    rpm=row[10],
                    error_code=row[11],
                )
            )
        return readings

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")


@router.get("/stats")
async def get_telemetry_stats(
    hours_back: int = Query(24, ge=1, le=720, description="Look-back window in hours"),
):
    """Aggregated telemetry stats grouped by device_id for the last N hours."""
    try:
        client = _get_ch_client()

        query = """
            SELECT
                device_id,
                count()                     AS reading_count,
                round(avg(temperature), 2)  AS avg_temperature,
                round(min(temperature), 2)  AS min_temperature,
                round(max(temperature), 2)  AS max_temperature,
                round(avg(vibration), 4)    AS avg_vibration,
                round(max(vibration), 4)    AS max_vibration,
                round(avg(pressure), 2)     AS avg_pressure,
                round(avg(humidity), 2)     AS avg_humidity,
                round(avg(power_usage), 2)  AS avg_power_usage,
                round(avg(rpm), 2)          AS avg_rpm,
                max(timestamp)              AS last_reading
            FROM raw_telemetry
            WHERE timestamp >= now() - INTERVAL {hours_back:UInt32} HOUR
            GROUP BY device_id
            ORDER BY device_id
        """

        result = client.query(query, parameters={"hours_back": hours_back})
        columns = [col[0] for col in result.column_names] if hasattr(result, "column_names") else [
            "device_id", "reading_count",
            "avg_temperature", "min_temperature", "max_temperature",
            "avg_vibration", "max_vibration",
            "avg_pressure", "avg_humidity", "avg_power_usage", "avg_rpm",
            "last_reading",
        ]

        stats = []
        for row in result.result_rows:
            stats.append(dict(zip(columns, row)))

        return {"hours_back": hours_back, "devices": stats}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")
