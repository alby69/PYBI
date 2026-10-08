"""Unit and integration tests for PyBI API v1 endpoints."""

import os
import shutil
import pytest
from fastapi.testclient import TestClient

from pybi.api.main import app
from pybi.core.storage import default_storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_projects():
    """Cleanup test project storage directory before and after test runs."""
    test_proj_ids = ["v1_test_proj", "v1_etl_proj", "v1_dash_proj", "v1_export_proj", "v1_viewer_proj"]
    for pid in test_proj_ids:
        default_storage.delete_project(pid)
    yield
    for pid in test_proj_ids:
        default_storage.delete_project(pid)


def test_auth_endpoints():
    """Test v1 Auth endpoints (login and profile info)."""
    # Test Login
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secretpassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"

    token = data["access_token"]

    # Test /me with valid token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "admin"
    assert me_data["role"] == "admin"

    # Test /me without token (guest fallback)
    guest_res = client.get("/api/v1/auth/me")
    assert guest_res.status_code == 200
    guest_data = guest_res.json()
    assert guest_data["username"] == "guest"


def test_projects_crud_and_files():
    """Test v1 Project CRUD operations and file upload management."""
    pid = "v1_test_proj"

    # 1. Create Project
    create_res = client.post(
        "/api/v1/projects",
        json={"project_id": pid, "name": "V1 Test Project", "description": "Testing API v1"},
    )
    assert create_res.status_code == 201
    proj_data = create_res.json()
    assert proj_data["id"] == pid
    assert proj_data["name"] == "V1 Test Project"

    # Duplicate creation error
    dup_res = client.post(
        "/api/v1/projects",
        json={"project_id": pid, "name": "Duplicate"},
    )
    assert dup_res.status_code == 400

    # 2. List Projects
    list_res = client.get("/api/v1/projects")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    pids = [p["project_id"] for p in list_data["projects"]]
    assert pid in pids

    # 3. Get Project
    get_res = client.get(f"/api/v1/projects/{pid}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == pid

    # 4. Update Project
    update_res = client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "Updated V1 Project Name", "description": "Updated Description"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated V1 Project Name"

    # 5. File Upload
    file_content = b"id,val\n1,10\n2,20\n"
    upload_res = client.post(
        f"/api/v1/projects/{pid}/files",
        files={"file": ("sample.csv", file_content, "text/csv")},
    )
    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    assert upload_data["filename"] == "sample.csv"
    assert upload_data["size_bytes"] == len(file_content)

    # 6. List Files
    files_res = client.get(f"/api/v1/projects/{pid}/files")
    assert files_res.status_code == 200
    assert "sample.csv" in files_res.json()["files"]

    # 7. Delete File
    del_file_res = client.delete(f"/api/v1/projects/{pid}/files/sample.csv")
    assert del_file_res.status_code == 200

    # 8. Delete Project
    del_res = client.delete(f"/api/v1/projects/{pid}")
    assert del_res.status_code == 200

    # 404 Check after deletion
    not_found_res = client.get(f"/api/v1/projects/{pid}")
    assert not_found_res.status_code == 404


def test_etl_endpoints():
    """Test v1 ETL DAG save, execute, job status polling, and preview endpoints."""
    pid = "v1_etl_proj"
    client.post("/api/v1/projects", json={"project_id": pid, "name": "ETL Project"})

    # Upload data file for ETL
    csv_bytes = b"category,amount\nA,100\nB,200\nA,300\n"
    client.post(
        f"/api/v1/projects/{pid}/files",
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )

    sample_dag = {
        "nodes": [
            {
                "id": "node_1",
                "type": "source",
                "data": {"node_type": "DataSource", "file_path": "sales.csv"},
            },
            {
                "id": "node_2",
                "type": "transform",
                "data": {"node_type": "Transform", "transform_type": "filter", "condition": "amount > 150"},
            },
        ],
        "edges": [
            {"id": "e1-2", "source": "node_1", "target": "node_2"}
        ],
    }

    # Save DAG via PUT /etl/dag
    save_res = client.put(f"/api/v1/projects/{pid}/etl/dag", json={"nodes": sample_dag["nodes"], "edges": sample_dag["edges"]})
    assert save_res.status_code == 200

    # Get DAG via GET /etl/dag
    get_dag_res = client.get(f"/api/v1/projects/{pid}/etl/dag")
    assert get_dag_res.status_code == 200
    fetched_nodes = get_dag_res.json()["nodes"]
    assert len(fetched_nodes) == 2

    # Execute DAG
    exec_res = client.post(f"/api/v1/projects/{pid}/etl/execute", json={"project_id": pid})
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "success"

    # Preview Node Output
    prev_res = client.post(
        f"/api/v1/projects/{pid}/etl/preview",
        json={"project_id": pid, "node_id": "node_2", "limit": 10},
    )
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["node_id"] == "node_2"
    assert prev_data["total_rows"] == 2
    assert "category" in prev_data["columns"]


def test_dashboards_endpoints():
    """Test v1 Dashboard endpoints including POST create dashboard."""
    pid = "v1_dash_proj"
    client.post("/api/v1/projects", json={"project_id": pid, "name": "Dash Project"})

    sample_layout = [
        {"i": "w1", "x": 0, "y": 0, "w": 6, "h": 4, "widget_type": "bar_chart"}
    ]

    # Create Dashboard via POST
    create_dash_res = client.post(
        f"/api/v1/projects/{pid}/dashboards",
        json={"name": "New Dynamic Dashboard"},
    )
    assert create_dash_res.status_code == 201
    created_id = create_dash_res.json()["dashboard_id"]

    # Save Dashboard
    save_res = client.put(
        f"/api/v1/projects/{pid}/dashboards/{created_id}",
        json={"name": "New Dynamic Dashboard", "layout": sample_layout, "bindings": {}},
    )
    assert save_res.status_code == 200

    # List Dashboards
    list_res = client.get(f"/api/v1/projects/{pid}/dashboards")
    assert list_res.status_code == 200
    d_list = list_res.json()["dashboards"]
    assert len(d_list) >= 1

    # Get Specific Dashboard
    get_res = client.get(f"/api/v1/projects/{pid}/dashboards/{created_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "New Dynamic Dashboard"
    assert get_res.json()["layout"] == sample_layout

    # Delete Dashboard
    del_res = client.delete(f"/api/v1/projects/{pid}/dashboards/{created_id}")
    assert del_res.status_code == 200


def test_viewer_data_endpoint():
    """Test v1 Viewer aggregated data endpoint."""
    pid = "v1_viewer_proj"
    client.post("/api/v1/projects", json={"project_id": pid, "name": "Viewer Project"})

    sample_layout = [
        {"i": "w1", "x": 0, "y": 0, "w": 6, "h": 4, "widget_type": "bar_chart", "config": {"source_name": "sales"}}
    ]
    client.put(
        f"/api/v1/projects/{pid}/dashboards/dash_1",
        json={"name": "Viewer Dash", "layout": sample_layout, "bindings": {}},
    )

    viewer_data_res = client.get(f"/api/v1/viewer/{pid}/dashboards/dash_1/data")
    assert viewer_data_res.status_code == 200
    data = viewer_data_res.json()
    assert data["project_id"] == pid
    assert data["dashboard_id"] == "dash_1"
    assert len(data["widgets"]) == 1
