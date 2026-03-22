"""
Tests for the /health endpoint and basic app startup.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


def test_health_returns_ok(client):
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_index_page_loads(client):
    """GET / should return 200 and contain the app title."""
    response = client.get("/")
    assert response.status_code == 200
    assert "MLOps LlamaIndex Lab" in response.text
