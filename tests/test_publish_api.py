"""Tests for Publisher and Viewer API."""

import os
import pytest
from fastapi.testclient import TestClient
from pybi.api import app
from pybi.publish import DashboardPublisher


def test_dashboard_publisher(tmp_path):
    publisher = DashboardPublisher()

    html_file = str(tmp_path / "test.html")
    pdf_file = str(tmp_path / "test.pdf")

    res_html = publisher.export_to_html("proj_1", html_file)
    assert os.path.exists(res_html)

    res_pdf = publisher.export_to_pdf("proj_1", pdf_file)
    assert os.path.exists(res_pdf)


def test_viewer_api():
    client = TestClient(app)

    res = client.get("/api/viewer/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_proj = client.get("/api/viewer/projects/demo")
    assert res_proj.status_code == 200
    assert res_proj.json()["project_id"] == "demo"
