"""API tests for FactoryPulse FastAPI service."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client, patching ClickHouse to avoid real connections."""
    import unittest.mock as mock

    # Mock clickhouse_connect before importing the app
    mock_ch = mock.MagicMock()
    mock_ch.query.return_value = mock.MagicMock(result_rows=[], column_names=[])

    with mock.patch("clickhouse_connect.get_client", return_value=mock_ch):
        from main import app

        yield TestClient(app)


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "FactoryPulse API"
    assert data["version"] == "1.0.0"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_telemetry_endpoint(client):
    response = client.get("/api/v1/telemetry?limit=5&hours_back=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_telemetry_stats(client):
    response = client.get("/api/v1/telemetry/stats?hours_back=1")
    assert response.status_code == 200


def test_alerts_endpoint(client):
    response = client.get("/api/v1/alerts?limit=5")
    assert response.status_code == 200


def test_active_alerts(client):
    response = client.get("/api/v1/alerts/active?limit=5")
    assert response.status_code == 200


def test_devices_endpoint(client):
    response = client.get("/api/v1/devices?limit=5")
    assert response.status_code == 200


def test_metrics_endpoint(client):
    """Prometheus metrics endpoint should be exposed."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_request" in response.text or "HELP" in response.text
