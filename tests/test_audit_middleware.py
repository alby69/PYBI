"""Tests for Audit Middleware and Admin Usage Metrics API."""

from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.api.middleware.audit import audit_store

client = TestClient(app)


def test_audit_middleware_and_usage_metrics():
    # Execute a few requests
    client.get("/api/v1/projects")
    client.get("/api/v1/admin/usage-metrics")

    metrics_res = client.get("/api/v1/admin/usage-metrics")
    assert metrics_res.status_code == 200

    data = metrics_res.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 2
    assert "status_code_counts" in data
    assert "average_latency_ms" in data
    assert isinstance(data["recent_logs"], list)
