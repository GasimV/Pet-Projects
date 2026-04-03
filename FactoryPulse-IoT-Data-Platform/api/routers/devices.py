"""Devices router — device metadata, health scores, and maintenance recommendations."""

import os

import clickhouse_connect
from fastapi import APIRouter, HTTPException

from models import Device, DeviceHealth, MaintenanceRecommendation

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _get_ch_client():
    """Create a ClickHouse client from environment variables."""
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=os.environ.get("CLICKHOUSE_DB", "factory_pulse"),
    )


@router.get("/", response_model=list[Device])
async def list_devices():
    """List all devices from ClickHouse."""
    try:
        client = _get_ch_client()

        result = client.query(
            """
            SELECT
                device_id, device_type, manufacturer, model,
                toString(install_date) AS install_date,
                location, zone,
                maintenance_interval_days,
                toString(last_maintenance_date) AS last_maintenance_date,
                status
            FROM raw_devices
            ORDER BY device_id
            """
        )

        devices = []
        for row in result.result_rows:
            devices.append(
                Device(
                    device_id=row[0],
                    device_type=row[1],
                    manufacturer=row[2],
                    model=row[3],
                    install_date=row[4],
                    location=row[5],
                    zone=row[6],
                    maintenance_interval_days=row[7],
                    last_maintenance_date=row[8],
                    status=row[9],
                )
            )
        return devices

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")


@router.get("/{device_id}", response_model=DeviceHealth)
async def get_device_health(device_id: str):
    """Device detail with computed health score.

    The health score is derived from recent telemetry and alert counts.
    If a dbt-built ``fct_device_health`` table exists it will be used;
    otherwise the score is computed on the fly from raw tables.
    """
    try:
        client = _get_ch_client()

        # Try the dbt fact table first; fall back to a live calculation.
        try:
            fct_result = client.query(
                """
                SELECT
                    device_id, health_score,
                    avg_temperature, avg_vibration, avg_pressure,
                    alert_count, last_reading
                FROM fct_device_health
                WHERE device_id = {device_id:String}
                """,
                parameters={"device_id": device_id},
            )
            if fct_result.result_rows:
                row = fct_result.result_rows[0]
                return DeviceHealth(
                    device_id=row[0],
                    health_score=row[1],
                    avg_temperature=row[2],
                    avg_vibration=row[3],
                    avg_pressure=row[4],
                    alert_count=row[5],
                    last_reading=row[6],
                )
        except Exception:
            pass  # table may not exist yet; compute live

        # Live calculation from raw tables
        telemetry = client.query(
            """
            SELECT
                round(avg(temperature), 2),
                round(avg(vibration), 4),
                round(avg(pressure), 2),
                max(timestamp)
            FROM raw_telemetry
            WHERE device_id = {device_id:String}
              AND timestamp >= now() - INTERVAL 24 HOUR
            """,
            parameters={"device_id": device_id},
        )

        alert_count_result = client.query(
            """
            SELECT count()
            FROM raw_alerts
            WHERE device_id = {device_id:String}
              AND resolved = 0
            """,
            parameters={"device_id": device_id},
        )

        avg_temp = telemetry.result_rows[0][0] if telemetry.result_rows else None
        avg_vib = telemetry.result_rows[0][1] if telemetry.result_rows else None
        avg_pres = telemetry.result_rows[0][2] if telemetry.result_rows else None
        last_reading = telemetry.result_rows[0][3] if telemetry.result_rows else None
        alert_count = alert_count_result.result_rows[0][0] if alert_count_result.result_rows else 0

        # Simple health score heuristic: start at 100, deduct for anomalies
        score = 100.0
        if avg_temp is not None and (avg_temp > 150 or avg_temp < -10):
            score -= 30
        if avg_vib is not None and avg_vib > 0.8:
            score -= 20
        score -= min(alert_count * 5, 40)  # cap alert penalty at 40
        score = max(score, 0.0)

        return DeviceHealth(
            device_id=device_id,
            health_score=round(score, 1),
            avg_temperature=avg_temp,
            avg_vibration=avg_vib,
            avg_pressure=avg_pres,
            alert_count=alert_count,
            last_reading=last_reading,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")


@router.get("/{device_id}/maintenance", response_model=MaintenanceRecommendation)
async def get_maintenance_recommendation(device_id: str):
    """Maintenance recommendation for a device.

    Uses ``fct_maintenance_recommendations`` if available, otherwise computes
    a recommendation from the raw device metadata and recent telemetry.
    """
    try:
        client = _get_ch_client()

        # Try dbt fact table first
        try:
            fct = client.query(
                """
                SELECT
                    device_id, device_type,
                    days_since_maintenance, maintenance_interval_days,
                    overdue, health_score, recommendation, priority
                FROM fct_maintenance_recommendations
                WHERE device_id = {device_id:String}
                """,
                parameters={"device_id": device_id},
            )
            if fct.result_rows:
                row = fct.result_rows[0]
                return MaintenanceRecommendation(
                    device_id=row[0],
                    device_type=row[1],
                    days_since_maintenance=row[2],
                    maintenance_interval_days=row[3],
                    overdue=bool(row[4]),
                    health_score=row[5],
                    recommendation=row[6],
                    priority=row[7],
                )
        except Exception:
            pass  # table may not exist yet

        # Live calculation from raw_devices
        dev = client.query(
            """
            SELECT
                device_id, device_type,
                maintenance_interval_days,
                last_maintenance_date,
                dateDiff('day', last_maintenance_date, today()) AS days_since
            FROM raw_devices
            WHERE device_id = {device_id:String}
            """,
            parameters={"device_id": device_id},
        )

        if not dev.result_rows:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        row = dev.result_rows[0]
        device_type = row[1]
        interval_days = row[2]
        days_since = row[4]
        overdue = days_since > interval_days

        # Build recommendation text
        if overdue:
            days_overdue = days_since - interval_days
            recommendation = (
                f"OVERDUE: Maintenance was due {days_overdue} day(s) ago. "
                f"Schedule immediately."
            )
            priority = "critical" if days_overdue > interval_days * 0.5 else "high"
        elif days_since > interval_days * 0.8:
            recommendation = (
                f"Maintenance due soon ({interval_days - days_since} days remaining). "
                f"Schedule within the next week."
            )
            priority = "medium"
        else:
            recommendation = (
                f"Device within normal maintenance window. "
                f"Next maintenance in ~{interval_days - days_since} days."
            )
            priority = "low"

        return MaintenanceRecommendation(
            device_id=device_id,
            device_type=device_type,
            days_since_maintenance=days_since,
            maintenance_interval_days=interval_days,
            overdue=overdue,
            health_score=None,
            recommendation=recommendation,
            priority=priority,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")
