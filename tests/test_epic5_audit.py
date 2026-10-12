"""Tests for Epic 5: Observability and Audit."""

from fastapi.testclient import TestClient
import pytest

from pybi.api.main import app
from pybi.api.middleware.audit import AuditLogStore
from pybi.auth.jwt_auth import create_access_token

client = TestClient(app)


def test_audit_middleware_and_admin_metrics():
    AuditLogStore.clear()

    # Generate admin JWT token
    admin_token = create_access_token({"sub": "admin", "role": "admin"})
    viewer_token = create_access_token({"sub": "john_viewer", "role": "viewer"})

    # Make several API requests
    res1 = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {admin_token}"})
    assert res1.status_code == 200

    res2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res2.status_code == 200

    # Query admin metrics with viewer token -> should be 403
    res_forbidden = client.get("/api/v1/admin/usage-metrics", headers={"Authorization": f"Bearer {viewer_token}"})
    assert res_forbidden.status_code == 403

    # Query admin metrics with admin token -> should return metrics dict
    res_metrics = client.get("/api/v1/admin/usage-metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_metrics.status_code == 200

    metrics = res_metrics.json()
    assert metrics["total_requests"] >= 3
    assert metrics["active_users"] >= 2
    assert "avg_response_time_ms" in metrics
    assert "status_codes" in metrics
