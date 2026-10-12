"""Tests for Epic 4: ALM & Project Portability."""

import os
from fastapi.testclient import TestClient
import pytest

from pybi.alm.bundler import ProjectBundler
from pybi.api.main import app
from pybi.core.storage import default_storage

client = TestClient(app)


def test_project_bundler_export_import(tmp_path):
    pid = "alm_test_proj"
    if default_storage.project_exists(pid):
        default_storage.delete_project(pid)

    # 1. Create project with data file and semantic model
    default_storage.save_project(pid, name="ALM Test Project")
    data_file = default_storage.save_uploaded_file(pid, "sales.csv", b"id,amount\n1,100\n2,200")
    assert os.path.exists(data_file)

    # 2. Export bundle
    bundle_path = tmp_path / f"{pid}.pybi"
    exported = ProjectBundler.create_bundle(pid, output_path=bundle_path)
    assert exported.exists()

    # 3. Delete original project
    default_storage.delete_project(pid)
    assert not default_storage.project_exists(pid)

    # 4. Import bundle under restored ID
    imported_id = ProjectBundler.extract_bundle(exported, target_project_id="restored_alm_proj")
    assert imported_id == "restored_alm_proj"
    assert default_storage.project_exists("restored_alm_proj")

    restored_files = default_storage.list_project_files("restored_alm_proj")
    assert "sales.csv" in restored_files

    default_storage.delete_project("restored_alm_proj")


def test_project_import_export_api_e2e(tmp_path):
    pid = "api_alm_proj"
    if default_storage.project_exists(pid):
        default_storage.delete_project(pid)

    res_create = client.post("/api/v1/projects", json={"name": "API ALM", "project_id": pid})
    assert res_create.status_code == 201

    # Export via API
    res_exp = client.get(f"/api/v1/projects/{pid}/export")
    assert res_exp.status_code == 200
    bundle_bytes = res_exp.content

    # Delete project
    client.delete(f"/api/v1/projects/{pid}")

    # Import via API
    res_imp = client.post(
        "/api/v1/projects/import",
        files={"file": (f"{pid}.pybi", bundle_bytes, "application/zip")},
    )
    assert res_imp.status_code == 201
    assert res_imp.json()["id"] == pid

    client.delete(f"/api/v1/projects/{pid}")
