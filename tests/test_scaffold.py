"""
Scaffolding verification tests for Phase 1.
"""
import fastapi
import numpy
import pandas
import scipy
from starlette.testclient import TestClient

from app.main import app


def test_package_imports():
    """Verify core numerical and web dependencies are accessible."""
    assert fastapi.__version__ is not None
    assert numpy.__version__ is not None
    assert pandas.__version__ is not None
    assert scipy.__version__ is not None


def test_health_endpoint():
    """Verify minimal FastAPI application health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Climate Trend Analyzer" in data["service"]
