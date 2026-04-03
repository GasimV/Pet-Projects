"""Alerts router — query and manage alerts from ClickHouse."""

import os
from typing import Optional

import clickhouse_connect
from fastapi import APIRouter, HTTPException, Query

from models import Alert

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _get_ch_client():
    """Create a ClickHouse client from environment variables."""
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=os.environ.get("CLICKHOUSE_DB", "factory_pulse"),
    )


def _rows_to_alerts(rows: list) -> list[Alert]:
    """Convert ClickHouse result rows to Alert models."""
    alerts = []
    for row in rows:
        alerts.append(
            Alert(
                alert_id=row[0],
                device_id=row[1],
                alert_type=row[2],
                severity=row[3],
                message=row[4],
                metric_name=row[5],
                metric_value=row[6],
                threshold=row[7],
                timestamp=row[8],
                resolved=row[9],
            )
        )
    return alerts


_ALERT_COLUMNS = """
    alert_id, device_id, alert_type, severity, message,
    metric_name, metric_value, threshold, timestamp, resolved
"""


@router.get("/", response_model=list[Alert])
async def get_alerts(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, warning, info)"),
    limit: int = Query(100, ge=1, le=10000, description="Max rows returned"),
):
    """Query alerts from ClickHouse."""
    try:
        client = _get_ch_client()

        query = f"SELECT {_ALERT_COLUMNS} FROM raw_alerts WHERE 1=1"
        params: dict = {"limit": limit}

        if device_id:
            query += " AND device_id = {device_id:String}"
            params["device_id"] = device_id

        if severity:
            query += " AND severity = {severity:String}"
            params["severity"] = severity

        query += " ORDER BY timestamp DESC LIMIT {limit:UInt32}"

        result = client.query(query, parameters=params)
        return _rows_to_alerts(result.result_rows)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")


@router.get("/active", response_model=list[Alert])
async def get_active_alerts(
    limit: int = Query(100, ge=1, le=10000, description="Max rows returned"),
):
    """Get unresolved (active) alerts."""
    try:
        client = _get_ch_client()

        query = f"""
            SELECT {_ALERT_COLUMNS}
            FROM raw_alerts
            WHERE resolved = 0
            ORDER BY timestamp DESC
            LIMIT {{limit:UInt32}}
        """

        result = client.query(query, parameters={"limit": limit})
        return _rows_to_alerts(result.result_rows)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse query failed: {exc}")


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Mark an alert as resolved.

    ClickHouse MergeTree tables are append-only, so we insert a new row with
    resolved=1.  The latest row wins when reading via FINAL or
    ReplacingMergeTree, but since raw_alerts uses plain MergeTree we use an
    ALTER UPDATE mutation for simplicity.
    """
    try:
        client = _get_ch_client()

        # Verify alert exists
        check = client.query(
            "SELECT count() FROM raw_alerts WHERE alert_id = {alert_id:String}",
            parameters={"alert_id": alert_id},
        )
        if check.result_rows[0][0] == 0:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # Mutate the resolved flag
        client.command(
            "ALTER TABLE raw_alerts UPDATE resolved = 1 "
            "WHERE alert_id = {alert_id:String}",
            parameters={"alert_id": alert_id},
        )

        return {"alert_id": alert_id, "status": "resolved"}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ClickHouse mutation failed: {exc}")
