"""Tests for ALM project bundler and import/export REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from pybi.alm.bundler import ProjectBundler
from pybi.api.main import app
from pybi.core.storage import default_storage
from pybi.storage.project_manager import create_project

client = TestClient(app)


def test_project_bundler_export_import():
    pid = "test_alm_proj_unique"
    if not default_storage.project_exists(pid):
        create_project("ALM Test Project", project_id=pid)

    bundle_bytes = ProjectBundler.export_bundle(pid)
    assert isinstance(bundle_bytes, bytes)
    assert len(bundle_bytes) > 0

    import_res = ProjectBundler.import_bundle(bundle_bytes, target_project_id="imported_alm_proj")
    assert import_res["status"] == "success"
    assert import_res["project_id"] == "imported_alm_proj"


def test_alm_export_import_api_endpoints():
    pid = "api_alm_proj_unique"
    if not default_storage.project_exists(pid):
        client.post("/api/v1/projects", json={"name": "API ALM Proj", "project_id": pid})

    export_res = client.get(f"/api/v1/projects/{pid}/export")
    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/zip"

    files = {"file": ("bundle.pybi", export_res.content, "application/zip")}
    import_res = client.post("/api/v1/projects/import", files=files)
    assert import_res.status_code == 201
    assert import_res.json()["success"] is True
