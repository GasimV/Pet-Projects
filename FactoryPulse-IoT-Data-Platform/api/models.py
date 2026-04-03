"""Pydantic models for the FactoryPulse API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TelemetryReading(BaseModel):
    """A single telemetry reading from a factory device."""

    event_id: str
    device_id: str
    device_type: str
    location: str
    timestamp: datetime
    temperature: float
    vibration: float
    pressure: float
    humidity: float
    power_usage: float
    rpm: float
    error_code: Optional[str] = None


class Alert(BaseModel):
    """An alert triggered by threshold breaches or anomaly detection."""

    alert_id: str
    device_id: str
    alert_type: str
    severity: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    timestamp: datetime
    resolved: int = 0


class Device(BaseModel):
    """Device reference and metadata."""

    device_id: str
    device_type: str
    manufacturer: str
    model: str
    install_date: str
    location: str
    zone: str
    maintenance_interval_days: int
    last_maintenance_date: str
    status: str


class DeviceHealth(BaseModel):
    """Device health score and related metrics."""

    device_id: str
    health_score: float
    avg_temperature: Optional[float] = None
    avg_vibration: Optional[float] = None
    avg_pressure: Optional[float] = None
    alert_count: int = 0
    last_reading: Optional[datetime] = None


class SearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=5, ge=1, le=100, description="Number of results")


class SearchResult(BaseModel):
    """A single semantic search result."""

    id: str
    title: str
    text: str
    device_id: Optional[str] = None
    severity: Optional[str] = None
    source: str
    score: float


class MaintenanceRecommendation(BaseModel):
    """Maintenance recommendation for a device."""

    device_id: str
    device_type: str
    days_since_maintenance: int
    maintenance_interval_days: int
    overdue: bool
    health_score: Optional[float] = None
    recommendation: str
    priority: str


class FeatureResponse(BaseModel):
    """Response containing online features for a device."""

    device_id: str
    features: dict[str, Any]
    feature_names: list[str]
